"""Desktop shortcut of PK Transport (Windows .lnk through PowerShell / WScript.Shell). Only when the user presses the button."""
import os
import shutil
import subprocess
import sys


def launcher_target(app_root):
    """(program, arguments) a shortcut runs: pyw (no console window) with the Python 3.12 selector when it works, else this Python."""
    main = os.path.join(app_root, "main.py")
    venv_w = os.path.join(app_root, ".venv", "Scripts", "pythonw.exe")
    if os.name == "nt" and os.path.isfile(venv_w):
        return venv_w, f'"{main}"'                  # the private environment made by install.bat
    if os.name == "nt":
        pyw = shutil.which("pyw")
        if pyw:
            try:
                ok = subprocess.run(["py", "-3.12", "-V"], capture_output=True, timeout=8).returncode == 0
            except (OSError, subprocess.SubprocessError):
                ok = False
            return pyw, (f'-3.12 "{main}"' if ok else f'"{main}"')
    exe = sys.executable
    if os.name == "nt" and exe.lower().endswith("python.exe"):
        w = exe[:-len("python.exe")] + "pythonw.exe"
        exe = w if os.path.isfile(w) else exe
    return exe, f'"{main}"'


def create_shortcut(app_root, folder=None, name="PK Transport"):
    """Create `<folder>/<name>.lnk` (folder = the Desktop by default). Returns (ok, path or error text)."""
    if os.name != "nt":
        return False, "shortcuts are only made on Windows"
    program, args = launcher_target(app_root)
    ps = ("$ws = New-Object -ComObject WScript.Shell; "
          "$dir = $env:PKT_SHORTCUT_DIR; if (-not $dir) { $dir = [Environment]::GetFolderPath('Desktop') }; "
          "$lnk = Join-Path $dir ($env:PKT_SHORTCUT_NAME + '.lnk'); "
          "$s = $ws.CreateShortcut($lnk); $s.TargetPath = $env:PKT_SHORTCUT_PROGRAM; $s.Arguments = $env:PKT_SHORTCUT_ARGS; "
          "$s.WorkingDirectory = $env:PKT_SHORTCUT_WORKDIR; $s.Description = 'PK Transport'; "
          "if ($env:PKT_SHORTCUT_ICON -and (Test-Path $env:PKT_SHORTCUT_ICON)) { $s.IconLocation = $env:PKT_SHORTCUT_ICON }; $s.Save(); Write-Output $lnk")
    env = dict(os.environ, PKT_SHORTCUT_DIR=folder or "", PKT_SHORTCUT_NAME=name, PKT_SHORTCUT_PROGRAM=program,
               PKT_SHORTCUT_ARGS=args, PKT_SHORTCUT_WORKDIR=app_root, PKT_SHORTCUT_ICON=os.path.join(app_root, "assets", "icon.ico"))
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    path = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if r.returncode != 0 or not path or not os.path.isfile(path):
        return False, (r.stderr.strip() or "the shortcut was not created")[-300:]
    return True, path
