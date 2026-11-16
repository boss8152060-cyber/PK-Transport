"""The module manager (no GUI): which versions of a module exist on GitHub, install / switch / update / uninstall it.

A module is a repository (PKT-Data, PKT-Train, PKT-Analyze) whose releases are git tags. The registry (modules.json) says where
each module lives and how its tags are written:  {"id": "data", "name": "PKT Data", "repo": "owner/PKT-Data", "tag_regex": "^v(\\d+\\.\\d+\\.\\d+)$"}.
Installing downloads the zip of a tag from GitHub (no git needed), checks the manifest (pkt_module.json) and swaps the folder
modules/<id> in one step; the old version is kept until the new one is in place. Everything the user made lives outside the module
folder (user_data/, pkt_settings.json), plus the few files a module lists as "user_files", which are carried over.

Command line (also what install.bat uses):
    python -m pkt.modman list                       installed modules and the newest version of each
    python -m pkt.modman install data train@0.2.1   install (optionally a given version)
    python -m pkt.modman update [data ...]          update what is installed (all when none is named)
    python -m pkt.modman uninstall analyze
    python -m pkt.modman prepare                    install the libraries of the modules that are already in modules/ (a portable zip with modules)
"""
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import zipfile

from pkt import __version__ as SHELL_VERSION
from pkt import plugin
from pkt.updates import version_tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_BASE = "https://api.github.com"
ZIP_URL = "https://github.com/{repo}/archive/refs/tags/{tag}.zip"
TAG_CACHE_SECONDS = 3600


class ModManError(Exception):
    pass


