param(
  [string]$Shape = '64x128x128',
  [ValidateRange(1, 20)]
  [int]$RepeatsPerJob = 3,
  [ValidateRange(1, 4)]
  [int]$ConcurrentJobs = 2,
  [ValidateRange(1, 10)]
  [int]$TimeoutMinutes = 5,
  [string]$OutputPath = 'docs/evidence/p17-local-docker-workload-20260909.json'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $root 'docker-compose.yml'
$benchmarkScript = Join-Path $root 'scripts/benchmark-p17-dvh.py'
$containerName = 'rt-connect-local-api-1'
$containerScript = '/tmp/benchmark-p17-dvh.py'

function Invoke-Docker {
  param([Parameter(Mandatory = $true)][string[]]$Arguments)
  $result = & docker @Arguments 2>&1 | Out-String
  if ($LASTEXITCODE -ne 0) {
    throw "Docker command failed: docker $($Arguments -join ' ')`n$($result.Trim())"
  }
  return $result.Trim()
}

function Convert-MemoryToBytes {
  param([Parameter(Mandatory = $true)][string]$Value)
  $match = [regex]::Match($Value.Trim(), '^(?<number>[0-9]+(?:\.[0-9]+)?)\s*(?<unit>[A-Za-z]+)$')
  if (-not $match.Success) { return $null }
  $number = [double]$match.Groups['number'].Value
  $unit = $match.Groups['unit'].Value.ToUpperInvariant()
  $multiplier = switch ($unit) {
    'B' { 1 }
    'KB' { 1000 }
    'KIB' { 1024 }
    'MB' { 1000 * 1000 }
    'MIB' { 1024 * 1024 }
    'GB' { 1000 * 1000 * 1000 }
    'GIB' { 1024 * 1024 * 1024 }
    default { return $null }
  }
  return [long][math]::Round($number * $multiplier)
}

function Get-ContainerMemorySample {
  $raw = & docker stats --no-stream --format '{{.MemUsage}}|{{.MemPerc}}' $containerName 2>$null | Out-String
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($raw)) { return $null }
  $parts = $raw.Trim() -split '\|', 2
  if ($parts.Count -ne 2) { return $null }
  $usage = ($parts[0] -split '/', 2)[0].Trim()
  $bytes = Convert-MemoryToBytes -Value $usage
  $percent = $null
  $percentMatch = [regex]::Match($parts[1].Trim(), '^(?<number>[0-9]+(?:\.[0-9]+)?)%$')
  if ($percentMatch.Success) { $percent = [double]$percentMatch.Groups['number'].Value }
  return [ordered]@{
    captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    memory_text = $usage
    memory_bytes = $bytes
    memory_percent = $percent
  }
}

function Start-BenchmarkJob {
  param([int]$JobNumber)
  $jobScript = {
    param($compose, $script, $shapeValue, $repeatValue, $number)
    $ErrorActionPreference = 'Stop'
    $raw = & docker compose -f $compose exec -T api python $script --shape $shapeValue --repeats $repeatValue 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
      throw "P17 Docker benchmark job $number failed: $($raw.Trim())"
    }
    $jsonMatch = [regex]::Match($raw, '(?s)\{.*\}')
    if (-not $jsonMatch.Success) {
      throw "P17 Docker benchmark job $number returned no JSON."
    }
    $payload = $jsonMatch.Value | ConvertFrom-Json
    [ordered]@{
      job_number = $number
      engine_version = [string]$payload.engine_version
      workload = $payload.workload
      result_oracle = $payload.result_oracle
      observations = $payload.observations
      summary = $payload.summary
    } | ConvertTo-Json -Depth 20 -Compress
  }
  return Start-Job -ArgumentList @($composeFile, $containerScript, $Shape, $RepeatsPerJob, $JobNumber) -ScriptBlock $jobScript
}

