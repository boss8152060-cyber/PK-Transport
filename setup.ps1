# =========================================================================
# PK Transport - one-time installer (called by install.bat; do not run it by hand)
#   1. Python 3.12 (installed for the current user when missing)
#   2. The three modules next to this file (PKT-Data, PKT-Train, PKT-Analyze\Run): used as they are when present
#      (e.g. from the portable zip), otherwise downloaded from GitHub
#   3. A private Python environment in .venv (nothing is installed into the system Python)
#   4. PyTorch: the CUDA build that matches the NVIDIA driver, or the CPU build when there is no NVIDIA GPU
#   5. ultralytics, opencv-python, pillow, pyyaml, matplotlib, numpy, albumentations
#   6. Desktop + Start Menu shortcuts, then PK Transport is opened
#
# Switches (for testing / special cases):
#   -DryRun       only print what would be done
#   -ForceCpu     install the CPU build of PyTorch even when an NVIDIA GPU is found
#   -NoLaunch     do not open the app at the end
#   -NoShortcuts  do not create shortcuts
# =========================================================================
param(
    [switch]$DryRun,
    [switch]$ForceCpu,
    [switch]$NoLaunch,
    [switch]$NoShortcuts
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Owner = "boss8152060-cyber"
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
function Invoke-Pip {
    param([string[]]$PipArgs)
    if ($DryRun) { Write-Host "[dry run] pip $($PipArgs -join ' ')"; return }
    & $VenvPython -m pip @PipArgs
    if ($LASTEXITCODE -ne 0) { throw "pip failed: $($PipArgs -join ' ')" }
}

# ------------------------------------------------------------------ 1. Python 3.12
Write-Step "Step 1/6: Python 3.12"
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

# ------------------------------------------------------------------ 2. modules
Write-Step "Step 2/6: PKT Data, PKT Train, PKT Analyze"
$modules = @(
    @{ Name = "PKT Data";    Repo = "PKT-Data";    Dir = "PKT-Data";         Marker = "main.py" },
    @{ Name = "PKT Train";   Repo = "PKT-Train";   Dir = "PKT-Train";        Marker = "README.md" },
    @{ Name = "PKT Analyze"; Repo = "PKT-Analyze"; Dir = "PKT-Analyze\Run"; Marker = "PKStudio.py" }
)
$haveGit = [bool](Get-Command git -ErrorAction SilentlyContinue)
$missing = @()
foreach ($m in $modules) {
    $folder = Join-Path $Root $m.Dir
    if (Test-Path (Join-Path $folder $m.Marker)) { Write-Host "$($m.Name): found ($($m.Dir))"; continue }
    if ($DryRun) { Write-Host "[dry run] $($m.Name): download from GitHub into $($m.Dir)"; continue }
    $ok = $false
    $repoUrl = "https://github.com/$Owner/$($m.Repo)"
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $folder) | Out-Null
        if ($haveGit) {
            $env:GIT_TERMINAL_PROMPT = "0"
            & git clone --quiet "$repoUrl.git" $folder 2>&1 | Out-Null
            $ok = ($LASTEXITCODE -eq 0) -and (Test-Path (Join-Path $folder $m.Marker))
        }
        if (-not $ok) {
            $zip = Join-Path $env:TEMP "$($m.Repo).zip"
            $tmp = Join-Path $env:TEMP "$($m.Repo)_unzip"
            if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
            Invoke-WebRequest -Uri "$repoUrl/archive/refs/heads/main.zip" -OutFile $zip
            Expand-Archive -Path $zip -DestinationPath $tmp -Force
            $inner = Get-ChildItem $tmp | Select-Object -First 1
            if (Test-Path $folder) { Remove-Item $folder -Recurse -Force }
            Move-Item $inner.FullName $folder
            Remove-Item $zip, $tmp -Recurse -Force -ErrorAction SilentlyContinue
            $ok = Test-Path (Join-Path $folder $m.Marker)
        }
    } catch { $ok = $false }
    if ($ok) { Write-Host "$($m.Name): downloaded" } else { $missing += $m.Name; Write-Warn "$($m.Name) could not be downloaded (the repository may be private)." }
}
if ($missing.Count -gt 0) {
    Write-Warn "Missing: $($missing -join ', '). Copy those folders next to this file (or use the portable zip) and run install.bat again."
}

# ------------------------------------------------------------------ 3. environment
Write-Step "Step 3/6: Private Python environment (.venv)"
if (Test-Path $VenvPython) {
    Write-Host ".venv already exists - it is reused."
} elseif ($DryRun) {
    Write-Host "[dry run] py -3.12 -m venv .venv"
} else {
    & py -3.12 -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) { Stop-Install "Could not create the Python environment (.venv)." }
}
if (-not $DryRun) { & $VenvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null }

# ------------------------------------------------------------------ 4. PyTorch
Write-Step "Step 4/6: PyTorch (large download - a few minutes)"
$cudaTag = $null
if (-not $ForceCpu) {
    try {
        $smi = & nvidia-smi 2>&1
        if ($LASTEXITCODE -eq 0) {
            $line = $smi | Select-String -Pattern "CUDA Version:\s*([\d.]+)"
            if ($line) {
                $ver = [version]$line.Matches[0].Groups[1].Value
                Write-Host "NVIDIA GPU found - CUDA $ver"
                if     ($ver -ge [version]"12.8") { $cudaTag = "cu128" }
                elseif ($ver -ge [version]"12.6") { $cudaTag = "cu126" }
                elseif ($ver -ge [version]"12.4") { $cudaTag = "cu124" }
                elseif ($ver -ge [version]"12.1") { $cudaTag = "cu121" }
                else                              { $cudaTag = "cu118" }
            } else { $cudaTag = "cu124" }
        }
    } catch { $cudaTag = $null }
}
try {
    if ($cudaTag) {
        Write-Host "Installing PyTorch for the GPU ($cudaTag) - about 2-3 GB ..."
        Invoke-Pip @("install", "torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/$cudaTag")
    } else {
        Write-Warn "No NVIDIA GPU (or -ForceCpu): installing the CPU build. Training and analysis will be much slower."
        Invoke-Pip @("install", "torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/cpu")
    }

    # ------------------------------------------------------------------ 5. libraries
    Write-Step "Step 5/6: ultralytics, opencv-python, pillow, pyyaml, matplotlib, numpy, albumentations"
    Invoke-Pip @("install", "ultralytics", "opencv-python", "pillow", "pyyaml", "matplotlib", "numpy", "albumentations", "--quiet")
} catch {
    Stop-Install "A package could not be installed: $($_.Exception.Message)`nCheck the internet connection and run install.bat again."
}

if (-not $DryRun) {
    $check = & $VenvPython -c "import torch, cv2, PIL, yaml, matplotlib, ultralytics; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" 2>&1
    Write-Host $check
    if ($LASTEXITCODE -ne 0) { Stop-Install "The libraries were installed but could not be imported:`n$check" }
    if ($cudaTag -and "$check" -notmatch "cuda True") {
        Write-Warn "An NVIDIA GPU was found but PyTorch cannot use it (cuda False). The programs still work on the CPU. Update the NVIDIA driver and run install.bat again."
    }
}

# ------------------------------------------------------------------ 6. shortcuts
Write-Step "Step 6/6: Shortcuts"
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
