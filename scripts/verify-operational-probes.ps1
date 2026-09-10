[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ApiBaseUrl,

  [Parameter(Mandatory = $true)]
  [string]$WebBaseUrl,

  [Parameter(Mandatory = $true)]
  [string]$ExpectedVersion,

  [Parameter(Mandatory = $true)]
  [string]$ExpectedSchemaRevision,

  [Parameter(Mandatory = $false)]
  [string]$AccessToken,

  [Parameter(Mandatory = $false)]
  [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$checks = New-Object System.Collections.Generic.List[object]

function Normalize-BaseUrl {
  param([Parameter(Mandatory = $true)][string]$Value)
  return $Value.TrimEnd('/')
}

function Add-Check {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][bool]$Ok,
    [Parameter(Mandatory = $true)][int]$StatusCode,
    [Parameter(Mandatory = $true)][long]$ElapsedMs,
    [Parameter(Mandatory = $true)][string]$Details
  )
  $checks.Add([ordered]@{
      name = $Name
      ok = $Ok
      status_code = $StatusCode
      elapsed_ms = $ElapsedMs
      details = $Details
    })
}

function Get-JsonProbe {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $false)][hashtable]$Headers = @{}
  )
  $started = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    $response = Invoke-WebRequest -Uri $Url -Method Get -Headers $Headers -UseBasicParsing -TimeoutSec 15
    $started.Stop()
    $payload = $response.Content | ConvertFrom-Json
    return [pscustomobject]@{
      name = $Name
      url = $Url
      status_code = [int]$response.StatusCode
      elapsed_ms = $started.ElapsedMilliseconds
      payload = $payload
      error = $null
    }
  } catch {
    $started.Stop()
    $statusCode = 0
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
      $statusCode = [int]$_.Exception.Response.StatusCode
    }
    return [pscustomobject]@{
      name = $Name
      url = $Url
      status_code = $statusCode
      elapsed_ms = $started.ElapsedMilliseconds
      payload = $null
      error = $_.Exception.Message
    }
  }
}

function Get-TextProbe {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Url
  )
  $started = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 15
    $started.Stop()
    return [pscustomobject]@{
      name = $Name
      url = $Url
      status_code = [int]$response.StatusCode
      elapsed_ms = $started.ElapsedMilliseconds
      content = [string]$response.Content
      error = $null
    }
  } catch {
    $started.Stop()
    $statusCode = 0
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
      $statusCode = [int]$_.Exception.Response.StatusCode
    }
    return [pscustomobject]@{
      name = $Name
      url = $Url
      status_code = $statusCode
      elapsed_ms = $started.ElapsedMilliseconds
      content = ''
      error = $_.Exception.Message
    }
  }
}

$api = Normalize-BaseUrl $ApiBaseUrl
$web = Normalize-BaseUrl $WebBaseUrl

$health = Get-JsonProbe -Name 'api.health' -Url "$api/api/v1/health"
if ($health.error) {
  Add-Check 'api.health.contract' $false $health.status_code $health.elapsed_ms "request failed"
} else {
  Add-Check 'api.health.contract' ($health.status_code -eq 200 -and $health.payload.status -eq 'ok') $health.status_code $health.elapsed_ms ("status={0}" -f $health.payload.status)
}

$ready = Get-JsonProbe -Name 'api.ready' -Url "$api/api/v1/ready"
if ($ready.error) {
  Add-Check 'api.ready.contract' $false $ready.status_code $ready.elapsed_ms "request failed"
} else {
  $readyOk = $ready.status_code -eq 200 -and $ready.payload.status -eq 'ready'
  Add-Check 'api.ready.contract' $readyOk $ready.status_code $ready.elapsed_ms ("status={0}; schema_revision={1}" -f $ready.payload.status, $ready.payload.schema_revision)
  Add-Check 'api.ready.schema_revision' ($ready.payload.schema_revision -eq $ExpectedSchemaRevision) $ready.status_code $ready.elapsed_ms ("expected={0}; observed={1}" -f $ExpectedSchemaRevision, $ready.payload.schema_revision)
}

