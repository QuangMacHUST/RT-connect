param(
  [string]$ApiBaseUrl = 'https://gleaming-cooperation-staging.up.railway.app',
  [string]$WebBaseUrl = 'https://rt-connect-web-staging-staging.up.railway.app',
  [string]$ExpectedVersion = '',
  [string]$ExpectedSchemaRevision = '',
  [int]$RequestTimeoutSec = 20,
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

function Invoke-PublicRequest {
  param(
    [string]$Url,
    [ValidateSet('GET', 'POST')]
    [string]$Method = 'GET',
    [string]$Body = ''
  )

  $statusMarker = '__RT_CONNECT_HTTP_STATUS__'
  $curlArguments = @(
    '--silent',
    '--show-error',
    '--location',
    '--max-time',
    [string]$RequestTimeoutSec,
    '--request',
    $Method,
    '--header',
    'Accept: application/json',
    '--write-out',
    "`n$statusMarker%{http_code}"
  )
  if ($Body) {
    $curlArguments += @('--header', 'Content-Type: application/json', '--data-raw', $Body)
  }
  $curlArguments += $Url

  $rawResponse = (& curl.exe @curlArguments 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0) {
    throw $rawResponse.Trim()
  }
  $markerIndex = $rawResponse.LastIndexOf($statusMarker)
  if ($markerIndex -lt 0) {
    throw 'curl did not return an HTTP status marker.'
  }
  $bodyText = $rawResponse.Substring(0, $markerIndex).TrimEnd("`r", "`n")
  $statusText = $rawResponse.Substring($markerIndex + $statusMarker.Length).Trim()
  return [pscustomobject]@{
    Body = $bodyText
    StatusCode = [int]$statusText
  }
}

function Get-JsonEndpoint {
  param([string]$Name, [string]$Url)
  try {
    $response = Invoke-PublicRequest -Url $Url
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
      Add-Check -Name $Name -Url $Url -Ok $false -StatusCode $response.StatusCode -Details 'HTTP status is not 2xx.'
      return $null
    }
    try {
      $payload = $response.Body | ConvertFrom-Json
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

function Get-ExpectedUnauthorizedEndpoint {
  param(
    [string]$Name,
    [string]$Url,
    [ValidateSet('GET', 'POST')]
    [string]$Method = 'GET',
    [string]$Body = ''
  )

  $statusCode = 0
  $details = ''
  try {
    $response = Invoke-PublicRequest -Url $Url -Method $Method -Body $Body
    $statusCode = $response.StatusCode
    $details = "observed_status=$statusCode"
  }
  catch {
    $details = $_.Exception.Message
  }

  $finalDetails = if ($details) { $details } else { 'No HTTP response.' }
  Add-Check -Name $Name -Url $Url -Ok ($statusCode -eq 401) -StatusCode $statusCode `
    -Details $finalDetails
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
  $organizationLifecycleOk = $openapiText.Contains('/api/v1/organizations/{organization_id}/members') `
    -and $openapiText.Contains('/api/v1/organizations/{organization_id}/invitations') `
    -and $openapiText.Contains('/api/v1/organizations/invitations/accept')
  Add-Check -Name 'api.openapi.organization_membership_routes' -Url "$ApiBaseUrl/api/v1/openapi.json" `
    -Ok $organizationLifecycleOk -StatusCode $openapiResult.StatusCode `
    -Details ("member_invitation_routes_present={0}" -f $organizationLifecycleOk)
}

$smokeOrganizationId = '00000000-0000-0000-0000-000000000000'
Get-ExpectedUnauthorizedEndpoint -Name 'api.organization.members.unauthenticated' `
  -Url "$ApiBaseUrl/api/v1/organizations/$smokeOrganizationId/members"
Get-ExpectedUnauthorizedEndpoint -Name 'api.organization.invitations.unauthenticated' `
  -Url "$ApiBaseUrl/api/v1/organizations/$smokeOrganizationId/invitations"
Get-ExpectedUnauthorizedEndpoint -Name 'api.organization.invitation_accept.unauthenticated' `
  -Url "$ApiBaseUrl/api/v1/organizations/invitations/accept" -Method 'POST'

try {
  $webResponse = Invoke-PublicRequest -Url $WebBaseUrl
  $webOk = $webResponse.StatusCode -ge 200 -and $webResponse.StatusCode -lt 300
  Add-Check -Name 'web.index' -Url $WebBaseUrl -Ok $webOk -StatusCode $webResponse.StatusCode `
    -Details ("bytes={0}" -f ([Text.Encoding]::UTF8.GetByteCount($webResponse.Body)))

  $assetMatch = [regex]::Match($webResponse.Body, 'assets/[^"''\s]+\.js')
  if (-not $assetMatch.Success) {
    Add-Check -Name 'web.bundle.discover' -Url $WebBaseUrl -Ok $false -StatusCode $webResponse.StatusCode `
      -Details 'No JavaScript asset was found in the public index.'
  }
  else {
    $bundleUrl = "$WebBaseUrl/$($assetMatch.Value)"
    $bundleResponse = Invoke-PublicRequest -Url $bundleUrl
    $bundleText = $bundleResponse.Body
    $bundleOk = $bundleResponse.StatusCode -ge 200 -and $bundleResponse.StatusCode -lt 300
    Add-Check -Name 'web.bundle' -Url $bundleUrl -Ok $bundleOk -StatusCode $bundleResponse.StatusCode `
      -Details ("bytes={0}; sha256={1}" -f `
        ([Text.Encoding]::UTF8.GetByteCount($bundleText)),
        ([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash([Text.Encoding]::UTF8.GetBytes($bundleText))).Replace('-', '').ToLowerInvariant()))
    $ctPreviewOk = $bundleText.Contains('CT ANATOMY PREVIEW')
    Add-Check -Name 'web.bundle.ct_preview_controls' -Url $bundleUrl -Ok $ctPreviewOk `
      -StatusCode $bundleResponse.StatusCode -Details ("ct_preview_controls_present={0}" -f $ctPreviewOk)
    # Use ASCII route/API markers here. Windows PowerShell 5.1 can decode the
    # UTF-8 native curl stream with the active console code page, which makes
    # Vietnamese UI literals unreliable even when the deployed bundle is valid.
    $organizationLifecycleUiOk = $bundleText.Contains('/invite') `
      -and $bundleText.Contains('organization-invitations') `
      -and $bundleText.Contains('/organizations/invitations/accept')
    Add-Check -Name 'web.bundle.organization_membership_ui' -Url $bundleUrl -Ok $organizationLifecycleUiOk `
      -StatusCode $bundleResponse.StatusCode -Details ("member_invitation_route_markers_present={0}" -f $organizationLifecycleUiOk)
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
