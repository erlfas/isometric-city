# Lublin Anno Domini 1392: Windows environment check & setup (Windows PowerShell 5.1+).
#   powershell -ExecutionPolicy Bypass -File scripts\setup_environment.ps1
# Installs node_modules, enables the pre-commit hook, prints tool paths. Missing tools are
# reported with their winget install command; nothing is installed system-wide.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$missing = @()

function Find-Tool($name, $candidates) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($c in $candidates) { $hit = Get-Item $c -ErrorAction SilentlyContinue | Select-Object -Last 1; if ($hit) { return $hit.FullName } }
    return $null
}

$git = Find-Tool 'git' @("$env:LOCALAPPDATA\GitHubDesktop\app-*\resources\app\git\cmd\git.exe", 'C:\Program Files\Git\cmd\git.exe')
$node = Find-Tool 'node' @('C:\Program Files\nodejs\node.exe')
$blender = Find-Tool 'blender' @('C:\Program Files\Blender Foundation\Blender*\blender.exe')
$py = $null
if ($blender) { $py = Get-Item (Join-Path (Split-Path $blender) '*\python\bin\python.exe') -ErrorAction SilentlyContinue | Select-Object -Last 1 -ExpandProperty FullName }
$standalonePy = Find-Tool 'python' @()
if ($standalonePy -and $standalonePy -notlike '*WindowsApps*') { $py = $standalonePy }

if (-not $git) { $missing += 'git      -> winget install Git.Git' }
if (-not $node) { $missing += 'node     -> winget install OpenJS.NodeJS.LTS' }
if (-not $blender) { $missing += 'blender  -> winget install BlenderFoundation.Blender' }

if ($node) {
    $env:Path = (Split-Path $node) + ';' + $env:Path
    if (-not (Test-Path node_modules)) { Write-Host 'Installing Node.js dependencies...'; npm install }
    else { Write-Host 'node_modules present.' }
}
if ($git) {
    & $git config core.hooksPath .githooks
    Write-Host 'Pre-commit hook enabled (core.hooksPath = .githooks).'
}

Write-Host ''
Write-Host "git      : $git"
Write-Host "node     : $node"
Write-Host "BLENDER  : $blender"
Write-Host "PY       : $py"
if ($missing.Count) {
    Write-Host ''
    Write-Host 'Missing tools:' -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}
Write-Host 'Environment OK.' -ForegroundColor Green
