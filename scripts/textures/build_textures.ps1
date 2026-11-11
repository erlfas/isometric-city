<#
  Rebuilds public/textures/ from texture_sources/ (picked hero images) + procedural recipes.

    powershell -ExecutionPolicy Bypass -File scripts\textures\build_textures.ps1

  texture_sources/ is git-ignored (70 MB of originals) - keep a backup. The processed
  1024 px outputs in public/textures/ are committed.
#>
param(
  [string]$Python = "C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe",
  [string]$WorkDir = (Join-Path $env:TEMP "lublin_texture_build")
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$conv = Join-Path $PSScriptRoot 'convert_image.ps1'
$src = Join-Path $WorkDir 'src'
$out = Join-Path $WorkDir 'out'
$dest = Join-Path $repo 'public\textures'

# Picked variant per hero texture (see docs/material_board and the review in Phase 2).
$picks = [ordered]@{
  'brick_gothic_a' = 'brick_gothic\v1.jpg'
  'brick_gothic_b' = 'brick_gothic\v3.jpg'
  'roof_tile_red'  = 'roof_tile_red\v2.jpg'
  'log_wall'       = 'log_wall\v1.jpg'
  'wood_shingle'   = 'wood_shingle\v3.jpg'
  'thatch'         = 'thatch\v3.jpg'
  'fieldstone'     = 'fieldstone\v1.jpg'
}

Remove-Item $WorkDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $src, $out, $dest | Out-Null

foreach ($k in $picks.Keys) {
  $in = Join-Path $repo "texture_sources\$($picks[$k])"
  if (-not (Test-Path $in)) { throw "Missing source $in" }
  & powershell -NoProfile -ExecutionPolicy Bypass -File $conv -In $in -Out (Join-Path $src "$k.bmp")
}

& $Python -I (Join-Path $PSScriptRoot 'build_textures.py') $src $out
if ($LASTEXITCODE -ne 0) { throw "build_textures.py failed" }

Get-ChildItem $out -Filter '*_albedo.bmp' | ForEach-Object {
  $id = $_.Name -replace '_albedo\.bmp$', ''
  & powershell -NoProfile -ExecutionPolicy Bypass -File $conv -In $_.FullName -Out (Join-Path $dest "${id}_albedo.jpg") -Quality 90
  & powershell -NoProfile -ExecutionPolicy Bypass -File $conv -In (Join-Path $out "${id}_normal.bmp") -Out (Join-Path $dest "${id}_normal.jpg") -Quality 95
}
Copy-Item (Join-Path $out 'manifest.json') (Join-Path $dest 'manifest.json') -Force

$total = (Get-ChildItem $dest -File | Measure-Object Length -Sum).Sum / 1MB
"public/textures: $((Get-ChildItem $dest -Filter *.jpg).Count) images, {0:N1} MB" -f $total
