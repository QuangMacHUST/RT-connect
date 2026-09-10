param(
  [string]$ProjectId,
  [string]$EnvironmentId,
  [string]$ApiServiceId,
  [string]$WebServiceId,
  [string]$WorkerServiceId,
  [string]$ExpectedWebOrigin,
  [string]$ExpectedApiBaseUrl,
  [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'

function Get-AccountToken {
  $envPath = Join-Path (Get-Location) '.env'
  if (-not (Test-Path -LiteralPath $envPath)) {
    throw '.env is required for the Railway read-only verifier.'
  }
  $line = Get-Content -LiteralPath $envPath | Where-Object {
    $_ -match '^\s*RAILWAY_ACCOUNT_TOKEN\s*='
  } | Select-Object -First 1
  if (-not $line) { throw 'RAILWAY_ACCOUNT_TOKEN is missing from .env.' }
  $token = ($line -replace '^\s*RAILWAY_ACCOUNT_TOKEN\s*=\s*', '').Trim()
  $token = $token.Trim('"').Trim("'")
  if ([string]::IsNullOrWhiteSpace($token)) { throw 'RAILWAY_ACCOUNT_TOKEN is empty.' }
  return $token
}

function Invoke-RailwayGraphQL {
  param(
    [string]$Token,
    [string]$Query,
    [hashtable]$Variables
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

function Add-Check {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Name,
    [bool]$Ok,
    [string]$Details
  )
  $Checks.Add([ordered]@{ name = $Name; ok = $Ok; details = $Details })
}

function Get-VariableMap {
  param(
    [string]$Token,
    [string]$Project,
    [string]$Environment,
    [string]$Service
  )
  $query = @'
query($environmentId:String!, $projectId:String!, $serviceId:String!) {
  variables(environmentId:$environmentId, projectId:$projectId, serviceId:$serviceId, unrendered:false)
}
'@
  return (Invoke-RailwayGraphQL -Token $Token -Query $query -Variables @{
    environmentId = $Environment
    projectId = $Project
    serviceId = $Service
  }).variables
}

function Get-ServiceInstance {
  param(
    [string]$Token,
    [string]$Environment,
    [string]$Service
  )
  $query = @'
query($environmentId:String!, $serviceId:String!) {
  serviceInstance(environmentId:$environmentId, serviceId:$serviceId) {
    id serviceId serviceName environmentId rootDirectory startCommand buildCommand
    dockerfilePath healthcheckPath healthcheckTimeout preDeployCommand
    preDeployTimeoutSeconds railwayConfigFile restartPolicyType restartPolicyMaxRetries
    numReplicas
  }
}
'@
  return (Invoke-RailwayGraphQL -Token $Token -Query $query -Variables @{
    environmentId = $Environment
    serviceId = $Service
  }).serviceInstance
}

function Has-Name {
  param([object]$Map, [string]$Name)
  return $null -ne $Map.PSObject.Properties[$Name]
}

function Test-RequiredNames {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Service,
    [object]$Map,
    [string[]]$Names
  )
  foreach ($name in $Names) {
    Add-Check -Checks $Checks -Name "$Service.variable.$name" `
      -Ok (Has-Name -Map $Map -Name $name) -Details 'name_present; value_not_recorded'
  }
}

function Test-ForbiddenNames {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Service,
    [object]$Map
  )
  $forbidden = @(
    'RAILWAY_ACCOUNT_TOKEN', 'RAILWAY_PROJECT_TOKEN', 'SUPABASE_SERVICE_ROLE_KEY',
    'VITE_DATABASE_URL', 'VITE_SUPABASE_SERVICE_ROLE_KEY', 'VITE_S3_SECRET_ACCESS_KEY'
  )
  foreach ($name in $forbidden) {
    Add-Check -Checks $Checks -Name "$Service.forbidden.$name" `
      -Ok (-not (Has-Name -Map $Map -Name $name)) -Details 'forbidden_name_absent'
  }
}

function Test-InternalHost {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Name,
    [object]$Map,
    [string]$VariableName
  )
  $property = $Map.PSObject.Properties[$VariableName]
  $value = if ($property) { [string]$property.Value } else { '' }
  $ok = $false
  if ($value) {
    try {
      $uri = [Uri]$value
      $ok = $uri.Host -match '\.railway\.internal$' -or $uri.Host -in @('postgres', 'redis', 'minio')
    }
    catch { $ok = $false }
  }
  $details = if ($ok) { 'private-host-classified; value_not_recorded' } else { 'missing_or_not_private; value_not_recorded' }
  Add-Check -Checks $Checks -Name "$Name.$VariableName.private_host" `
    -Ok $ok -Details $details
}

function Test-StorageEndpoint {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Name,
    [object]$Map,
    [string]$VariableName
  )
  $property = $Map.PSObject.Properties[$VariableName]
  $value = if ($property) { [string]$property.Value } else { '' }
  $ok = $false
  if ($value) {
    try {
      $uri = [Uri]$value
      $ok = $uri.Scheme -eq 'https' -and
        $uri.Host -notmatch '\.up\.railway\.app$' -and
        $uri.Host -notmatch '^localhost$|^127\.0\.0\.1$'
    }
    catch { $ok = $false }
  }
  $details = if ($ok) { 'external-s3-compatible-endpoint; host_not_recorded' } else { 'missing_or_app_public_endpoint; value_not_recorded' }
  Add-Check -Checks $Checks -Name "$Name.$VariableName.external_endpoint" `
    -Ok $ok -Details $details
}

function Get-ArrayCount {
  param([object]$Value)
  if ($null -eq $Value) { return 0 }
  return @($Value).Count
}

function Test-PublicHttps {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Name,
    [object]$Map,
    [string]$VariableName
  )
  $property = $Map.PSObject.Properties[$VariableName]
  $value = if ($property) { [string]$property.Value } else { '' }
  $ok = $value -match '^https://[^\s,]+$'
  $details = if ($ok) { 'https-url-classified; value_not_recorded' } else { 'missing_or_not_https; value_not_recorded' }
  Add-Check -Checks $Checks -Name "$Name.$VariableName.https" `
    -Ok $ok -Details $details
}

function Normalize-PublicApiBaseUrl {
  param([string]$Value)

  $trimmed = $Value.Trim().TrimEnd('/')
  try {
    $uri = [Uri]$trimmed
  }
  catch {
    throw 'ExpectedApiBaseUrl must be an absolute HTTP(S) URL.'
  }
  if ($uri.Scheme -notin @('http', 'https') -or [string]::IsNullOrWhiteSpace($uri.Host)) {
    throw 'ExpectedApiBaseUrl must be an absolute HTTP(S) URL.'
  }

  $path = $uri.AbsolutePath.TrimEnd('/')
  if ($path -eq '') {
    return "$trimmed/api/v1"
  }
  if ($path -eq '/api/v1') {
    return $trimmed
  }
  throw 'ExpectedApiBaseUrl must be the public API origin or the /api/v1 base prefix.'
}

function Test-ExactValue {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Name,
    [object]$Map,
    [string]$VariableName,
    [string]$Expected
  )
  $property = $Map.PSObject.Properties[$VariableName]
  $actual = if ($property) { [string]$property.Value } else { '' }
  $ok = $actual -eq $Expected
  $observedClass = if ($actual) { 'present' } else { 'missing' }
  Add-Check -Checks $Checks -Name $Name -Ok $ok -Details ("expected={0}; observed_class={1}" -f $Expected, $observedClass)
}

function Test-CorsOrigin {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [object]$Map,
    [string]$ExpectedOrigin
  )
  $property = $Map.PSObject.Properties['CORS_ALLOWED_ORIGINS']
  $actual = if ($property) { [string]$property.Value } else { '' }
  $ok = $actual -and $actual.Contains($ExpectedOrigin) -and -not $actual.Contains('*')
  $details = if ($ok) { 'expected_origin_present; wildcard_absent; value_not_recorded' } else { 'origin_missing_or_wildcard_present; value_not_recorded' }
  Add-Check -Checks $Checks -Name 'api.cors.allowed_origin' -Ok $ok -Details $details
}

if ([string]::IsNullOrWhiteSpace($ProjectId) -or
    [string]::IsNullOrWhiteSpace($EnvironmentId) -or
    [string]::IsNullOrWhiteSpace($ApiServiceId) -or
    [string]::IsNullOrWhiteSpace($WebServiceId) -or
    [string]::IsNullOrWhiteSpace($WorkerServiceId) -or
    [string]::IsNullOrWhiteSpace($ExpectedWebOrigin) -or
    [string]::IsNullOrWhiteSpace($ExpectedApiBaseUrl)) {
  throw 'ProjectId, EnvironmentId, service IDs, ExpectedWebOrigin and ExpectedApiBaseUrl are required.'
}

$token = Get-AccountToken
$normalizedExpectedApiBaseUrl = Normalize-PublicApiBaseUrl -Value $ExpectedApiBaseUrl
$checks = [System.Collections.Generic.List[object]]::new()
$services = [ordered]@{
  api = $ApiServiceId
  web = $WebServiceId
  worker = $WorkerServiceId
}
$instances = [ordered]@{}
$variables = [ordered]@{}

foreach ($name in $services.Keys) {
  $instances[$name] = Get-ServiceInstance -Token $token -Environment $EnvironmentId -Service $services[$name]
  $variables[$name] = Get-VariableMap -Token $token -Project $ProjectId -Environment $EnvironmentId -Service $services[$name]
  Add-Check -Checks $checks -Name "$name.identity.service_id" `
    -Ok ($instances[$name].serviceId -eq $services[$name]) -Details "expected=$($services[$name]); observed=$($instances[$name].serviceId)"
  Add-Check -Checks $checks -Name "$name.identity.environment_id" `
    -Ok ($instances[$name].environmentId -eq $EnvironmentId) -Details "expected=$EnvironmentId; observed=$($instances[$name].environmentId)"
}

$api = $instances.api
Add-Check -Checks $checks -Name 'api.root_directory' -Ok ($api.rootDirectory -eq '/apps/api') -Details "observed=$($api.rootDirectory)"
Add-Check -Checks $checks -Name 'api.dockerfile' -Ok ($api.dockerfilePath -eq '/apps/api/Dockerfile') -Details "observed=$($api.dockerfilePath)"
Add-Check -Checks $checks -Name 'api.healthcheck' -Ok ($api.healthcheckPath -eq '/api/v1/health') -Details "observed=$($api.healthcheckPath)"
Add-Check -Checks $checks -Name 'api.pre_deploy_migration' -Ok (@($api.preDeployCommand) -contains 'alembic upgrade head') -Details "observed=$(@($api.preDeployCommand) -join ',')"
Test-RequiredNames -Checks $checks -Service 'api' -Map $variables.api -Names @('DATABASE_URL','REDIS_URL','S3_ENDPOINT','S3_BUCKET','SUPABASE_JWT_ISSUER','SUPABASE_JWT_AUDIENCE','SUPABASE_JWKS_URL','CORS_ALLOWED_ORIGINS')
Test-CorsOrigin -Checks $checks -Map $variables.api -ExpectedOrigin $ExpectedWebOrigin
Test-InternalHost -Checks $checks -Name 'api' -Map $variables.api -VariableName 'DATABASE_URL'
Test-InternalHost -Checks $checks -Name 'api' -Map $variables.api -VariableName 'REDIS_URL'
Test-StorageEndpoint -Checks $checks -Name 'api' -Map $variables.api -VariableName 'S3_ENDPOINT'
Test-ForbiddenNames -Checks $checks -Service 'api' -Map $variables.api

$web = $instances.web
Add-Check -Checks $checks -Name 'web.root_directory' -Ok ($web.rootDirectory -eq '/apps/web') -Details "observed=$($web.rootDirectory)"
Add-Check -Checks $checks -Name 'web.dockerfile' -Ok ($web.dockerfilePath -eq '/apps/web/Dockerfile') -Details "observed=$($web.dockerfilePath)"
Add-Check -Checks $checks -Name 'web.no_healthcheck' -Ok ([string]::IsNullOrWhiteSpace([string]$web.healthcheckPath)) -Details "observed=$($web.healthcheckPath)"
Add-Check -Checks $checks -Name 'web.no_pre_deploy' -Ok ((Get-ArrayCount -Value $web.preDeployCommand) -eq 0) -Details "observed=$(@($web.preDeployCommand) -join ',')"
Test-RequiredNames -Checks $checks -Service 'web' -Map $variables.web -Names @('VITE_API_BASE_URL','VITE_SUPABASE_URL','VITE_SUPABASE_PUBLISHABLE_KEY','VITE_APP_VERSION')
Test-ExactValue -Checks $checks -Name 'web.vite_api_base_url' -Map $variables.web -VariableName 'VITE_API_BASE_URL' -Expected $normalizedExpectedApiBaseUrl
Test-PublicHttps -Checks $checks -Name 'web' -Map $variables.web -VariableName 'VITE_API_BASE_URL'
Test-PublicHttps -Checks $checks -Name 'web' -Map $variables.web -VariableName 'VITE_SUPABASE_URL'
Test-ForbiddenNames -Checks $checks -Service 'web' -Map $variables.web

$worker = $instances.worker
Add-Check -Checks $checks -Name 'worker.root_directory' -Ok ($worker.rootDirectory -eq '/apps/api') -Details "observed=$($worker.rootDirectory)"
Add-Check -Checks $checks -Name 'worker.start_command' -Ok ($worker.startCommand -eq 'python -m rt_connect_api.worker') -Details "observed=$($worker.startCommand)"
Add-Check -Checks $checks -Name 'worker.no_healthcheck' -Ok ([string]::IsNullOrWhiteSpace([string]$worker.healthcheckPath)) -Details "observed=$($worker.healthcheckPath)"
Add-Check -Checks $checks -Name 'worker.no_pre_deploy' -Ok ((Get-ArrayCount -Value $worker.preDeployCommand) -eq 0) -Details "observed=$(@($worker.preDeployCommand) -join ',')"
Test-RequiredNames -Checks $checks -Service 'worker' -Map $variables.worker -Names @('DATABASE_URL','REDIS_URL','S3_ENDPOINT','S3_BUCKET','SUPABASE_JWT_ISSUER','SUPABASE_JWT_AUDIENCE','SUPABASE_JWKS_URL','GAMMA_WORKER_POLL_SECONDS')
Test-InternalHost -Checks $checks -Name 'worker' -Map $variables.worker -VariableName 'DATABASE_URL'
Test-InternalHost -Checks $checks -Name 'worker' -Map $variables.worker -VariableName 'REDIS_URL'
Test-StorageEndpoint -Checks $checks -Name 'worker' -Map $variables.worker -VariableName 'S3_ENDPOINT'
Test-ForbiddenNames -Checks $checks -Service 'worker' -Map $variables.worker

Add-Check -Checks $checks -Name 'worker.no_public_domain_variable' `
  -Ok (-not (Has-Name -Map $variables.worker -Name 'RAILWAY_PUBLIC_DOMAIN')) -Details 'worker_public_domain_variable_absent'

$failed = @($checks | Where-Object { -not $_.ok })
$report = [ordered]@{
  schema_version = 'rt-connect.railway-effective-settings.v1'
  captured_at_utc = [DateTime]::UtcNow.ToString('o')
  project_id = $ProjectId
  environment_id = $EnvironmentId
  services = $services
  service_settings = [ordered]@{
    api = $api
    web = $web
    worker = $worker
  }
  variable_names = [ordered]@{
    api = @($variables.api.PSObject.Properties.Name | Sort-Object)
    web = @($variables.web.PSObject.Properties.Name | Sort-Object)
    worker = @($variables.worker.PSObject.Properties.Name | Sort-Object)
  }
  checks = $checks
  passed = ($failed.Count -eq 0)
  failed_check_count = $failed.Count
  contains_secret_values = $false
  contains_database_urls = $false
  contains_patient_data = $false
}

$encoded = $report | ConvertTo-Json -Depth 20
if ($OutputPath) {
  $parent = Split-Path -Parent $OutputPath
  if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  Set-Content -LiteralPath $OutputPath -Value $encoded -Encoding UTF8
}
Write-Output $encoded
if (-not $report.passed) { exit 1 }
