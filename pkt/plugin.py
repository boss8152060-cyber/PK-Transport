"""PK Transport modules: the manifest every module repository carries and the loading of its plugin file.

A module (PKT Data, PKT Train, PKT Analyze ...) is a folder that has

    pkt_module.json   what it is: {"api": 1, "id": "data", "name": "PKT Data", "version": "1.4.0", "min_shell": "2.0.0",
                                   "plugin": "pkt_plugin.py", "requirements_file": "requirements.txt", "needs_torch": true,
                                   "user_files": [".pk_ui_config.json"]}
    pkt_plugin.py     how it appears in the window (the plugin API, version PLUGIN_API):

        API = 1
        def texts():                      -> {"th": {key: text}, "en": {key: text}}   extra texts for app.t()       (optional)
        def catalogs():                   -> [{"lang": "th", "exact": {}, "templates": {}, "fragments": False}]   translations of
                                              the module's own widgets (see pkt/ui/xlate.py)                       (optional)
        def summary(app, folder):         -> short text for the Home card ("12 runs · best mAP 0.81")              (optional)
        def recent(app, folder):          -> [{"mtime": float, "glyph": "◈", "title": "...", "meta": "..."}]        (optional)
        def create(parent, app, folder):  -> a ttk.Frame (the page); it may have on_show(), is_running(), stop_for_exit()

The top of pkt_plugin.py must stay light (no torch, no big imports): Home imports it just to read summary() / recent().
"""
import importlib.util
import json
import os
import sys

from pkt.updates import version_tuple

PLUGIN_API = 1
MANIFEST = "pkt_module.json"
INSTALLED_FILE = ".pkt_installed.json"          # written next to the module's files by the installer


class PluginError(Exception):
    pass


def read_manifest(folder):
    """The manifest dict of a module folder; PluginError when it is missing or not valid JSON."""
    path = os.path.join(folder, MANIFEST)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        raise PluginError(f"{MANIFEST} is missing in {folder}") from None
    except ValueError as exc:
        raise PluginError(f"{MANIFEST} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise PluginError(f"{MANIFEST} must hold an object")
    return data


def check_manifest(manifest, mid, shell_version):
    """'' when this shell can use the module, else the reason (shown to the user)."""
    if manifest.get("id") != mid:
        return f"this is module '{manifest.get('id')}', not '{mid}'"
    if int(manifest.get("api", 0) or 0) != PLUGIN_API:
        return f"it needs plugin API {manifest.get('api')}, this PK Transport has {PLUGIN_API}"
    need = manifest.get("min_shell") or ""
    if need and version_tuple(need) and version_tuple(shell_version) < version_tuple(need):
        return f"it needs PK Transport {need} or newer (this is {shell_version})"
    if not manifest.get("version"):
        return "the manifest has no version"
    return ""


def plugin_modname(mid):
    return f"pkt_plugin_{mid}"


def load_plugin(folder, mid, manifest=None):
    """Import the plugin file of the module in `folder` (its folder is put on sys.path so the module's own packages import)."""
    manifest = manifest or read_manifest(folder)
    path = os.path.join(folder, manifest.get("plugin") or "pkt_plugin.py")
    if not os.path.isfile(path):
        raise PluginError(f"plugin file not found: {path}")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    name = plugin_modname(mid)
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException as exc:
        sys.modules.pop(name, None)
        raise PluginError(f"{type(exc).__name__}: {exc}") from exc
    if int(getattr(module, "API", 0) or 0) != PLUGIN_API:
        sys.modules.pop(name, None)
        raise PluginError(f"the plugin speaks API {getattr(module, 'API', None)}, this PK Transport speaks {PLUGIN_API}")
    return module


def purge(folder, mid):
    """Forget everything that was imported from the module folder (so a new version can be loaded in the same run).
    Only safe for a module whose page was never created; otherwise the program has to be restarted."""
    prefix = os.path.normcase(os.path.abspath(folder)) + os.sep
    for name, mod in list(sys.modules.items()):
        path = getattr(mod, "__file__", None) or ""
        if name == plugin_modname(mid) or (path and os.path.normcase(os.path.abspath(path)).startswith(prefix)):
            sys.modules.pop(name, None)
    sys.path[:] = [p for p in sys.path if os.path.normcase(os.path.abspath(p)) != prefix[:-1] and not os.path.normcase(os.path.abspath(p)).startswith(prefix)]


def read_installed(folder):
    """{'version', 'tag', 'source', 'installed'} written by the installer, or {} (a linked development folder has none)."""
    try:
        with open(os.path.join(folder, INSTALLED_FILE), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
