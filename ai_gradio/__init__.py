from importlib.metadata import version

try:
    __version__ = version("ai-gradio")
except Exception:
    __version__ = "unknown"

from .providers import registry

__all__ = ["registry"]
