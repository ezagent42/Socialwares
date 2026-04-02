"""Load the App object from socialware.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from socialwares.app import App


def load_app(path: str | Path = "socialware.py") -> App:
    """Dynamically load socialware.py and return the app object defined within it.

    Convention: socialware.py must contain an App instance named 'app'.
    Note: temporarily changes the working directory to the directory containing
    socialware.py so that file= relative paths resolve correctly.
    """
    import os

    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Cannot find {path}")

    # Change to the directory containing socialware.py (file= relative paths depend on this)
    old_cwd = os.getcwd()
    os.chdir(path.parent)

    spec = importlib.util.spec_from_file_location("socialware", str(path))
    if spec is None or spec.loader is None:
        os.chdir(old_cwd)
        raise ImportError(f"Cannot load {path}")

    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(old_cwd)

    if not hasattr(mod, "app"):
        raise ValueError(f"'app' object not found in {path}")

    app = mod.app
    if not isinstance(app, App):
        raise TypeError(f"'app' in {path} is not an App instance (type: {type(app).__name__})")

    return app
