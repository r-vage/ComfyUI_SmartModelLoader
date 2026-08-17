# Copy-only migration from Eclipse and older loader locations.

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from .config_store import CONFIG_PATH, ensure_config_exists, update_config_values
from .json_store import JsonStoreError, read_json_object, write_json_object
from .logger import log

_LOG_PREFIX = "Migration"
_MIGRATION_MARKER = ".eclipse_loader_data_migrated"
_MIGRATION_MARKER_VERSION = 2
_CONFIG_KEYS = (
    "civitai_api_key",
    "hf_token",
    "allow_legacy_model_formats",
    "retry_download_attempts",
    "log_level",
    "use_sliders",
)
_ECLIPSE_CONFIG_KEYS = frozenset(_CONFIG_KEYS)
_DEFAULT_CONFIG_VALUES = {
    "civitai_api_key": "",
    "hf_token": "",
    "allow_legacy_model_formats": False,
    "retry_download_attempts": 2,
    "log_level": "warning",
    "use_sliders": True,
}


def _copy_file_if_missing(source: Path, destination: Path) -> bool:
    if not source.is_file() or source.is_symlink() or destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.migration-{os.getpid()}")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
        return True
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _copy_templates(source: Path, destination: Path) -> int:
    if not source.is_dir() or source.is_symlink():
        return 0
    copied = 0
    destination.mkdir(parents=True, exist_ok=True)
    for source_file in source.glob("*.json"):
        if _copy_file_if_missing(source_file, destination / source_file.name):
            copied += 1
    return copied


def _extract_bundled_templates(root: Path) -> int:
    source = root / ".defaults" / "templates"
    destination = root / "templates"
    if not source.is_dir() or source.is_symlink():
        return 0
    copied = 0
    for source_file in source.glob("*.json.example"):
        target_name = source_file.name.removesuffix(".example")
        if _copy_file_if_missing(source_file, destination / target_name):
            copied += 1
    return copied


def _migrate_config(source: Path) -> tuple[list[str], list[str]]:
    if not source.is_file() or source.is_symlink():
        return [], []
    try:
        legacy = read_json_object(source)
        current = read_json_object(CONFIG_PATH)
    except (JsonStoreError, OSError):
        return [], []
    examined = sorted(_ECLIPSE_CONFIG_KEYS)
    updates: dict[str, Any] = {}
    for key in _CONFIG_KEYS:
        value = legacy.get(key)
        current_value = current.get(key, _DEFAULT_CONFIG_VALUES[key])
        if value in (None, "") or current_value != _DEFAULT_CONFIG_VALUES[key]:
            continue
        if key == "allow_legacy_model_formats" and value is not True:
            continue
        updates[key] = value
    if updates and update_config_values(updates):
        return sorted(updates), examined
    return [], examined


def _read_marker_keys(marker: Path) -> set[str]:
    if not marker.is_file() or marker.is_symlink():
        return set()
    try:
        data = read_json_object(marker)
    except (JsonStoreError, OSError):
        return set()
    keys = data.get("examined_eclipse_config_keys")
    if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
        return set()
    return set(keys)


def _marker_is_current(marker: Path, examined: set[str]) -> bool:
    if not marker.is_file() or marker.is_symlink():
        return False
    try:
        data = read_json_object(marker)
    except (JsonStoreError, OSError):
        return False
    version = data.get("version")
    return (
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= _MIGRATION_MARKER_VERSION
        and data.get("completed") is True
        and _ECLIPSE_CONFIG_KEYS <= examined
    )


def run_migrations(repo_root: str | os.PathLike[str] | None = None) -> None:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent.parent
    ensure_config_exists()
    marker = root / _MIGRATION_MARKER
    examined_keys = _read_marker_keys(marker)
    if _marker_is_current(marker, examined_keys):
        _extract_bundled_templates(root)
        return
    custom_nodes = root.parent
    eclipse_candidates = (
        custom_nodes / "comfyui_eclipse",
        custom_nodes / "ComfyUI_Eclipse",
    )
    eclipse_root = next((path for path in eclipse_candidates if path.is_dir()), None)
    copied_templates = 0
    migrated_keys: list[str] = []
    queue_copied = False
    if eclipse_root is not None:
        copied_templates += _copy_templates(eclipse_root / "templates", root / "templates")
        migrated_keys, newly_examined = _migrate_config(eclipse_root / "config.json")
        examined_keys.update(newly_examined)
        queue_copied = _copy_file_if_missing(
            eclipse_root / "download_manager" / "queue.json",
            root / "download_manager" / "queue.json",
        )
    comfyui_root = custom_nodes.parent
    copied_templates += _copy_templates(
        comfyui_root / "models" / "smart_loader_templates",
        root / "templates",
    )
    # User templates win on the first migration; bundled presets only fill names
    # that were not present in either supported legacy location.
    copied_templates += _extract_bundled_templates(root)
    write_json_object(
        marker,
        {
            "version": _MIGRATION_MARKER_VERSION,
            "completed": True,
            "examined_eclipse_config_keys": sorted(examined_keys),
        },
        private=True,
    )
    if copied_templates or migrated_keys or queue_copied:
        log.msg(
            _LOG_PREFIX,
            f"Copied {copied_templates} template(s), {len(migrated_keys)} config value(s), "
            f"and {'one queue snapshot' if queue_copied else 'no queue snapshot'}",
        )