$version = Get-JsonProbe -Name 'api.version' -Url "$api/api/v1/version"
if ($version.error) {
  Add-Check 'api.version.contract' $false $version.status_code $version.elapsed_ms "request failed"
} else {
  $versionOk = $version.status_code -eq 200 -and
    -not [string]::IsNullOrWhiteSpace([string]$version.payload.version) -and
    ([string]$version.payload.environment -in @('staging', 'production'))
  Add-Check 'api.version.contract' $versionOk $version.status_code $version.elapsed_ms ("version={0}; environment={1}; schema_revision={2}" -f $version.payload.version, $version.payload.environment, $version.payload.schema_revision)
  Add-Check 'api.version.expected' ($version.payload.version -eq $ExpectedVersion) $version.status_code $version.elapsed_ms ("expected={0}; observed={1}" -f $ExpectedVersion, $version.payload.version)
  Add-Check 'api.version.schema_revision' ($version.payload.schema_revision -eq $ExpectedSchemaRevision) $version.status_code $version.elapsed_ms ("expected={0}; observed={1}" -f $ExpectedSchemaRevision, $version.payload.schema_revision)
}

if ($health.payload -and $ready.payload -and $version.payload) {
  $parityOk = $health.payload.status -eq 'ok' -and
    $ready.payload.status -eq 'ready' -and
    $ready.payload.schema_revision -eq $version.payload.schema_revision -and
    $ready.payload.schema_revision -eq $ExpectedSchemaRevision
  Add-Check 'platform.schema_parity' $parityOk 200 0 ("health={0}; ready={1}; ready_schema={2}; version_schema={3}" -f $health.payload.status, $ready.payload.status, $ready.payload.schema_revision, $version.payload.schema_revision)
}

$webProbe = Get-TextProbe -Name 'web.app' -Url "$web/app"
if ($webProbe.error) {
  Add-Check 'web.app.reachable' $false $webProbe.status_code $webProbe.elapsed_ms "request failed"
} else {
  $html = $webProbe.content
  $hasHtmlShell = $html -match '<html' -and $html -match '<script'
  $containsSecretLikeValue = $html -match '(?i)(postgres(?:ql)?://|service_role|secret_access_key|authorization:\s*bearer)'
  Add-Check 'web.app.reachable' ($webProbe.status_code -eq 200 -and $hasHtmlShell) $webProbe.status_code $webProbe.elapsed_ms ("html_shell={0}" -f $hasHtmlShell)
  Add-Check 'web.app.no_secret_markers' (-not $containsSecretLikeValue) $webProbe.status_code $webProbe.elapsed_ms ("secret_markers={0}" -f $containsSecretLikeValue)
}

if (-not [string]::IsNullOrWhiteSpace($AccessToken)) {
  $queue = Get-JsonProbe -Name 'api.gamma.queue_metrics' -Url "$api/api/v1/gamma/queue-metrics" -Headers @{ Authorization = "Bearer $AccessToken" }
  if ($queue.error) {
    Add-Check 'api.gamma.queue_metrics' $false $queue.status_code $queue.elapsed_ms "request failed"
  } else {
    $queueOk = $queue.status_code -eq 200 -and $null -ne $queue.payload.backend -and $null -ne $queue.payload.available
    Add-Check 'api.gamma.queue_metrics' $queueOk $queue.status_code $queue.elapsed_ms ("backend={0}; available={1}; configured={2}" -f $queue.payload.backend, $queue.payload.available, $queue.payload.configured)
  }
} else {
  $checks.Add([ordered]@{
      name = 'api.gamma.queue_metrics'
      ok = $null
      status_code = 0
      elapsed_ms = 0
      details = 'not run: no session access token supplied'
    })
}

$failedChecks = @($checks | Where-Object { $_.ok -eq $false })
$requiredChecks = @($checks | Where-Object { $_.ok -ne $null })
$passed = $failedChecks.Count -eq 0 -and $requiredChecks.Count -gt 0
$result = [ordered]@{
  schema_version = 'rt-connect.p20-operational-probes.v1'
  captured_at_utc = [DateTime]::UtcNow.ToString('o')
  api_base_url = $api
  web_base_url = $web
  expected_version = $ExpectedVersion
  expected_schema_revision = $ExpectedSchemaRevision
  access_token_supplied = -not [string]::IsNullOrWhiteSpace($AccessToken)
  passed = $passed
  failed_check_count = $failedChecks.Count
  checks = $checks.ToArray()
  scope = 'Operational endpoint and public web probe; no alert delivery, provider backup/restore, authenticated browser E2E, or clinical readiness claim.'
}

$json = $result | ConvertTo-Json -Depth 10
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
  $parent = Split-Path -Parent $OutputPath
  if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
  Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
}
Write-Output $json

if (-not $passed) {
  exit 1
}
