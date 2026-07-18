# Install Read Aloud desktop app on Windows.
# Usage (from repo root or this folder):
#   powershell -ExecutionPolicy Bypass -File windows\install-windows.ps1
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WinDir = $PSScriptRoot
$VenvPython = Join-Path $Root "venv\Scripts\python.exe"
$VenvPythonw = Join-Path $Root "venv\Scripts\pythonw.exe"
$VenvPip = Join-Path $Root "venv\Scripts\pip.exe"
$GuiScript = Join-Path $WinDir "read-aloud-gui-win.py"
# Must live next to the venv Scripts so pythonw can find ..\pyvenv.cfg
$LauncherExe = Join-Path $Root "venv\Scripts\ReadAloud.exe"
$BrokenLauncher = Join-Path $WinDir "ReadAloud.exe"
$IconPng = Join-Path $Root "browser-extension-store\icons\icon128.png"
$IconIco = Join-Path $WinDir "read-aloud.ico"
$Rcedit = Join-Path $WinDir "rcedit-x64.exe"
$SetLnkCs = Join-Path $WinDir "SetLnkAppId.cs"
$SetLnkExe = Join-Path $WinDir "SetLnkAppId.exe"
$AppId = "Beanwl.ReadAloud"
$ExtensionDir = Join-Path $Root "browser-extension-store"

Write-Host "Installing Read Aloud (Windows) from $Root"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python was not found on PATH. Install Python 3.10+ from https://www.python.org/downloads/"
}

if (-not (Test-Path $VenvPython)) {
  Write-Host "Creating virtual environment..."
  python -m venv (Join-Path $Root "venv")
}

Write-Host "Installing Python dependencies..."
& $VenvPip install -r (Join-Path $Root "requirements.txt") | Out-Null

function New-MultiSizeIco {
  param([string]$PngPath, [string]$IcoPath)
  Add-Type -AssemblyName System.Drawing
  $src = [System.Drawing.Bitmap]::FromFile($PngPath)
  $sizes = @(16, 32, 48, 64, 128, 256)
  $ms = New-Object System.IO.MemoryStream
  $bw = New-Object System.IO.BinaryWriter $ms
  $bw.Write([uint16]0)
  $bw.Write([uint16]1)
  $bw.Write([uint16]$sizes.Count)
  $offset = 6 + (16 * $sizes.Count)
  $images = @()
  foreach ($size in $sizes) {
    $bmp = New-Object System.Drawing.Bitmap $size, $size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($src, 0, 0, $size, $size)
    $g.Dispose()
    $imgMs = New-Object System.IO.MemoryStream
    $bmp.Save($imgMs, [System.Drawing.Imaging.ImageFormat]::Png)
    $bytes = $imgMs.ToArray()
    $imgMs.Dispose()
    $bmp.Dispose()
    $images += , @($size, $bytes)
  }
  foreach ($img in $images) {
    $size = $img[0]
    $bytes = $img[1]
    $bw.Write([byte]$(if ($size -ge 256) { 0 } else { $size }))
    $bw.Write([byte]$(if ($size -ge 256) { 0 } else { $size }))
    $bw.Write([byte]0)
    $bw.Write([byte]0)
    $bw.Write([uint16]1)
    $bw.Write([uint16]32)
    $bw.Write([uint32]$bytes.Length)
    $bw.Write([uint32]$offset)
    $offset += $bytes.Length
  }
  foreach ($img in $images) { $bw.Write($img[1]) }
  $bw.Flush()
  [System.IO.File]::WriteAllBytes($IcoPath, $ms.ToArray())
  $bw.Dispose()
  $ms.Dispose()
  $src.Dispose()
}

if ((Test-Path $IconPng) -and (-not (Test-Path $IconIco) -or (Get-Item $IconIco).Length -lt 1000)) {
  Write-Host "Building icon..."
  New-MultiSizeIco -PngPath $IconPng -IcoPath $IconIco
}

if (-not (Test-Path $Rcedit)) {
  Write-Host "Downloading rcedit (for taskbar icon)..."
  Invoke-WebRequest -Uri "https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe" `
    -OutFile $Rcedit -UseBasicParsing
}

Write-Host "Building ReadAloud.exe launcher..."
# Remove old broken copy outside the venv (causes "No pyvenv.cfg file")
if (Test-Path $BrokenLauncher) {
  Remove-Item -Force $BrokenLauncher
}
Copy-Item -Force $VenvPythonw $LauncherExe
& $Rcedit $LauncherExe --set-icon $IconIco

if (-not (Test-Path $SetLnkExe)) {
  $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
  if (-not (Test-Path $csc)) {
    $csc = Get-ChildItem "$env:WINDIR\Microsoft.NET\Framework*\*\csc.exe" -ErrorAction SilentlyContinue |
      Select-Object -First 1 -ExpandProperty FullName
  }
  if (-not $csc) { throw "Could not find csc.exe to build shortcut helper." }
  & $csc /nologo /target:exe /out:$SetLnkExe $SetLnkCs
}

function Update-ReadAloudShortcut {
  param([string]$Path)
  $dir = Split-Path $Path
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
  & $SetLnkExe $Path $LauncherExe "`"$GuiScript`"" $Root $IconIco $AppId | Out-Null
}

$desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "Read Aloud.lnk"
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Read Aloud.lnk"
$pinned = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Read Aloud.lnk"

Update-ReadAloudShortcut $desktop
Update-ReadAloudShortcut $startMenu
Update-ReadAloudShortcut $pinned
Write-Host "Created Desktop, Start Menu, and taskbar shortcuts."

# Best-effort pin verb (often unavailable on Windows 11)
try {
  Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ShellPin {
  [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
  public static extern IntPtr ShellExecuteW(IntPtr hwnd, string lpOperation, string lpFile, string lpParameters, string lpDirectory, int nShowCmd);
}
"@
  [void][ShellPin]::ShellExecuteW([IntPtr]::Zero, "taskbarpin", $desktop, $null, $null, 0)
} catch { }

Write-Host ""
Write-Host "Speak Selection (browser extension, optional):"
Write-Host "  1) Open chrome://extensions"
Write-Host "  2) Enable Developer mode"
Write-Host "  3) Load unpacked -> $ExtensionDir"
Write-Host ""

Write-Host "Launching Read Aloud..."
Start-Process -FilePath $LauncherExe -ArgumentList "`"$GuiScript`"" -WorkingDirectory $Root

Write-Host "Done. Use the Desktop or taskbar 'Read Aloud' shortcut to open it again."
