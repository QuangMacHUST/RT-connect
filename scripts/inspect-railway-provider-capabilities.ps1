[CmdletBinding()]
param(
  [Parameter(Mandatory = $false)]
  [string]$EnvPath = (Join-Path (Get-Location) '.env'),

  [Parameter(Mandatory = $false)]
  [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

function Get-AccountToken {
  param([Parameter(Mandatory = $true)][string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    throw ".env is required for the Railway read-only capability inspection: $Path"
  }

  $line = Get-Content -LiteralPath $Path | Where-Object {
    $_ -match '^\s*RAILWAY_ACCOUNT_TOKEN\s*='
  } | Select-Object -First 1
  if (-not $line) {
    throw 'RAILWAY_ACCOUNT_TOKEN is missing from .env.'
  }

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
    [Parameter(Mandatory = $false)][hashtable]$Variables = @{}
  )

  $body = @{ query = $Query; variables = $Variables } | ConvertTo-Json -Depth 12
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

function Get-MatchingNames {
  param(
    [Parameter(Mandatory = $false)][object[]]$Items,
    [Parameter(Mandatory = $true)][string]$PropertyName
  )

  if ($null -eq $Items) {
    return @()
  }
  return @($Items |
    ForEach-Object { [string]$_.$PropertyName } |
    Where-Object { $_ -match '(?i)(backup|snapshot|restore|volume)' } |
    Sort-Object -Unique)
}

$token = Get-AccountToken -Path $EnvPath
$rootQuery = @'
query {
  __type(name: "Query") {
    fields { name }
  }
}
'@
$schemaQuery = @'
query {
  __schema {
    types { name kind }
  }
}
'@
$typeQuery = @'
query($name: String!) {
  __type(name: $name) {
    name
    kind
    fields { name }
  }
}
'@

$root = Invoke-RailwayGraphQL -Token $token -Query $rootQuery
$schema = Invoke-RailwayGraphQL -Token $token -Query $schemaQuery
$rootFields = if ($null -eq $root.__type) {
  @()
} else {
  Get-MatchingNames -Items @($root.__type.fields) -PropertyName 'name'
}
$typeNames = if ($null -eq $schema.__schema) {
  @()
} else {
  Get-MatchingNames -Items @($schema.__schema.types) -PropertyName 'name'
}
$matchedTypes = New-Object System.Collections.Generic.List[object]

foreach ($typeName in $typeNames) {
  $typeResult = Invoke-RailwayGraphQL -Token $token -Query $typeQuery -Variables @{ name = $typeName }
  $type = $typeResult.__type
  if ($null -ne $type) {
    $fields = Get-MatchingNames -Items @($type.fields) -PropertyName 'name'
    $matchedTypes.Add([ordered]@{
        name = $type.name
        kind = $type.kind
        matching_fields = $fields
      })
  }
}

$capabilityDetected = $rootFields.Count -gt 0 -or $matchedTypes.Count -gt 0
$interpretation = if ($capabilityDetected) {
  'Potential provider backup/snapshot/restore/volume symbols were exposed by Railway introspection; inspect the named fields read-only before using any mutation.'
} else {
  'No matching provider symbols were exposed by the introspected schema. This is not proof that the Railway UI/provider lacks backups; inspect the dashboard or provider documentation separately.'
}

$result = [ordered]@{
  schema_version = 'rt-connect.railway-provider-capabilities.v1'
  captured_at_utc = [DateTime]::UtcNow.ToString('o')
  endpoint = 'https://backboard.railway.com/graphql/v2'
  read_only = $true
  introspection_succeeded = $null -ne $schema.__schema
  query_root_exposed = $null -ne $root.__type
  provider_capability_detected = $capabilityDetected
  matching_query_fields = $rootFields
  matching_types = $matchedTypes.ToArray()
  interpretation = $interpretation
  secret_scan = [ordered]@{
    token_recorded = $false
    database_url_recorded = $false
  }
}

$json = $result | ConvertTo-Json -Depth 12
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
  $parent = Split-Path -Parent $OutputPath
  if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
  Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
}
Write-Output $json
