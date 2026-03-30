"""加载 socialware.py 中的 App 对象。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from socialwares.app import App


def load_app(path: str | Path = "socialware.py") -> App:
    """动态加载 socialware.py，返回其中的 app 对象。

    约定：socialware.py 中必须有一个名为 app 的 App 实例。
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"找不到 {path}")

    spec = importlib.util.spec_from_file_location("socialware", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "app"):
        raise ValueError(f"{path} 中未找到 'app' 对象")

    app = mod.app
    if not isinstance(app, App):
        raise TypeError(f"{path} 中的 'app' 不是 App 实例（类型: {type(app).__name__}）")

    return app
