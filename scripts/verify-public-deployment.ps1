param(
  [string]$ApiBaseUrl = 'https://gleaming-cooperation-staging.up.railway.app',
  [string]$WebBaseUrl = 'https://rt-connect-web-staging-staging.up.railway.app',
  [string]$ExpectedVersion = '',
  [string]$ExpectedSchemaRevision = '',
  [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
$ApiBaseUrl = $ApiBaseUrl.TrimEnd('/')
$WebBaseUrl = $WebBaseUrl.TrimEnd('/')
$checks = [System.Collections.Generic.List[object]]::new()

function Add-Check {
  param(
    [string]$Name,
    [string]$Url,
    [bool]$Ok,
    [string]$Details,
    [int]$StatusCode = 0
  )
  $checks.Add([ordered]@{
      name = $Name
      url = $Url
      ok = $Ok
      status_code = $StatusCode
      details = $Details
    })
}

function Get-JsonEndpoint {
  param([string]$Name, [string]$Url)
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
      Add-Check -Name $Name -Url $Url -Ok $false -StatusCode $response.StatusCode -Details 'HTTP status is not 2xx.'
      return $null
    }
    try {
      $payload = $response.Content | ConvertFrom-Json
    }
    catch {
      Add-Check -Name $Name -Url $Url -Ok $false -StatusCode $response.StatusCode -Details 'Response is not valid JSON.'
      return $null
    }
    return [pscustomobject]@{ Payload = $payload; StatusCode = $response.StatusCode }
  }
  catch {
    Add-Check -Name $Name -Url $Url -Ok $false -Details $_.Exception.Message
    return $null
  }
}

$healthResult = Get-JsonEndpoint -Name 'api.health' -Url "$ApiBaseUrl/api/v1/health"
if ($null -ne $healthResult) {
  $healthOk = $healthResult.Payload.status -eq 'ok'
  Add-Check -Name 'api.health.contract' -Url "$ApiBaseUrl/api/v1/health" -Ok $healthOk `
    -StatusCode $healthResult.StatusCode -Details ("status={0}" -f $healthResult.Payload.status)
}

$readyResult = Get-JsonEndpoint -Name 'api.ready' -Url "$ApiBaseUrl/api/v1/ready"
$schemaRevision = $null
if ($null -ne $readyResult) {
  $schemaRevision = [string]$readyResult.Payload.schema_revision
  $readyOk = $readyResult.Payload.status -eq 'ready'
  Add-Check -Name 'api.ready.contract' -Url "$ApiBaseUrl/api/v1/ready" -Ok $readyOk `
    -StatusCode $readyResult.StatusCode -Details ("status={0}; schema_revision={1}" -f $readyResult.Payload.status, $schemaRevision)
  if ($ExpectedSchemaRevision) {
    Add-Check -Name 'api.ready.schema_revision' -Url "$ApiBaseUrl/api/v1/ready" `
      -Ok ($schemaRevision -eq $ExpectedSchemaRevision) -StatusCode $readyResult.StatusCode `
      -Details ("expected={0}; observed={1}" -f $ExpectedSchemaRevision, $schemaRevision)
  }
}