# ====================================================================== registry and places
def load_registry(path=None):
    path = path or os.path.join(ROOT, "modules.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["modules"]
    except (OSError, ValueError, KeyError) as exc:
        raise ModManError(f"cannot read the module registry {path}: {exc}") from None


def modules_dir(root=ROOT):
    return os.path.join(root, "modules")


LEGACY_FOLDERS = ("PKT-Data", "PKT-Train", "PKT-Analyze")      # the module folders of PK Transport 1.x, when they sat inside the app folder


def legacy_folders(root=ROOT):
    """The folders of PK Transport 1.x that are still next to the app (the modules are in modules/ now; these are no longer used)."""
    return [name for name in LEGACY_FOLDERS if os.path.isdir(os.path.join(root, name))]


def user_data_dir(root=ROOT, *parts):
    """Where the modules keep what the user makes (trained runs ...); never touched by install / uninstall / update."""
    path = os.path.join(root, "user_data", *parts)
    os.makedirs(path, exist_ok=True)
    return path


def module_folder(root, mod_def, settings=None):
    """(folder, linked). A folder the user pointed this module to (a development checkout) wins over modules/<id>."""
    user = ((settings or {}).get("modules") or {}).get(mod_def["id"]) or {}
    path = (user.get("path") or "").strip()
    if path:
        return (path if os.path.isabs(path) else os.path.normpath(os.path.join(root, path))), True
    return os.path.join(modules_dir(root), mod_def["id"]), False


def installed_state(root, mod_def, settings=None, shell_version=SHELL_VERSION):
    """{'id', 'name', 'folder', 'linked', 'installed', 'version', 'tag', 'manifest', 'problem'}.
    installed = the folder has a manifest; problem = why this shell cannot use it ('' when fine)."""
    folder, linked = module_folder(root, mod_def, settings)
    out = {"id": mod_def["id"], "name": mod_def.get("name", mod_def["id"]), "folder": folder, "linked": linked, "installed": False,
           "version": "", "tag": "", "manifest": {}, "problem": ""}
    if not os.path.isdir(folder):
        return out
    try:
        manifest = plugin.read_manifest(folder)
    except plugin.PluginError as exc:
        out["problem"] = str(exc) if linked or os.path.isfile(os.path.join(folder, plugin.MANIFEST)) else ""
        out["installed"] = linked                               # a linked folder that is not a module is reported, an empty modules/<id> is "not installed"
        return out
    info = plugin.read_installed(folder)
    out.update(installed=True, manifest=manifest, version=info.get("version") or manifest.get("version", ""), tag=info.get("tag", ""))
    out["problem"] = plugin.check_manifest(manifest, mod_def["id"], shell_version)
    return out


# ====================================================================== versions on GitHub
def _http_get(url, timeout=20, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "PK-Transport", "Accept": "application/vnd.github+json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except OSError as exc:
        raise ModManError(f"cannot reach GitHub ({exc})") from None


def parse_tags(names, tag_regex, min_version=""):
    """[{'tag', 'version', 'tuple'}] for the tag names that match the module's pattern (and are not older than `min_version`:
    the first release that is a PK Transport module), newest first."""
    rx = re.compile(tag_regex)
    floor = version_tuple(min_version)
    out = []
    for name in names:
        m = rx.match(name)
        if m and version_tuple(m.group(1)) and version_tuple(m.group(1)) >= floor:
            out.append({"tag": name, "version": m.group(1), "tuple": version_tuple(m.group(1))})
    out.sort(key=lambda t: t["tuple"], reverse=True)
    return out


def list_tags(mod_def, api_base=API_BASE, timeout=20, cache_dir=None, ttl=TAG_CACHE_SECONDS):
    """The released versions of a module (its git tags), newest first. Cached on disk for an hour (GitHub allows 60 anonymous calls per hour)."""
    cache = os.path.join(cache_dir, f"tags_{mod_def['id']}.json") if cache_dir else None
    if cache and os.path.isfile(cache) and time.time() - os.path.getmtime(cache) < ttl:
        try:
            with open(cache, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("repo") == mod_def["repo"]:
                return parse_tags(data["names"], mod_def["tag_regex"], mod_def.get("min_version", ""))
        except (OSError, ValueError, KeyError):
            pass
    names, page = [], 1
    while page <= 10:
        raw = _http_get(f"{api_base}/repos/{mod_def['repo']}/tags?per_page=100&page={page}", timeout)
        try:
            batch = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise ModManError("GitHub answered something that is not a tag list") from None
        if not isinstance(batch, list):
            raise ModManError(str(batch.get("message", "GitHub refused the request")) if isinstance(batch, dict) else "unexpected GitHub answer")
        names += [t.get("name", "") for t in batch if isinstance(t, dict)]
        if len(batch) < 100:
            break
        page += 1
    if cache:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache, "w", encoding="utf-8") as f:
                json.dump({"repo": mod_def["repo"], "names": names}, f)
        except OSError:
            pass
    return parse_tags(names, mod_def["tag_regex"], mod_def.get("min_version", ""))


def update_state(state, tags):
    """'' (not installed / no information) | 'uptodate' | 'update' (a newer version exists) for an installed module."""
    if not state["installed"] or state["linked"] or not tags or not version_tuple(state["version"]):
        return ""
    return "update" if tags[0]["tuple"] > version_tuple(state["version"]) else "uptodate"


# ====================================================================== install / uninstall
def _extract_zip(data, target):
    """Extract a GitHub zip (one top folder) into `target`; returns nothing. Paths that leave the folder are refused."""
    base = os.path.abspath(target)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        if not names:
            raise ModManError("the downloaded zip is empty")
        top = names[0].split("/")[0]
        for name in names:
            parts = [p for p in name.split("/")[1:] if p]
            if name.split("/")[0] != top or not parts or ".." in parts:
                continue
            dest = os.path.abspath(os.path.join(base, *parts))
            if os.path.commonpath([dest, base]) != base:
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(name) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)


def install(root, mod_def, tag, log=print, zip_url=ZIP_URL, shell_version=SHELL_VERSION, timeout=180, settings=None):
    """Install (or replace by) the version `tag` of a module. Returns the manifest. The old version stays until the new one is complete."""
    mid = mod_def["id"]
    mods = modules_dir(root)
    os.makedirs(mods, exist_ok=True)
    url = zip_url.format(repo=mod_def["repo"], tag=tag)
    log(f"Downloading {mod_def.get('name', mid)} {tag} ...")
    data = _http_get(url, timeout, headers={"Accept": "application/zip"})
    tmp = os.path.join(mods, f".new_{mid}")
    old = os.path.join(mods, f".old_{mid}")
    for leftover in (tmp, old):
        shutil.rmtree(leftover, ignore_errors=True)
    os.makedirs(tmp)
    try:
        try:
            _extract_zip(data, tmp)
        except zipfile.BadZipFile:
            raise ModManError("the downloaded file is not a zip") from None
        try:
            manifest = plugin.read_manifest(tmp)
        except plugin.PluginError as exc:
            raise ModManError(f"this version is not a PK Transport module: {exc}") from None
        problem = plugin.check_manifest(manifest, mid, shell_version)
        if problem:
            raise ModManError(f"{tag} cannot be installed: {problem}")
        target = os.path.join(mods, mid)
        if os.path.isdir(target):
            for rel in manifest.get("user_files") or []:                  # the few files the module itself writes into its folder
                src = os.path.join(target, rel)
                if os.path.isfile(src) and not os.path.isfile(os.path.join(tmp, rel)):
                    os.makedirs(os.path.dirname(os.path.join(tmp, rel)) or tmp, exist_ok=True)
                    shutil.copy2(src, os.path.join(tmp, rel))
        with open(os.path.join(tmp, plugin.INSTALLED_FILE), "w", encoding="utf-8") as f:
            json.dump({"version": manifest["version"], "tag": tag, "source": "zip", "installed": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
        if os.path.isdir(target):
            try:
                os.replace(target, old)                                    # fails while a file of it is open (a running module)
            except OSError as exc:
                raise ModManError(f"the current {mod_def.get('name', mid)} is in use ({exc}); close PK Transport and try again") from None
        try:
            os.replace(tmp, target)
        except OSError as exc:
            if os.path.isdir(old):
                os.replace(old, target)                                    # put the old version back
            raise ModManError(f"cannot put the new version in place: {exc}") from None
        shutil.rmtree(old, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log(f"{mod_def.get('name', mid)} {manifest['version']} installed")
    return manifest


def uninstall(root, mod_def, log=print):
    """Remove modules/<id>. A linked development folder is never deleted. What the user made (user_data/) stays."""
    folder = os.path.join(modules_dir(root), mod_def["id"])
    if not os.path.isdir(folder):
        raise ModManError(f"{mod_def.get('name', mod_def['id'])} is not installed")
    try:
        shutil.rmtree(folder)
    except OSError as exc:
        raise ModManError(f"cannot remove {folder} ({exc}); close PK Transport and try again") from None
    log(f"{mod_def.get('name', mod_def['id'])} removed")


# ====================================================================== command line
def _by_id(registry, mid):
    for mod_def in registry:
        if mod_def["id"] == mid:
            return mod_def
    raise ModManError(f"unknown module '{mid}' (known: {', '.join(d['id'] for d in registry)})")


def main(argv=None, root=ROOT, registry=None, out=print):
    argv = list(sys.argv[1:] if argv is None else argv)
    registry = registry if registry is not None else load_registry()
    cache = user_data_dir(root, "cache")
    if not argv or argv[0] not in ("list", "install", "update", "uninstall", "prepare"):
        out(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "list":
            for mod_def in registry:
                st = installed_state(root, mod_def)
                try:
                    tags = list_tags(mod_def, cache_dir=cache)
                    newest = tags[0]["version"] if tags else "-"
                except ModManError as exc:
                    newest = f"? ({exc})"
                out(f"{mod_def['id']:8} {'installed ' + st['version'] if st['installed'] else 'not installed':24} newest {newest}")
            return 0
        if cmd == "install":
            if not args:
                raise ModManError("name the modules to install, e.g. data train analyze (or data@1.3.8)")
            for item in args:
                mid, _, ver = item.partition("@")
                mod_def = _by_id(registry, mid)
                tags = list_tags(mod_def, cache_dir=cache)
                pick = next((t for t in tags if t["version"] == ver), None) if ver else (tags[0] if tags else None)
                if pick is None:
                    raise ModManError(f"no such version of {mid}: {ver or '(none released)'}")
                install(root, mod_def, pick["tag"], log=out)
                from pkt import envsetup
                envsetup.prepare_module(plugin.read_manifest(module_folder(root, mod_def)[0]), module_folder(root, mod_def)[0], log=out)
            return 0
        if cmd == "update":
            ids = args or [d["id"] for d in registry if installed_state(root, d)["installed"]]
            for mid in ids:
                mod_def = _by_id(registry, mid)
                st = installed_state(root, mod_def)
                tags = list_tags(mod_def, cache_dir=cache)
                if update_state(st, tags) == "update":
                    install(root, mod_def, tags[0]["tag"], log=out)
                    from pkt import envsetup
                    envsetup.prepare_module(plugin.read_manifest(st["folder"]), st["folder"], log=out)
                else:
                    out(f"{mid}: up to date")
            return 0
        if cmd == "uninstall":
            for mid in args:
                uninstall(root, _by_id(registry, mid), log=out)
            return 0
        if cmd == "prepare":
            from pkt import envsetup
            for mod_def in registry:
                st = installed_state(root, mod_def)
                if st["installed"] and not st["problem"] and (not args or mod_def["id"] in args):
                    out(f"{mod_def['name']} {st['version']}: libraries ...")
                    envsetup.prepare_module(st["manifest"], st["folder"], log=out)
            return 0
    except ModManError as exc:
        out(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
