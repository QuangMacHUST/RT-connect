param(
  [switch]$WithContainers,
  [ValidateRange(30, 3600)]
  [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$apiPython = "$root\apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $apiPython)) { $apiPython = 'python' }
$dockerCommand = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $dockerCommand) {
  $userDockerCommand = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
  if (Test-Path $userDockerCommand) { $dockerCommand = $userDockerCommand }
}
if ($dockerCommand) {
  $dockerBin = Split-Path -Parent $dockerCommand
  if (($env:Path -split ';') -notcontains $dockerBin) { $env:Path = "$dockerBin;$env:Path" }
}

function Assert-NativeSuccess([string]$step) {
  if ($LASTEXITCODE -ne 0) {
    throw "$step failed with exit code $LASTEXITCODE."
  }
}

$logRoot = Join-Path ([System.IO.Path]::GetTempPath()) "rt-connect-p1-$PID"
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Redact-CommandOutput([string]$value) {
  if ($null -eq $value) { return '' }
  $value = $value -replace '(?i)(postgres(?:ql)?://[^:\s/]+:)[^@\s]+(@)', '$1<redacted>$2'
  $value = $value -replace '(?i)(bearer\s+)[A-Za-z0-9._-]+', '$1<redacted>'
  return $value -replace '(?i)(--?(?:token|password|secret|key)[=\s]+)\S+', '$1<redacted>'
}

function Invoke-CheckedProcess {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][string]$Step
  )

  $safeName = ($Step -replace '[^A-Za-z0-9_-]', '-')
  $stdoutPath = Join-Path $logRoot "$safeName-$PID.out.log"
  $stderrPath = Join-Path $logRoot "$safeName-$PID.err.log"
  $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory `
    -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -WindowStyle Hidden
  try {
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
      if (-not $process.HasExited) {
        try { $process.Kill($true) } catch { $process.Kill() }
      }
      throw "$Step exceeded timeout ${TimeoutSeconds}s."
    }
    if (Test-Path $stdoutPath) { Redact-CommandOutput (Get-Content $stdoutPath -Raw) }
    if (Test-Path $stderrPath) { Redact-CommandOutput (Get-Content $stderrPath -Raw) }
    if ($process.ExitCode -ne 0) {
      throw "$Step failed with exit code $($process.ExitCode)."
    }
  }
  finally {
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
  }
}

try {
  $npmExecutable = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
  if (-not $npmExecutable) { $npmExecutable = (Get-Command npm -ErrorAction Stop).Source }

Push-Location "$root\apps\api"
Invoke-CheckedProcess -FilePath $apiPython -Arguments @('-m', 'pytest') -WorkingDirectory (Get-Location) -Step 'API tests'
Invoke-CheckedProcess -FilePath $apiPython -Arguments @('-m', 'ruff', 'check', 'src', 'tests') -WorkingDirectory (Get-Location) -Step 'API lint'
Invoke-CheckedProcess -FilePath $apiPython -Arguments @('-m', 'mypy', 'src') -WorkingDirectory (Get-Location) -Step 'API typecheck'
Invoke-CheckedProcess -FilePath $apiPython -Arguments @('-m', 'alembic', 'upgrade', 'head', '--sql') -WorkingDirectory (Get-Location) -Step 'API migration SQL generation'
Pop-Location

Push-Location "$root\apps\web"
Invoke-CheckedProcess -FilePath $npmExecutable -Arguments @('run', 'lint') -WorkingDirectory (Get-Location) -Step 'Web lint'
Invoke-CheckedProcess -FilePath $npmExecutable -Arguments @('run', 'typecheck') -WorkingDirectory (Get-Location) -Step 'Web typecheck'
Invoke-CheckedProcess -FilePath $npmExecutable -Arguments @('run', 'test') -WorkingDirectory (Get-Location) -Step 'Web tests'
Invoke-CheckedProcess -FilePath $npmExecutable -Arguments @('run', 'build') -WorkingDirectory (Get-Location) -Step 'Web build'
Pop-Location

if ($WithContainers) {
  if (-not $dockerCommand) { throw 'Docker CLI is required for -WithContainers.' }
  $composeArguments = @('compose', '-f', "$root\docker-compose.yml")
  try {
    Invoke-CheckedProcess -FilePath $dockerCommand -Arguments (@($composeArguments) + @('up', '--build', '--wait')) -WorkingDirectory $root -Step 'Docker Compose startup/health'
    Invoke-CheckedProcess -FilePath $dockerCommand -Arguments (@($composeArguments) + @('exec', '-T', 'api', 'alembic', 'upgrade', 'head')) -WorkingDirectory $root -Step 'Alembic migration inside the API container'
    Invoke-CheckedProcess -FilePath $dockerCommand -Arguments (@($composeArguments) + @('exec', '-T', 'api', 'python', '-m', 'rt_connect_api.cli', 'seed-synthetic')) -WorkingDirectory $root -Step 'Synthetic seed inside the API container'
    $seedCount = & $dockerCommand @composeArguments exec -T postgres psql -U rt_connect -d rt_connect -tAc 'SELECT count(*) FROM machines;'
    if ($LASTEXITCODE -ne 0 -or [int]$seedCount -lt 1) { throw 'Synthetic machine seed was not persisted.' }
    $health = Invoke-RestMethod 'http://localhost:8000/api/v1/health' -TimeoutSec $TimeoutSeconds
    if ($health.status -ne 'ok') { throw 'API health did not return ok.' }
    $readiness = Invoke-RestMethod 'http://localhost:8000/api/v1/ready' -TimeoutSec $TimeoutSeconds
    if ($readiness.status -ne 'ready') { throw 'API readiness did not return ready.' }
    Invoke-WebRequest 'http://localhost:5173/health' -UseBasicParsing -TimeoutSec $TimeoutSeconds | Out-Null
  }
  finally {
    & $dockerCommand @composeArguments down -v
  }
}
}
finally {
  Remove-Item -LiteralPath $logRoot -Recurse -Force -ErrorAction SilentlyContinue
}
