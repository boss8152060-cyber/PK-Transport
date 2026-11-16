"""The Python libraries a module needs (no GUI): PyTorch (CUDA build when there is an NVIDIA GPU, else CPU) and the module's requirements.

The libraries go into the Python that runs PK Transport (the private .venv made by install.bat). `runner` runs a command and gives
back (exit code, output lines) so tests need no network."""
import os
import re
import subprocess
import sys
import tempfile

CUDA_TAGS = (("12.8", "cu128"), ("12.6", "cu126"), ("12.4", "cu124"), ("12.1", "cu121"))
TORCH_INDEX = "https://download.pytorch.org/whl/{tag}"


def cuda_tag_from_smi(text):
    """'cu124' etc. from the output of nvidia-smi (its 'CUDA Version: 12.5' line), 'cu124' when the version cannot be read, None without a GPU."""
    if not text or "NVIDIA" not in text.upper():
        return None
    m = re.search(r"CUDA Version:\s*(\d+)\.(\d+)", text)
    if not m:
        return "cu124"
    have = (int(m.group(1)), int(m.group(2)))
    for ver, tag in CUDA_TAGS:
        major, minor = (int(x) for x in ver.split("."))
        if have >= (major, minor):
            return tag
    return "cu118"


def quiet(log):
    """A log function that drops the pip lines nobody needs to read ('Requirement already satisfied ...', '[notice] ...')."""
    def filtered(line):
        if not (line.startswith("Requirement already satisfied") or line.startswith("[notice]")):
            log(line)
    return filtered


def default_runner(cmd, log=None, timeout=None):
    """Run `cmd`, send every output line to `log` as it comes, return (exit code, all lines)."""
    lines = []
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        return 127, [str(exc)]
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            lines.append(line)
            if log:
                log(line)
    proc.wait()
    return proc.returncode, lines


def detect_cuda_tag(runner=default_runner):
    code, lines = runner(["nvidia-smi"])
    return cuda_tag_from_smi("\n".join(lines)) if code == 0 else None


def torch_status(python=sys.executable, runner=default_runner):
    """{'version', 'cuda'} of the PyTorch in `python`, or None when it is not installed."""
    code, lines = runner([python, "-c", "import torch; print(torch.__version__); print(torch.cuda.is_available())"])
    if code != 0 or len(lines) < 2:
        return None
    return {"version": lines[-2], "cuda": lines[-1].strip() == "True"}


def ensure_torch(python=sys.executable, log=print, force_cpu=False, runner=default_runner):
    """Install PyTorch if it is missing (or CPU-only on a PC with an NVIDIA GPU). Returns the torch_status afterwards."""
    force_cpu = force_cpu or os.environ.get("PKT_FORCE_CPU") == "1"        # (install.bat -ForceCpu)
    tag = None if force_cpu else detect_cuda_tag(runner)
    status = torch_status(python, runner)
    if status and (status["cuda"] or not tag):
        log(f"PyTorch {status['version']} is installed ({'GPU' if status['cuda'] else 'CPU'})")
        return status
    if tag:
        log(f"Installing PyTorch for the GPU ({tag}) - about 2-3 GB, this takes a few minutes ...")
        cmd = [python, "-m", "pip", "install", "--upgrade", "torch", "torchvision", "--index-url", TORCH_INDEX.format(tag=tag)]
    else:
        log("No NVIDIA GPU found: installing the CPU build of PyTorch (training and analysis will be slower) ...")
        cmd = [python, "-m", "pip", "install", "torch", "torchvision", "--index-url", TORCH_INDEX.format(tag="cpu")]
    code, _lines = runner(cmd, quiet(log)) if runner is default_runner else runner(cmd)
    if code != 0:
        raise RuntimeError("PyTorch could not be installed (see the log)")
    return torch_status(python, runner)


def install_requirements(python, requirements, log=print, runner=default_runner):
    """pip install the given requirement lines (a list of 'name' / 'name>=1.0')."""
    reqs = [r.strip() for r in requirements if r and r.strip() and not r.strip().startswith("#")]
    if not reqs:
        return
    log("Installing libraries: " + ", ".join(reqs))
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(reqs) + "\n")
        path = f.name
    try:
        cmd = [python, "-m", "pip", "install", "-r", path]
        code, _lines = runner(cmd, quiet(log)) if runner is default_runner else runner(cmd)
    finally:
        os.remove(path)
    if code != 0:
        raise RuntimeError("the libraries could not be installed (see the log)")


def module_requirements(manifest, folder):
    """The requirement lines of a module: its 'requirements' list plus the lines of its 'requirements_file'."""
    reqs = list(manifest.get("requirements") or [])
    rf = manifest.get("requirements_file")
    if rf and os.path.isfile(os.path.join(folder, rf)):
        with open(os.path.join(folder, rf), encoding="utf-8") as f:
            reqs += [line.strip() for line in f if line.strip() and not line.strip().startswith(("#", "-"))]
    seen, out = set(), []
    for r in reqs:
        key = re.split(r"[<>=!~ ;\[]", r, 1)[0].lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def prepare_module(manifest, folder, log=print, python=sys.executable, runner=default_runner, force_cpu=False):
    """Everything a module needs before it can run: PyTorch (when 'needs_torch') and its requirements."""
    if manifest.get("needs_torch"):
        ensure_torch(python, log, force_cpu=force_cpu, runner=runner)
    install_requirements(python, module_requirements(manifest, folder), log, runner)