if (-not (Test-Path -LiteralPath $composeFile)) { throw "Compose file not found: $composeFile" }
if (-not (Test-Path -LiteralPath $benchmarkScript)) { throw "Benchmark script not found: $benchmarkScript" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI is required.' }

$services = Invoke-Docker -Arguments @('compose', '-f', $composeFile, 'ps', '--status', 'running', '--services')
if (-not (($services -split "`r?`n") -contains 'api')) {
  throw 'The API Compose service is not running. Start it with docker compose up -d --build api.'
}

Invoke-Docker -Arguments @('cp', $benchmarkScript, "$containerName`:$containerScript") | Out-Null
$imageDigest = Invoke-Docker -Arguments @('inspect', $containerName, '--format', '{{.Image}}')
$engineVersion = Invoke-Docker -Arguments @(
  'compose', '-f', $composeFile, 'exec', '-T', 'api', 'python', '-c',
  'from rt_connect_api.services.dose_dvh_engine import DVH_ENGINE_VERSION; print(DVH_ENGINE_VERSION)'
)
$health = Invoke-RestMethod 'http://localhost:8000/api/v1/health'
$readiness = Invoke-RestMethod 'http://localhost:8000/api/v1/ready'

$jobs = [System.Collections.Generic.List[object]]::new()
for ($index = 1; $index -le $ConcurrentJobs; $index++) {
  $jobs.Add((Start-BenchmarkJob -JobNumber $index))
}

$samples = [System.Collections.Generic.List[object]]::new()
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
try {
  while ($true) {
    $sample = Get-ContainerMemorySample
    if ($null -ne $sample) { $samples.Add($sample) }
    $states = @($jobs | ForEach-Object { (Get-Job -Id $_.Id).State })
    if (@($states | Where-Object { $_ -in @('Failed', 'Stopped') }).Count -gt 0) {
      $failedJobs = @($jobs | ForEach-Object { Get-Job -Id $_.Id } | Where-Object { $_.State -in @('Failed', 'Stopped') })
      $messages = $failedJobs | ForEach-Object { (Receive-Job -Job $_ -ErrorAction SilentlyContinue | Out-String).Trim() }
      throw "At least one concurrent benchmark job failed: $($messages -join ' | ')"
    }
    if (@($states | Where-Object { $_ -eq 'Running' }).Count -eq 0) { break }
    if ((Get-Date) -gt $deadline) { throw "Concurrent benchmark exceeded $TimeoutMinutes minute(s)." }
    Start-Sleep -Milliseconds 100
  }
  $jobResults = [System.Collections.Generic.List[object]]::new()
  foreach ($job in $jobs) {
    $payloadText = Receive-Job -Job $job -Wait -ErrorAction Stop | Out-String
    $jobResults.Add(($payloadText.Trim() | ConvertFrom-Json))
  }
}
finally {
  foreach ($job in $jobs) {
    Remove-Job -Id $job.Id -Force -ErrorAction SilentlyContinue
  }
}

$memoryValues = @($samples | Where-Object { $null -ne $_.memory_bytes } | ForEach-Object { [long]$_.memory_bytes })
$sourceSha = (git -C $root rev-parse HEAD).Trim()
$report = [ordered]@{
  schema_version = 'rt-connect.p17-docker-workload-verification.v1'
  captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
  repository_sha = $sourceSha
  execution = [ordered]@{
    compose_file = 'docker-compose.yml'
    service = 'api'
    image_digest = $imageDigest
    engine_version = $engineVersion
    health_status = [string]$health.status
    readiness_status = [string]$readiness.status
    schema_revision = [string]$readiness.schema_revision
  }
  workload = [ordered]@{
    shape = $Shape
    repeats_per_job = $RepeatsPerJob
    concurrent_jobs = $ConcurrentJobs
    patient_data = $false
  }
  job_results = $jobResults
  container_memory_sampling = [ordered]@{
    sample_count = $samples.Count
    max_sampled_bytes = if ($memoryValues.Count) { ($memoryValues | Measure-Object -Maximum).Maximum } else { $null }
    max_sampled_percent = if (@($samples | Where-Object { $null -ne $_.memory_percent }).Count) { (@($samples | ForEach-Object { $_.memory_percent }) | Measure-Object -Maximum).Maximum } else { $null }
    samples = $samples
    is_peak_rss = $false
  }
  performance_gate = 'NOT_ASSESSED'
  passed = (
    $health.status -eq 'ok' -and
    $readiness.status -eq 'ready' -and
    @($jobResults | Where-Object { $_.engine_version -ne 'p17-dvh-1.1.0' }).Count -eq 0
  )
}

$json = $report | ConvertTo-Json -Depth 30
$targetPath = if ([IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $root $OutputPath }
$targetDirectory = Split-Path -Parent $targetPath
if ($targetDirectory -and -not (Test-Path -LiteralPath $targetDirectory)) {
  New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
}
[IO.File]::WriteAllText($targetPath, $json, [Text.UTF8Encoding]::new($false))
$json
if (-not $report.passed) { exit 1 }
