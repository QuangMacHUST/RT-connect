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

function Convert-CgroupMemoryValueToBytes {
  param([AllowNull()][string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
  $trimmed = $Value.Trim()
  if ($trimmed -eq 'max') { return $null }
  if ($trimmed -notmatch '^[0-9]+$') { return $null }
  $number = [long]::Parse($trimmed, [Globalization.CultureInfo]::InvariantCulture)
  if ($number -ge [long]::MaxValue / 2) { return $null }
  return $number
}

function Get-ContainerCgroupMemory {
  $probe = @'
if [ -f /sys/fs/cgroup/memory.peak ]; then
  printf '%s\n' 'cgroup_version=v2'
  printf '%s=' 'memory_limit_bytes'; cat /sys/fs/cgroup/memory.max; printf '\n'
  printf '%s=' 'memory_current_bytes'; cat /sys/fs/cgroup/memory.current; printf '\n'
  printf '%s=' 'memory_peak_bytes'; cat /sys/fs/cgroup/memory.peak; printf '\n'
elif [ -f /sys/fs/cgroup/memory/memory.max_usage_in_bytes ]; then
  printf '%s\n' 'cgroup_version=v1'
  printf '%s=' 'memory_limit_bytes'; cat /sys/fs/cgroup/memory/memory.limit_in_bytes; printf '\n'
  printf '%s=' 'memory_current_bytes'; cat /sys/fs/cgroup/memory/memory.usage_in_bytes; printf '\n'
  printf '%s=' 'memory_peak_bytes'; cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes; printf '\n'
else
  printf '%s\n' 'cgroup_version=unknown'
fi
'@
  try {
    $raw = Invoke-Docker -Arguments @('exec', $containerName, 'sh', '-c', $probe)
  }
  catch {
    return [ordered]@{
      available = $false
      error = $_.Exception.Message
      is_peak_rss = $false
    }
  }
  $values = @{}
  foreach ($line in ($raw -split "`r?`n")) {
    $match = [regex]::Match($line, '^(?<key>[a-z_]+)=(?<value>.*)$')
    if ($match.Success) { $values[$match.Groups['key'].Value] = $match.Groups['value'].Value }
  }
  $version = if ($values.ContainsKey('cgroup_version')) { [string]$values['cgroup_version'] } else { 'unknown' }
  $peakMetric = if ($version -eq 'v2') { 'memory.peak' } elseif ($version -eq 'v1') { 'memory.max_usage_in_bytes' } else { $null }
  return [ordered]@{
    available = $version -in @('v1', 'v2')
    cgroup_version = $version
    memory_limit_bytes = if ($values.ContainsKey('memory_limit_bytes')) { Convert-CgroupMemoryValueToBytes $values['memory_limit_bytes'] } else { $null }
    memory_current_bytes = if ($values.ContainsKey('memory_current_bytes')) { Convert-CgroupMemoryValueToBytes $values['memory_current_bytes'] } else { $null }
    memory_peak_bytes = if ($values.ContainsKey('memory_peak_bytes')) { Convert-CgroupMemoryValueToBytes $values['memory_peak_bytes'] } else { $null }
    peak_metric = $peakMetric
    peak_scope = 'since_container_start'
    is_peak_rss = $false
  }
}

function Get-ContainerResourcePolicy {
  $raw = Invoke-Docker -Arguments @(
    'inspect', $containerName, '--format',
    '{{.HostConfig.Memory}}|{{.HostConfig.NanoCpus}}|{{.HostConfig.CpuQuota}}|{{.HostConfig.CpuPeriod}}'
  )
  $parts = $raw.Trim() -split '\|', 4
  if ($parts.Count -ne 4) { throw "Could not read resource policy for $containerName." }
  $memoryBytes = [long]::Parse($parts[0], [Globalization.CultureInfo]::InvariantCulture)
  $nanoCpus = [long]::Parse($parts[1], [Globalization.CultureInfo]::InvariantCulture)
  $cpuQuota = [long]::Parse($parts[2], [Globalization.CultureInfo]::InvariantCulture)
  $cpuPeriod = [long]::Parse($parts[3], [Globalization.CultureInfo]::InvariantCulture)
  $cpuLimit = if ($nanoCpus -gt 0) {
    [double]$nanoCpus / 1000000000.0
  }
  elseif ($cpuQuota -gt 0 -and $cpuPeriod -gt 0) {
    [double]$cpuQuota / [double]$cpuPeriod
  }
  else {
    $null
  }
  return [ordered]@{
    memory_limit_bytes = if ($memoryBytes -gt 0) { $memoryBytes } else { $null }
    cpu_limit = $cpuLimit
    nano_cpus = if ($nanoCpus -gt 0) { $nanoCpus } else { $null }
    cpu_quota = if ($cpuQuota -gt 0) { $cpuQuota } else { $null }
    cpu_period = if ($cpuPeriod -gt 0) { $cpuPeriod } else { $null }
    source = 'docker inspect HostConfig'
  }
}

function Invoke-ApiHealthProbe {
  $stopwatch = [Diagnostics.Stopwatch]::StartNew()
  try {
    $payload = Invoke-RestMethod 'http://localhost:8000/api/v1/health' -TimeoutSec 2
    $stopwatch.Stop()
    return [ordered]@{
      captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
      ok = ([string]$payload.status -eq 'ok')
      status = [string]$payload.status
      latency_ms = [math]::Round($stopwatch.Elapsed.TotalMilliseconds, 3)
      error = $null
    }
  }
  catch {
    $stopwatch.Stop()
    return [ordered]@{
      captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
      ok = $false
      status = $null
      latency_ms = [math]::Round($stopwatch.Elapsed.TotalMilliseconds, 3)
      error = $_.Exception.Message
    }
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
$resourcePolicy = Get-ContainerResourcePolicy
$cgroupBefore = Get-ContainerCgroupMemory
$apiProbes = [System.Collections.Generic.List[object]]::new()
$apiProbes.Add((Invoke-ApiHealthProbe))

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
    $apiProbes.Add((Invoke-ApiHealthProbe))
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
$apiProbes.Add((Invoke-ApiHealthProbe))
$cgroupAfter = Get-ContainerCgroupMemory

$memoryValues = @($samples | Where-Object { $null -ne $_.memory_bytes } | ForEach-Object { [long]$_.memory_bytes })
$rssValues = @(
  $jobResults |
    ForEach-Object { $_.observations } |
    ForEach-Object { $_.peak_rss_bytes } |
    Where-Object { $null -ne $_ } |
    ForEach-Object { [long]$_ }
)
$elapsedValues = @(
  $jobResults |
    ForEach-Object { $_.observations } |
    ForEach-Object { [double]$_.elapsed_seconds }
)
$latencyValues = @(
  $apiProbes |
    Where-Object { $_.ok -and $null -ne $_.latency_ms } |
    ForEach-Object { [double]$_.latency_ms }
)
$failedApiProbes = @($apiProbes | Where-Object { -not $_.ok })
$p95Latency = $null
if ($latencyValues.Count -gt 0) {
  $orderedLatencies = @($latencyValues | Sort-Object)
  $p95Index = [math]::Max(0, [math]::Ceiling($orderedLatencies.Count * 0.95) - 1)
  $p95Latency = $orderedLatencies[$p95Index]
}
$memoryLimitBytes = $resourcePolicy.memory_limit_bytes
$rssBudgetBytes = if ($null -ne $memoryLimitBytes) {
  [long][math]::Floor([double]$memoryLimitBytes * 0.8)
}
else {
  $null
}
$maxRssBytes = if ($rssValues.Count -gt 0) { ($rssValues | Measure-Object -Maximum).Maximum } else { $null }
$maxElapsedSeconds = if ($elapsedValues.Count -gt 0) { ($elapsedValues | Measure-Object -Maximum).Maximum } else { $null }
$resourceEvidenceAvailable = (
  $rssValues.Count -eq ($ConcurrentJobs * $RepeatsPerJob) -and
  $null -ne $memoryLimitBytes -and
  $memoryLimitBytes -gt 0 -and
  $null -ne $resourcePolicy.cpu_limit -and
  [double]$resourcePolicy.cpu_limit -gt 0
)
$resourceBudgetPassed = (
  $resourceEvidenceAvailable -and
  $null -ne $rssBudgetBytes -and
  [long]$maxRssBytes -lt [long]$rssBudgetBytes -and
  $null -ne $maxElapsedSeconds -and
  [double]$maxElapsedSeconds -le ($TimeoutMinutes * 60)
)
$apiResponsivenessPassed = (
  $apiProbes.Count -gt 0 -and
  $failedApiProbes.Count -eq 0 -and
  $null -ne $p95Latency -and
  [double]$p95Latency -le 1000
)
$performanceGate = if (-not $resourceEvidenceAvailable) {
  'NOT_ASSESSED'
}
elseif (-not $resourceBudgetPassed -or -not $apiResponsivenessPassed) {
  'LOCAL_RESOURCE_GATE_FAIL'
}
else {
  'LOCAL_RESOURCE_GATE_PASS'
}
$sourceSha = (git -C $root rev-parse HEAD).Trim()
$cgroupPeakBytes = $cgroupAfter['memory_peak_bytes']
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
    resource_policy = $resourcePolicy
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
  cgroup_memory_observation = [ordered]@{
    before_workload = $cgroupBefore
    after_workload = $cgroupAfter
    peak_bytes_since_container_start = $cgroupPeakBytes
    is_peak_rss = $false
  }
  process_rss_observation = [ordered]@{
    measurement_source = 'resource.getrusage(RUSAGE_SELF).ru_maxrss'
    peak_rss_bytes_max = $maxRssBytes
    observation_count = $rssValues.Count
    is_peak_rss = ($rssValues.Count -gt 0)
  }
  api_responsiveness = [ordered]@{
    probe_url = 'http://localhost:8000/api/v1/health'
    sample_count = $apiProbes.Count
    error_count = $failedApiProbes.Count
    p95_latency_ms = $p95Latency
    max_latency_ms = if ($latencyValues.Count -gt 0) { ($latencyValues | Measure-Object -Maximum).Maximum } else { $null }
    samples = $apiProbes
    passed = $apiResponsivenessPassed
  }
  performance_budget = [ordered]@{
    rss_limit_fraction = 0.8
    rss_budget_bytes = $rssBudgetBytes
    max_elapsed_seconds = $maxElapsedSeconds
    elapsed_budget_seconds = $TimeoutMinutes * 60
    resource_budget_passed = $resourceBudgetPassed
    api_responsiveness_passed = $apiResponsivenessPassed
  }
  performance_gate = $performanceGate
  passed = (
    $health.status -eq 'ok' -and
    $readiness.status -eq 'ready' -and
    @($jobResults | Where-Object { $_.engine_version -ne 'p17-dvh-1.1.0' }).Count -eq 0 -and
    $performanceGate -ne 'LOCAL_RESOURCE_GATE_FAIL'
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
