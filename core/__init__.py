from .common import RESOLUTION_MAP, RESOLUTION_PRESETS, SLIDER_DISPLAY
from .keys import CATEGORY

__all__ = [
    "CATEGORY",
    "RESOLUTION_MAP",
    "RESOLUTION_PRESETS",
    "SLIDER_DISPLAY",
    "__version__",
    "version",
]


def _read_pyproject_version() -> str:
    try:
        import re
        from pathlib import Path

        for parent in Path(__file__).resolve().parents:
            toml_file = parent / "pyproject.toml"
            if not toml_file.exists():
                continue
            match = re.search(
                r"\bversion\s*=\s*['\"]([^'\"]+)['\"]",
                toml_file.read_text(encoding="utf-8"),
            )
            if match:
                return match.group(1)
    except (OSError, ValueError):
        pass
    return "1.0.0"


__version__ = _read_pyproject_version()
version = __version__
