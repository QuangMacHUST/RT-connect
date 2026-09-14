[CmdletBinding()]
param(
  [string]$EnvPath = (Join-Path (Get-Location) '.env'),
  [string]$ProjectId = '339f2c50-ddd7-491f-8c4e-da2a2d169502',
  [string]$EnvironmentId = 'b0ab34e5-0ff4-479d-8232-659d175e9e2f',
  [string]$ApiServiceId = '9b35bf0b-0419-4679-8af0-e639e5a84713',
  [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'

function Get-AccountToken {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw ".env is required: $Path"
  }
  $line = Get-Content -LiteralPath $Path | Where-Object {
    $_ -match '^\s*RAILWAY_ACCOUNT_TOKEN\s*='
  } | Select-Object -First 1
  if (-not $line) { throw 'RAILWAY_ACCOUNT_TOKEN is missing from .env.' }
  $token = ($line -replace '^\s*RAILWAY_ACCOUNT_TOKEN\s*=\s*', '').Trim()
  $token = $token.Trim('"').Trim("'")
  if ([string]::IsNullOrWhiteSpace($token)) {
    throw 'RAILWAY_ACCOUNT_TOKEN is empty.'
  }
  return $token
}

function Invoke-RailwayGraphQL {
  param(
    [Parameter(Mandatory = $true)][string]$Token,
    [Parameter(Mandatory = $true)][string]$Query,
    [hashtable]$Variables = @{}
  )
  $body = @{ query = $Query; variables = $Variables } | ConvertTo-Json -Depth 20
  $response = Invoke-RestMethod `
    -Uri 'https://backboard.railway.com/graphql/v2' `
    -Method Post `
    -Headers @{ Authorization = "Bearer $Token"; 'Content-Type' = 'application/json' } `
    -Body $body
  if ($response.errors) {
    $messages = @($response.errors | ForEach-Object { $_.message }) -join '; '
    throw "Railway GraphQL request failed: $messages"
  }
  return $response.data
}

function Get-EnvironmentName {
  param([string]$Token)
  $query = @'
query($id:String!, $projectId:String!) {
  environment(id:$id, projectId:$projectId) { id name }
}
'@
  return (Invoke-RailwayGraphQL -Token $Token -Query $query -Variables @{
      id = $EnvironmentId
      projectId = $ProjectId
    }).environment.name
}

function Get-VariableValue {
  param([string]$Token)
  $query = @'
query($environmentId:String!, $projectId:String!, $serviceId:String!) {
  variables(environmentId:$environmentId, projectId:$projectId, serviceId:$serviceId, unrendered:false)
}
'@
  $map = (Invoke-RailwayGraphQL -Token $Token -Query $query -Variables @{
      environmentId = $EnvironmentId
      projectId = $ProjectId
      serviceId = $ApiServiceId
    }).variables
  $property = $map.PSObject.Properties['S3_BUCKET']
  if ($null -eq $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw 'API S3_BUCKET is missing or empty; refusing to run a destructive configuration probe.'
  }
  return [string]$property.Value
}

function Set-Bucket {
  param([string]$Token, [string]$Value)
  $mutation = @'
mutation($input:VariableUpsertInput!) {
  variableUpsert(input:$input)
}
'@
  $ok = (Invoke-RailwayGraphQL -Token $Token -Query $mutation -Variables @{
      input = @{
        environmentId = $EnvironmentId
        name = 'S3_BUCKET'
        projectId = $ProjectId
        serviceId = $ApiServiceId
        skipDeploys = $true
        value = $Value
      }
    }).variableUpsert
  if (-not $ok) { throw 'Railway rejected the S3_BUCKET update.' }
}

function Redeploy-Api {
  param([string]$Token)
  $mutation = @'
mutation($environmentId:String!, $serviceId:String!) {
  serviceInstanceRedeploy(environmentId:$environmentId, serviceId:$serviceId)
}
'@
  $ok = (Invoke-RailwayGraphQL -Token $Token -Query $mutation -Variables @{
      environmentId = $EnvironmentId
      serviceId = $ApiServiceId
    }).serviceInstanceRedeploy
  if (-not $ok) { throw 'Railway rejected the API staging redeploy.' }
}

function Get-LatestDeployment {
  param([string]$Token)
  $query = @'
query($input:DeploymentListInput!) {
  deployments(first:10, input:$input) {
    edges { node { id status createdAt serviceId environmentId } }
  }
}
'@
  $edges = (Invoke-RailwayGraphQL -Token $Token -Query $query -Variables @{
      input = @{
        projectId = $ProjectId
        environmentId = $EnvironmentId
        serviceId = $ApiServiceId
      }
    }).deployments.edges
  return @($edges | ForEach-Object { $_.node } | Sort-Object {
      [DateTime]$_.createdAt
    } -Descending | Select-Object -First 1)
}

function Wait-ForDeployment {
  param(
    [string]$Token,
    [DateTime]$BaselineCreatedAt
  )
  $deadline = (Get-Date).ToUniversalTime().AddSeconds($TimeoutSeconds)
  do {
    $latest = Get-LatestDeployment -Token $Token
    if ($latest -and ([DateTime]$latest.createdAt -gt $BaselineCreatedAt)) {
      if ($latest.status -eq 'SUCCESS') { return $latest }
      if ($latest.status -in @('FAILED', 'CRASHED', 'REMOVED', 'CANCELED', 'SKIPPED')) {
        throw "API staging deployment ended in terminal state $($latest.status)."
      }
      Write-Output "Waiting for staging API deployment state $($latest.status)..."
    }
    Start-Sleep -Seconds 10
  } while ((Get-Date).ToUniversalTime() -lt $deadline)
  throw 'Timed out waiting for the staging API deployment.'
}

$token = Get-AccountToken -Path $EnvPath
$environmentName = Get-EnvironmentName -Token $token
if ($environmentName -ne 'staging') {
  throw "Refusing to mutate non-staging environment: $environmentName"
}

$originalBucket = $null
$restoreRequired = $false
try {
  $originalBucket = Get-VariableValue -Token $token
  $baseline = Get-LatestDeployment -Token $token
  $baselineCreatedAt = if ($baseline) { [DateTime]$baseline.createdAt } else { [DateTime]'2000-01-01T00:00:00Z' }
  $faultBucket = "rt-connect-p6-fault-$([Guid]::NewGuid().ToString('N').Substring(0, 12))"
  Set-Bucket -Token $token -Value $faultBucket
  $restoreRequired = $true
  Redeploy-Api -Token $token
  $deployment = Wait-ForDeployment -Token $token -BaselineCreatedAt $baselineCreatedAt
  Write-Output "FAULT_READY deployment=$($deployment.id)"
  Write-Output 'Run the staging upload/retry probe now, then type RESTORE on stdin.'
  $signal = [Console]::ReadLine()
  if ($signal.Trim() -ne 'RESTORE') {
    throw 'Expected RESTORE on stdin before restoring the staging API configuration.'
  }
}
finally {
  if ($restoreRequired -and $originalBucket) {
    try {
      $restoreBaseline = Get-LatestDeployment -Token $token
      $restoreBaselineCreatedAt = if ($restoreBaseline) {
        [DateTime]$restoreBaseline.createdAt
      } else {
        [DateTime]'2000-01-01T00:00:00Z'
      }
      Set-Bucket -Token $token -Value $originalBucket
      Redeploy-Api -Token $token
      $restored = Wait-ForDeployment -Token $token -BaselineCreatedAt $restoreBaselineCreatedAt
      Write-Output "RESTORED deployment=$($restored.id)"
    }
    catch {
      Write-Error "STAGING RESTORE FAILED: $($_.Exception.Message)"
      throw
    }
  }
}
