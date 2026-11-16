# =========================================================================
# PK Transport - one-time installer of the app itself (called by install.bat; do not run it by hand)
#   1. Python 3.12 (installed for the current user when missing)
#   2. A private Python environment in .venv (nothing is installed into the system Python)
#   3. The modules you ask for with -Modules (PKT Data, PKT Train, PKT Analyze: each with its libraries; PyTorch for the GPU or the CPU).
#      Without -Modules nothing heavy is downloaded: choose the modules later on the Modules page of the app.
#   4. Desktop + Start Menu shortcuts, then PK Transport is opened
# The app itself needs only Python's standard library, so this takes a minute or two.
#
# Switches:
#   -Modules data,train,analyze   install these modules now (names: data, train, analyze; or "all"). A version: data@1.4.0
#   -DryRun       only print what would be done
#   -ForceCpu     install the CPU build of PyTorch even when an NVIDIA GPU is found
#   -NoLaunch     do not open the app at the end
#   -NoShortcuts  do not create shortcuts
# =========================================================================
param(
    [string]$Modules = "",
    [switch]$DryRun,
    [switch]$ForceCpu,
    [switch]$NoLaunch,
    [switch]$NoShortcuts
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$VenvDir = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPythonW = Join-Path $VenvDir "Scripts\pythonw.exe"

function Write-Step($msg) { Write-Host ""; Write-Host "===> $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "!! $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "XX $msg" -ForegroundColor Red }
function Stop-Install($msg) {
    Write-Err $msg
    if (-not $DryRun) { Read-Host "Press Enter to close this window" | Out-Null }
    exit 1
}

# ------------------------------------------------------------------ 1. Python 3.12
Write-Step "Step 1/4: Python 3.12"
$havePython = $false
try {
    $v = & py -3.12 --version 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Host "Found $v"; $havePython = $true }
} catch { $havePython = $false }

if (-not $havePython) {
    Write-Warn "Python 3.12 was not found. Downloading the official installer (a few minutes) ..."
    if ($DryRun) {
        Write-Host "[dry run] download and install Python 3.12.7 for the current user"
    } else {
        $url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
        $installer = Join-Path $env:TEMP "python-3.12.7-installer.exe"
        Invoke-WebRequest -Uri $url -OutFile $installer
        $sig = Get-AuthenticodeSignature -FilePath $installer
        if ($sig.Status -ne "Valid" -or $sig.SignerCertificate.Subject -notmatch "Python Software Foundation") {
            Remove-Item $installer -Force -ErrorAction SilentlyContinue
            Stop-Install "The downloaded Python installer failed its signature check. Install Python 3.12 from python.org and run install.bat again."
        }
        Start-Process -FilePath $installer -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_launcher=1" -Wait
        Remove-Item $installer -ErrorAction SilentlyContinue
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
        try { $v = & py -3.12 --version 2>&1; if ($LASTEXITCODE -ne 0) { throw "no" } } catch {
            Stop-Install "Python 3.12 was installed but cannot be started yet. Close this window and run install.bat again."
        }
        Write-Host "Installed $v"
    }
}

# ------------------------------------------------------------------ 2. environment
Write-Step "Step 2/4: Private Python environment (.venv)"
if (Test-Path $VenvPython) {
    Write-Host ".venv already exists - it is reused."
} elseif ($DryRun) {
    Write-Host "[dry run] py -3.12 -m venv .venv"
} else {
    & py -3.12 -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) { Stop-Install "Could not create the Python environment (.venv)." }
    & $VenvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null
}

# ------------------------------------------------------------------ 3. modules
Write-Step "Step 3/4: Modules"
$wanted = @()
if ($Modules.Trim().ToLower() -eq "all") { $wanted = @("data", "train", "analyze") }
elseif ($Modules.Trim() -ne "") { $wanted = $Modules.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
$bundled = @(Get-ChildItem -Path (Join-Path $Root "modules") -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName "pkt_module.json") })
if ($wanted.Count -eq 0 -and $bundled.Count -gt 0) {
    Write-Host "Modules that came with this folder: $($bundled.Name -join ', ') - installing their libraries ..."
    if ($DryRun) { Write-Host "[dry run] python -m pkt.modman prepare" }
    else {
        if ($ForceCpu) { $env:PKT_FORCE_CPU = "1" }
        & $VenvPython -m pkt.modman prepare
        if ($LASTEXITCODE -ne 0) { Write-Warn "The libraries of a module could not be installed (see above). Use the Modules page of the app to try again (Reinstall)." }
    }
} elseif ($wanted.Count -eq 0) {
    Write-Host "No module requested: open PK Transport and choose them on the Modules page (PKT Data, PKT Train, PKT Analyze)."
} elseif ($DryRun) {
    Write-Host "[dry run] python -m pkt.modman install $($wanted -join ' ')"
} else {
    if ($ForceCpu) { $env:PKT_FORCE_CPU = "1" }
    & $VenvPython -m pkt.modman install @wanted
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "A module could not be installed (see above). The app still opens: use its Modules page to try again."
    }
}

# ------------------------------------------------------------------ 4. shortcuts
Write-Step "Step 4/4: Shortcuts"
if ($NoShortcuts -or $DryRun) {
    Write-Host "(skipped)"
} else {
    try {
        $wsh = New-Object -ComObject WScript.Shell
        $icon = Join-Path $Root "assets\icon.ico"
        foreach ($dir in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("StartMenu"))) {
            $lnk = $wsh.CreateShortcut((Join-Path $dir "PK Transport.lnk"))
            $lnk.TargetPath = $VenvPythonW
            $lnk.Arguments = '"' + (Join-Path $Root "main.py") + '"'
            $lnk.WorkingDirectory = $Root
            if (Test-Path $icon) { $lnk.IconLocation = $icon }
            $lnk.Description = "PK Transport"
            $lnk.Save()
        }
        Write-Host "Shortcuts created on the Desktop and in the Start Menu (search 'PK Transport')."
    } catch { Write-Warn "Could not create the shortcuts. Use run_pk_transport.bat instead." }
}

Write-Step "Done."
if (-not $NoLaunch -and -not $DryRun) {
    Write-Host "Opening PK Transport ..."
    Start-Process -FilePath $VenvPythonW -ArgumentList ('"' + (Join-Path $Root "main.py") + '"') -WorkingDirectory $Root
}