$versionResult = Get-JsonEndpoint -Name 'api.version' -Url "$ApiBaseUrl/api/v1/version"
$version = $null
if ($null -ne $versionResult) {
  $version = [string]$versionResult.Payload.version
  $versionOk = (-not [string]::IsNullOrWhiteSpace($version)) -and `
    ([string]$versionResult.Payload.environment -in @('staging', 'production'))
  Add-Check -Name 'api.version.contract' -Url "$ApiBaseUrl/api/v1/version" -Ok $versionOk `
    -StatusCode $versionResult.StatusCode -Details ("version={0}; environment={1}; schema_revision={2}" -f `
      $version, $versionResult.Payload.environment, $versionResult.Payload.schema_revision)
  if ($ExpectedVersion) {
    Add-Check -Name 'api.version.expected' -Url "$ApiBaseUrl/api/v1/version" `
      -Ok ($version -eq $ExpectedVersion) -StatusCode $versionResult.StatusCode `
      -Details ("expected={0}; observed={1}" -f $ExpectedVersion, $version)
  }
}

$openapiResult = Get-JsonEndpoint -Name 'api.openapi' -Url "$ApiBaseUrl/api/v1/openapi.json"
if ($null -ne $openapiResult) {
  $openapiText = $openapiResult.Payload | ConvertTo-Json -Depth 100 -Compress
  $routeOk = $openapiText.Contains('/dvh/ct-preview')
  Add-Check -Name 'api.openapi.ct_preview_route' -Url "$ApiBaseUrl/api/v1/openapi.json" `
    -Ok $routeOk -StatusCode $openapiResult.StatusCode -Details ("route_present={0}" -f $routeOk)
}

try {
  $webResponse = Invoke-WebRequest -Uri $WebBaseUrl -UseBasicParsing
  $webOk = $webResponse.StatusCode -ge 200 -and $webResponse.StatusCode -lt 300
  Add-Check -Name 'web.index' -Url $WebBaseUrl -Ok $webOk -StatusCode $webResponse.StatusCode `
    -Details ("bytes={0}" -f ([Text.Encoding]::UTF8.GetByteCount($webResponse.Content)))

  $assetMatch = [regex]::Match($webResponse.Content, 'assets/[^"''\s]+\.js')
  if (-not $assetMatch.Success) {
    Add-Check -Name 'web.bundle.discover' -Url $WebBaseUrl -Ok $false -StatusCode $webResponse.StatusCode `
      -Details 'No JavaScript asset was found in the public index.'
  }
  else {
    $bundleUrl = "$WebBaseUrl/$($assetMatch.Value)"
    $bundleResponse = Invoke-WebRequest -Uri $bundleUrl -UseBasicParsing
    $bundleText = $bundleResponse.Content
    $bundleOk = $bundleResponse.StatusCode -ge 200 -and $bundleResponse.StatusCode -lt 300
    Add-Check -Name 'web.bundle' -Url $bundleUrl -Ok $bundleOk -StatusCode $bundleResponse.StatusCode `
      -Details ("bytes={0}; sha256={1}" -f `
        ([Text.Encoding]::UTF8.GetByteCount($bundleText)),
        ([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash([Text.Encoding]::UTF8.GetBytes($bundleText))).Replace('-', '').ToLowerInvariant()))
    $ctPreviewOk = $bundleText.Contains('CT ANATOMY PREVIEW')
    Add-Check -Name 'web.bundle.ct_preview_controls' -Url $bundleUrl -Ok $ctPreviewOk `
      -StatusCode $bundleResponse.StatusCode -Details ("ct_preview_controls_present={0}" -f $ctPreviewOk)
    if ($ExpectedVersion) {
      $buildLabelOk = $bundleText.Contains($ExpectedVersion)
      Add-Check -Name 'web.bundle.expected_version' -Url $bundleUrl -Ok $buildLabelOk `
        -StatusCode $bundleResponse.StatusCode -Details ("expected={0}; present={1}" -f $ExpectedVersion, $buildLabelOk)
    }
  }
}
catch {
  Add-Check -Name 'web.public' -Url $WebBaseUrl -Ok $false -Details $_.Exception.Message
}

$failed = @($checks | Where-Object { -not $_.ok })
$report = [ordered]@{
  schema_version = 'rt-connect.public-deployment-verification.v1'
  captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
  api_base_url = $ApiBaseUrl
  web_base_url = $WebBaseUrl
  expected_version = $ExpectedVersion
  expected_schema_revision = $ExpectedSchemaRevision
  observed_version = $version
  observed_schema_revision = $schemaRevision
  passed = ($failed.Count -eq 0)
  failed_check_count = $failed.Count
  checks = $checks
}

$json = $report | ConvertTo-Json -Depth 20
if ($OutputPath) {
  $targetPath = if ([IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path (Split-Path -Parent $PSScriptRoot) $OutputPath }
  $targetDirectory = Split-Path -Parent $targetPath
  if ($targetDirectory -and -not (Test-Path $targetDirectory)) {
    New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
  }
  [IO.File]::WriteAllText($targetPath, $json, [Text.UTF8Encoding]::new($false))
}

$json
if ($failed.Count -gt 0) { exit 1 }
