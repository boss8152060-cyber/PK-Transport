"""What the modules share through PK Transport (no GUI): the model PKT Analyze starts with.

PKT Train writes its best weights; the user (or the Train page's "use in PKT Analyze" button) can hand one to PKT Analyze. It is kept in
pkt_settings.json ("shared"/"analyze_model") and given to PKT Analyze as the environment variable PKT_MODEL_PATH.
"""
import os


def analyze_environment(settings, base_env=None):
    """The environment PKT Analyze is started with: the base one + PKT_MODEL_PATH when a model was chosen and still exists."""
    env = dict(base_env if base_env is not None else os.environ)
    model = ((settings or {}).get("shared") or {}).get("analyze_model", "")
    if model and os.path.isfile(model):
        env["PKT_MODEL_PATH"] = model
    else:
        env.pop("PKT_MODEL_PATH", None)         # no stale value from the shell: PKT Analyze then uses its own default
    return env


def set_analyze_model(settings, path):
    """Remember the model for PKT Analyze in the settings dict (empty path = forget it); returns True when it was set."""
    shared = settings.setdefault("shared", {})
    if path and os.path.isfile(path):
        shared["analyze_model"] = os.path.normpath(path)
        return True
    shared.pop("analyze_model", None)
    return False


def get_analyze_model(settings):
    model = ((settings or {}).get("shared") or {}).get("analyze_model", "")
    return model if model and os.path.isfile(model) else ""
