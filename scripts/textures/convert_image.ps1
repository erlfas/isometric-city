param(
  [Parameter(Mandatory)] [string]$In,
  [Parameter(Mandatory)] [string]$Out,
  [int]$Size = 0,          # resize to Size x Size (0 = keep)
  [int]$Quality = 90       # JPEG quality when Out ends in .jpg
)
# Image format bridge for the texture pipeline (no Pillow on this machine):
#   source .jpg/.png  -> 24-bit .bmp (optionally resized)  for numpy processing
#   processed .bmp    -> .jpg (with quality) or .png         for the runtime
Add-Type -AssemblyName System.Drawing
$src = [System.Drawing.Image]::FromFile((Resolve-Path $In).Path)
$w = if ($Size -gt 0) { $Size } else { $src.Width }
$h = if ($Size -gt 0) { $Size } else { $src.Height }
$bmp = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = 'HighQualityBicubic'
$g.PixelOffsetMode = 'HighQuality'
# TileFlipXY wrap mode avoids dark fringes at the borders when resampling.
$attr = New-Object System.Drawing.Imaging.ImageAttributes
$attr.SetWrapMode([System.Drawing.Drawing2D.WrapMode]::TileFlipXY)
$g.DrawImage($src, (New-Object System.Drawing.Rectangle 0, 0, $w, $h), 0, 0, $src.Width, $src.Height, [System.Drawing.GraphicsUnit]::Pixel, $attr)
$g.Dispose(); $src.Dispose()

$outFull = [System.IO.Path]::GetFullPath($Out)
New-Item -ItemType Directory -Force (Split-Path $outFull) | Out-Null
switch -Regex ($Out) {
  '\.jpe?g$' {
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
    $ep = New-Object System.Drawing.Imaging.EncoderParameters 1
    $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), ([long]$Quality)
    $bmp.Save($outFull, $codec, $ep)
  }
  '\.png$' { $bmp.Save($outFull, [System.Drawing.Imaging.ImageFormat]::Png) }
  '\.bmp$' { $bmp.Save($outFull, [System.Drawing.Imaging.ImageFormat]::Bmp) }
  default { throw "Unsupported output extension: $Out" }
}
$bmp.Dispose()
