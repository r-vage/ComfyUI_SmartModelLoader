# Smart Model Loader server endpoints extracted from Eclipse.
#
# Loader templates, verified CivitAI acquisition, integrity, file lists, and settings.

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

# Prevent shadowing of ComfyUI's top-level utils package by comfy/utils.py when nodes.py has been imported first.
if "utils" not in sys.modules:
    try:
        import utils  # type: ignore  # noqa: F401
    except ImportError:
        pass

import folder_paths  # type: ignore
import requests  # type: ignore
from aiohttp import web  # type: ignore
from server import PromptServer  # type: ignore

from .civitai_client import (
    CivitaiSelectionError,
    DownloadCancelled,
    DownloadDestinationBusy,
    cancel_active_download,
    download_file,
    parse_air,
    release_download_id,
    reserve_download_id,
    resolve_file_for_download,
)
from .common import get_config_value, update_config_values
from .config_store import DEFAULT_CHIP_COLOR, normalize_chip_color
from .logger import log
from .model_integrity import (
    integrity_key,
    read_expected,
    write_expected,
)
from .model_integrity import (
    verify as verify_hash,
)
from .model_loader.endpoints import (
    delete_template_transaction,
    global_mutation_denial,
    prepare_download_destination,
    promote_verified_replacement,
    read_json_object_request,
    require_json_boolean,
    resolve_role_target,
)
from .model_loader.progress import ConsolePhaseProgress
from .model_loader.validation import (
    GGUF_EXTENSIONS,
    LEGACY_MODEL_EXTENSIONS,
    SAFE_TENSOR_EXTENSIONS,
    LoaderValidationError,
    resolve_model_file,
)

_MODEL_IO_SEMAPHORE = asyncio.Semaphore(2)

# Detect ComfyUI native dynamic VRAM:
# 0.18.x: ModelPatcher gained 'model_mmap_residency'
# 0.23.0+: ModelPatcherDynamic subclass (is_dynamic() returns True) replaces that attribute
try:
    import comfy.model_patcher as _mp  # type: ignore

    _HAS_NATIVE_DYNAMIC_VRAM = hasattr(
        _mp, "ModelPatcherDynamic",
    ) or hasattr(  # 0.23.0+
        _mp.ModelPatcher, "model_mmap_residency",
    )  # 0.18.x
except Exception:  # noqa: BLE001 - optional ComfyUI compatibility probe
    _HAS_NATIVE_DYNAMIC_VRAM = False


def is_safe_filename(filename: str) -> bool:
    # Validate filename to prevent path traversal attacks.
    # Returns True if filename is safe (no path separators or traversal).
    if not filename:
        log.warning("Security", "Blocked empty filename")
        return False
    # Block path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        log.warning(
            "Security", f"Blocked path traversal attempt in filename: {filename}",
        )
        return False
    # Block null bytes
    if "\x00" in filename:
        log.warning("Security", f"Blocked null byte in filename: {filename!r}")
        return False
    return True


# Map template file-bearing fields → folder_paths keys to try (in order).
_TEMPLATE_FILE_FIELD_FOLDERS: dict[str, list[str]] = {
    "ckpt_name": ["checkpoints"],
    "unet_name": ["diffusion_models"],
    "nunchaku_name": ["diffusion_models"],
    "qwen_name": ["diffusion_models"],
    "zimage_name": ["diffusion_models"],
    "gguf_name": ["diffusion_models_gguf", "diffusion_models"],
    "clip_name1": ["clip", "text_encoders"],
    "clip_name2": ["clip", "text_encoders"],
    "clip_name3": ["clip", "text_encoders"],
    "clip_name4": ["clip", "text_encoders"],
    "vae_name": ["vae"],
    "audio_vae_name": ["vae"],
    **{f"lora_name_{i}": ["loras"] for i in range(1, 11)},
}


def _overlay_expected_hashes_from_disk(config: dict[str, Any]) -> dict[str, Any]:
    # Snapshot each selected file's trusted <file>.eclipse.json into the template's
    # expected_hashes map (keyed by folder role + relative path). The on-disk
    # .eclipse.json is authoritative
    # for present files; manually-entered/pending entries already in expected_hashes are
    # preserved (never wiped) so shipped templates can still locate absent files.
    raw = config.get("expected_hashes", "{}")
    expected: dict[str, Any] = {}
    if isinstance(raw, dict):
        expected = dict(raw)
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                expected = parsed
        except Exception:  # noqa: BLE001 - malformed legacy metadata is ignored
            expected = {}

    for field, folder_keys in _TEMPLATE_FILE_FIELD_FOLDERS.items():
        value = config.get(field)
        if not value or value in ("None", ""):
            continue
        resolved_file = None
        for folder_key in folder_keys:
            if folder_key not in folder_paths.folder_names_and_paths:
                continue
            try:
                reference_type = "model_gguf" if folder_key == "diffusion_models_gguf" else "model"
                if field.startswith("clip_name"):
                    reference_type = "clip"
                elif field.startswith("lora_name"):
                    reference_type = "lora"
                elif field in {"vae_name", "audio_vae_name"}:
                    reference_type = "vae"
                resolved_file = resolve_model_file(
                    folder_key,
                    str(value),
                    reference_type=reference_type,
                )
                break
            except LoaderValidationError:
                continue

        if not resolved_file:
            continue

        disk_expected = read_expected(resolved_file.path)
        if not disk_expected:
            continue

        key = integrity_key(resolved_file.role, resolved_file.relative_path)
        prev = expected.get(key)
        merged = dict(prev) if isinstance(prev, dict) else {}
        merged.update(disk_expected)  # .eclipse.json is authoritative for present files
        expected[key] = merged

    config["expected_hashes"] = json.dumps(expected)
    return config


class LoaderEndpoints:
    # Eclipse template and configuration server endpoints.

    def __init__(self):
        self.extension_root = os.path.dirname(os.path.dirname(__file__))
        self.loader_dir = os.path.join(self.extension_root, "templates")

        self._register_endpoints()

    def _register_endpoints(self):
        # Register all template-related endpoints.

        # ==================== LOADER TEMPLATES ====================

        @PromptServer.instance.routes.get("/smart-model-loader/templates/{filename}")
        async def serve_loader_template(request):
            # Serve a loader template file.
            filename = request.match_info.get("filename", "")

            # Security: validate filename BEFORE path operations
            if not is_safe_filename(filename):
                return web.Response(status=400, text="Invalid filename")
            if not filename.endswith(".json"):
                return web.Response(status=400, text="Invalid file type")

            template_dir = self.loader_dir
            template_path = os.path.join(template_dir, filename)

            # Security: double-check path stays within template directory
            if not os.path.abspath(template_path).startswith(
                os.path.abspath(template_dir),
            ):
                return web.Response(status=403, text="Access denied")

            if os.path.exists(template_path) and os.path.isfile(template_path):
                # Read, normalize paths (cross-platform), and serve as JSON
                try:
                    from .loader_templates import load_template

                    config = await asyncio.to_thread(
                        load_template, Path(filename).stem,
                    )
                    if not config:
                        return web.Response(status=500, text="Template is malformed")
                    return web.json_response(config)
                except Exception as error:  # noqa: BLE001 - endpoint boundary sanitizes failures
                    log.error("Smart Loader", f"Template read failed: {type(error).__name__}")
                    return web.Response(status=500, text="Error reading template")
            else:
                return web.Response(status=404, text="Template not found")

        @PromptServer.instance.routes.get("/smart-model-loader/templates")
        async def get_loader_templates_list(request):
            # Get list of available loader templates.
            from .loader_templates import get_template_list

            templates = await asyncio.to_thread(get_template_list)
            return web.json_response(templates)

        # ==================== LOADER TEMPLATE SAVE/DELETE (JS-driven, no queue needed) ====================

        @PromptServer.instance.routes.post("/smart-model-loader/templates/save")
        async def save_loader_template_endpoint(request):
            # Save a loader template from JS without needing to queue the workflow.
            # JS sends the full config dict built from widget values.
            denial = global_mutation_denial(request)
            if denial is not None:
                return denial
            try:
                data = await read_json_object_request(request)
                name = data.get("name", "").strip()
                config = data.get("config", {})

                if not name:
                    return web.json_response(
                        {"success": False, "error": "Template name is required"},
                        status=400,
                    )
                if not is_safe_filename(f"{name}.json"):
                    return web.json_response(
                        {"success": False, "error": "Invalid template name"}, status=400,
                    )

                # Snapshot trusted .eclipse.json expected values into the template (plan §4.3).
                try:
                    if isinstance(config, dict):
                        config = await asyncio.to_thread(
                            _overlay_expected_hashes_from_disk, config,
                        )
                    else:
                        return web.json_response(
                            {"success": False, "error": "Template config must be an object"},
                            status=400,
                        )
                except Exception as e:  # noqa: BLE001 - optional metadata overlay boundary
                    log.warning("Smart Loader", f"expected_hashes overlay skipped: {e}")

                from .loader_templates import save_template

                success = await asyncio.to_thread(save_template, name, config)
                if success:
                    log.msg(
                        "Smart Loader", f"\u2713 Template '{name}' saved successfully",
                    )
                    return web.json_response({"success": True})
                log.error(
                    "Smart Loader", f"\u2717 Failed to save template '{name}'",
                )
                return web.json_response(
                    {"success": False, "error": "Failed to save template"},
                    status=500,
                )
            except web.HTTPException:
                raise
            except Exception as e:  # noqa: BLE001 - endpoint boundary sanitizes failures
                log.error(
                    "Smart Loader", f"Template save failed: {type(e).__name__}",
                )
                return web.json_response(
                    {"success": False, "error": "Template save failed"}, status=500,
                )

        @PromptServer.instance.routes.post("/smart-model-loader/templates/delete")
        async def delete_loader_template_endpoint(request):
            # Delete a loader template from JS without needing to queue the workflow.
            denial = global_mutation_denial(request)
            if denial is not None:
                return denial
            try:
                bounded_data = await read_json_object_request(request)
                bounded_name = bounded_data.get("name", "").strip()
                if not bounded_name or not is_safe_filename(f"{bounded_name}.json"):
                    return web.json_response(
                        {"success": False, "error": "Invalid template name"},
                        status=400,
                    )
                deleted_models = await asyncio.to_thread(
                    delete_template_transaction,
                    bounded_name,
                    delete_models=bounded_data.get("delete_models") is True,
                )
                return web.json_response(
                    {"success": True, "deleted_models": deleted_models},
                )
            except BlockingIOError:
                return web.json_response(
                    {"success": False, "error": "Prompt queue is active"}, status=409,
                )
            except FileNotFoundError:
                return web.json_response(
                    {"success": False, "error": "Template not found"}, status=404,
                )
            except web.HTTPException:
                raise
            except (OSError, ValueError) as error:
                log.error("Smart Loader", f"Template deletion failed: {type(error).__name__}")
                return web.json_response(
                    {"success": False, "error": "Template deletion failed"}, status=500,
                )

        # ==================== CIVITAI DOWNLOAD (locator-first: AIR/SHA) ====================

        @PromptServer.instance.routes.post("/smart-model-loader/civitai/download")
        async def civitai_download_endpoint(request):
            # Download a model file using AIR or SHA locator and save to the target role folder.
            # Filename is resolved from CivitAI metadata, not provided by user.
            denial = global_mutation_denial(request)
            if denial is not None:
                return denial
            data = await read_json_object_request(request)

            target_role = str(data.get("target_role") or "").strip()
            # Treat JSON null/None safely (str(None) would become the literal "None").
            air = str(data.get("air") or "").strip() or None
            sha256 = str(data.get("sha256") or "").strip() or None
            requested_filename = (
                str(data.get("requested_filename") or "").strip() or None
            )
            download_preference = str(
                data.get("download_preference") or "default",
            ).strip()
            try:
                overwrite = require_json_boolean(data, "overwrite")
            except TypeError as error:
                return web.json_response(
                    {"success": False, "error": str(error)},
                    status=400,
                )
            node_id = data.get("node_id")
            supplied_download_id = data.get("download_id")
            if supplied_download_id is None:
                download_id = uuid.uuid4().hex
            elif isinstance(supplied_download_id, str) and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]{19,127}", supplied_download_id,
            ):
                download_id = supplied_download_id
            else:
                return web.json_response(
                    {"success": False, "error": "Invalid download identity"},
                    status=400,
                )
            conflict_policy = (
                str(data.get("conflict_policy", "skip") or "skip").strip().lower()
            )
            if conflict_policy not in {"skip", "overwrite", "rename"}:
                conflict_policy = "skip"
            if overwrite:
                conflict_policy = "overwrite"

            progress_state = {
                "filename": requested_filename or "CivitAI model",
                "phase": None,
                "event_key": None,
            }
            progress_console = ConsolePhaseProgress("CivitAI")

            def _emit_progress(
                phase: str,
                downloaded: int = 0,
                total: int = 0,
                *,
                terminal: bool = False,
                abortable: bool = False,
            ) -> None:
                pct = min(100, int(downloaded / total * 100)) if total else 0
                phase_changed = progress_state["phase"] != phase
                if phase_changed:
                    progress_state["phase"] = phase
                if phase == "resolving":
                    if phase_changed:
                        log.msg(
                            "CivitAI",
                            f"{progress_state['filename']}: {phase}",
                        )
                else:
                    progress_console.update(
                        progress_state["filename"],
                        phase,
                        downloaded,
                        total,
                        terminal=terminal,
                    )
                event_step = pct if total else downloaded // (64 * 1024 * 1024)
                event_key = (phase, event_step, terminal, abortable)
                if node_id is None or progress_state["event_key"] == event_key:
                    return
                progress_state["event_key"] = event_key
                try:
                    PromptServer.instance.send_sync(
                        "smart-model-loader.download-progress",
                        {
                            "node_id": node_id,
                            "download_id": download_id,
                            "phase": phase,
                            "terminal": terminal,
                            "abortable": abortable,
                            "pct": pct,
                            "downloaded": downloaded,
                            "total": total,
                            "filename": progress_state["filename"],
                        },
                    )
                except Exception:  # noqa: BLE001 - websocket transport failures are non-fatal
                    log.debug("CivitAI", "Could not publish download progress event")

            api_key = str(get_config_value("civitai_api_key", "") or "").strip()
            if not api_key:
                return web.json_response(
                    {
                        "success": False,
                        "error": "CivitAI API key not set — add it in Smart Model Loader settings.",
                    },
                    status=400,
                )

            if not air and not sha256:
                return web.json_response(
                    {
                        "success": False,
                        "error": "No AIR or SHA provided. Paste one into expected_sha_or_air first.",
                    },
                    status=400,
                )

            if air and not parse_air(air):
                return web.json_response(
                    {
                        "success": False,
                        "error": "Malformed AIR (expected urn:air:... format).",
                    },
                    status=400,
                )

            if sha256:
                import re as _re

                if not _re.match(r"^[0-9a-fA-F]{64}$", sha256):
                    return web.json_response(
                        {
                            "success": False,
                            "error": "Invalid SHA256 (must be 64 hex chars).",
                        },
                        status=400,
                    )

            role_to_folder = {
                "checkpoints": "checkpoints",
                "diffusion_models": "diffusion_models",
                "diffusion_models_gguf": "diffusion_models_gguf",
                "unet": "diffusion_models",
                "vae": "vae",
                "text_encoders": "text_encoders",
                "clip": "clip",
                "loras": "loras",
                "embeddings": "embeddings",
                "clip_vision": "clip_vision",
            }
            folder_key = role_to_folder.get(target_role)
            if folder_key is None or folder_key not in folder_paths.folder_names_and_paths:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Unknown target role/folder: {target_role}",
                    },
                    status=400,
                )

            try:
                _emit_progress("resolving")
                async with _MODEL_IO_SEMAPHORE:
                    resolved = await asyncio.to_thread(
                        resolve_file_for_download,
                        air=air,
                        sha256=sha256,
                        api_key=api_key,
                        download_preference=download_preference,
                        target_role=target_role,
                    )
            except CivitaiSelectionError as error:
                log.warning("CivitAI", f"File selection failed: {error}")
                _emit_progress("failed", terminal=True)
                return web.json_response(
                    {
                        "success": False,
                        "error": str(error),
                        "available_files": error.available_files,
                        "available_precisions": error.available_precisions,
                        "download_id": download_id,
                    },
                    status=422,
                )
            except (TypeError, ValueError) as error:
                log.warning("CivitAI", f"Identity validation failed: {type(error).__name__}")
                _emit_progress("failed", terminal=True)
                return web.json_response(
                    {
                        "success": False,
                        "error": "CivitAI identity validation failed",
                        "download_id": download_id,
                    },
                    status=422,
                )
            except (OSError, requests.RequestException) as error:
                log.error("CivitAI", f"Resolve failed: {type(error).__name__}")
                _emit_progress("failed", terminal=True)
                return web.json_response(
                    {
                        "success": False,
                        "error": "CivitAI request failed",
                        "download_id": download_id,
                    },
                    status=500,
                )

            if not resolved:
                _emit_progress("failed", terminal=True)
                return web.json_response(
                    {
                        "success": False,
                        "error": "Could not resolve a downloadable file from AIR/SHA.",
                        "download_id": download_id,
                    },
                    status=404,
                )

            progress_state["filename"] = resolved["filename"]

            folder_paths_list = folder_paths.get_folder_paths(folder_key)
            if not folder_paths_list:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"No folder path configured for {folder_key}",
                    },
                    status=500,
                )

            selected_path = folder_paths_list[0]
            for p in folder_paths_list:
                if Path(p).name.lower() == target_role.lower():
                    selected_path = p
                    break

            try:
                root_dir, destination, relative_filename = await asyncio.to_thread(
                    prepare_download_destination,
                    selected_path,
                    requested_filename=requested_filename,
                    resolved_filename=resolved["filename"],
                )
            except (FileNotFoundError, OSError, ValueError):
                return web.json_response(
                    {"success": False, "error": "Unsafe download destination."},
                    status=400,
                )

            safe_name = destination.name
            destination_extension = Path(safe_name).suffix.lower()
            source_extension = Path(resolved["filename"]).suffix.lower()
            allowed_extensions = set(SAFE_TENSOR_EXTENSIONS)
            if folder_key in {"diffusion_models", "diffusion_models_gguf", "clip", "text_encoders"}:
                allowed_extensions.update(GGUF_EXTENSIONS)
            if get_config_value("allow_legacy_model_formats", False) is True:
                allowed_extensions.update(LEGACY_MODEL_EXTENSIONS)
            if (
                destination_extension not in allowed_extensions
                or source_extension not in allowed_extensions
                or not (
                    destination_extension == source_extension
                    or {
                        destination_extension,
                        source_extension,
                    }.issubset(SAFE_TENSOR_EXTENSIONS)
                )
            ):
                return web.json_response(
                    {"success": False, "error": "CivitAI file format is not permitted for this role"},
                    status=422,
                )

            try:
                root_dir, destination, relative_filename = await asyncio.to_thread(
                    prepare_download_destination,
                    selected_path,
                    requested_filename=requested_filename,
                    resolved_filename=resolved["filename"],
                    create_parents=True,
                )
            except (FileNotFoundError, OSError, ValueError):
                return web.json_response(
                    {"success": False, "error": "Unsafe download destination."},
                    status=400,
                )

            if destination.exists():
                if conflict_policy == "skip":
                    _emit_progress("verifying")
                    existing_result = await asyncio.to_thread(
                        verify_hash,
                        destination,
                        resolved["sha256"],
                        on_mismatch="error",
                    )
                    if existing_result.get("status") != "ok":
                        _emit_progress("failed", terminal=True)
                        return web.json_response(
                            {
                                "success": False,
                                "error": "Existing file does not match CivitAI SHA-256",
                            },
                            status=422,
                        )
                    existing_relative = destination.relative_to(root_dir).as_posix()
                    metadata_written = await asyncio.to_thread(
                        write_expected,
                        destination,
                        air=resolved.get("air") or air,
                        sha256=resolved["sha256"],
                        reference_type="civitai",
                        folder_role=folder_key,
                        relative_path=existing_relative,
                    )
                    if not metadata_written:
                        _emit_progress("failed", terminal=True)
                        return web.json_response(
                            {
                                "success": False,
                                "error": "Verified file metadata could not be persisted",
                            },
                            status=500,
                        )
                    _emit_progress("completed", terminal=True)
                    return web.json_response(
                        {
                            "success": True,
                            "status": "skipped_existing",
                            "filename": destination.name,
                            "air": resolved.get("air"),
                            "sha256": resolved.get("sha256"),
                            "precision": resolved.get("precision"),
                            "download_id": download_id,
                        },
                    )
                if conflict_policy == "rename":
                    stem = destination.stem
                    suffix = destination.suffix
                    parent = destination.parent
                    idx = 1
                    candidate = destination
                    while candidate.exists():
                        candidate = parent / f"{stem}_{idx}{suffix}"
                        idx += 1
                    destination = candidate
                # conflict_policy == overwrite falls through and replaces file

            # Update safe_name in case it was renamed during conflict resolution
            safe_name = destination.name

            # Relative filename for response (includes subdirectory if present).
            relative_filename = destination.relative_to(root_dir).as_posix()

            progress_state["filename"] = safe_name

            def _progress_cb(downloaded, total):
                _emit_progress(
                    "transferring",
                    downloaded,
                    total,
                    abortable=True,
                )

            def _phase_cb(phase, downloaded, total):
                _emit_progress(
                    phase,
                    downloaded,
                    total,
                    abortable=phase == "transferring",
                )

            if not reserve_download_id(download_id):
                _emit_progress("failed", terminal=True)
                return web.json_response(
                    {
                        "success": False,
                        "error": "Download identity is already in use",
                        "download_id": download_id,
                    },
                    status=409,
                )

            try:
                try:
                    async with _MODEL_IO_SEMAPHORE:
                        ok = await asyncio.to_thread(
                            download_file,
                            url=resolved["download_url"],
                            destination=destination,
                            api_key=api_key,
                            expected_sha256=resolved["sha256"],
                            expected_size=resolved.get("expected_size"),
                            progress_cb=_progress_cb,
                            phase_cb=_phase_cb,
                            download_id=download_id,
                            require_idle_promotion=True,
                            allow_replace_existing=conflict_policy == "overwrite",
                        )
                except DownloadCancelled:
                    _emit_progress("aborted", terminal=True)
                    return web.json_response(
                        {
                            "success": False,
                            "status": "aborted",
                            "error": "Download transfer was aborted",
                            "download_id": download_id,
                        },
                        status=409,
                    )
                except DownloadDestinationBusy:
                    _emit_progress("failed", terminal=True)
                    return web.json_response(
                        {
                            "success": False,
                            "error": "Download destination is already in use",
                            "download_id": download_id,
                        },
                        status=409,
                    )
                except BlockingIOError:
                    _emit_progress("failed", terminal=True)
                    return web.json_response(
                        {
                            "success": False,
                            "error": "Prompt queue is active",
                            "download_id": download_id,
                        },
                        status=409,
                    )
                if not ok:
                    _emit_progress("failed", terminal=True)
                    return web.json_response(
                        {
                            "success": False,
                            "error": "Download failed. Check logs for details.",
                            "download_id": download_id,
                        },
                        status=500,
                    )

                expected_sha = resolved["sha256"]
                verify_size = destination.stat().st_size
                _emit_progress("verifying", 0, verify_size)

                def _verify_progress(processed, total):
                    _emit_progress("verifying", processed, total)

                async with _MODEL_IO_SEMAPHORE:
                    verify_result = await asyncio.to_thread(
                        verify_hash,
                        destination,
                        expected_sha,
                        on_mismatch="warn",
                        progress_cb=_verify_progress,
                    )

                if verify_result.get("status") != "ok":
                    _emit_progress("failed", terminal=True)
                    return web.json_response(
                        {
                            "success": False,
                            "error": "Downloaded file failed integrity verification",
                            "download_id": download_id,
                        },
                        status=422,
                    )

                relative_path = destination.relative_to(root_dir).as_posix()
                metadata_written = await asyncio.to_thread(
                    write_expected,
                    destination,
                    air=resolved.get("air") or air,
                    sha256=expected_sha,
                    reference_type="civitai",
                    folder_role=folder_key,
                    relative_path=relative_path,
                )
                if not metadata_written:
                    _emit_progress("failed", terminal=True)
                    return web.json_response(
                        {
                            "success": False,
                            "error": "Verified download metadata could not be persisted",
                            "download_id": download_id,
                        },
                        status=500,
                    )

                _emit_progress("completed", terminal=True)
                return web.json_response(
                    {
                        "success": True,
                        "status": "downloaded",
                        "filename": relative_filename,
                        "air": resolved.get("air") or air,
                        "sha256": (
                            expected_sha.lower()
                            if isinstance(expected_sha, str)
                            else None
                        ),
                        "precision": resolved.get("precision"),
                        "verify_status": verify_result.get("status"),
                        "unverified": False,
                        "model_version_id": resolved.get("model_version_id"),
                        "file_id": resolved.get("file_id"),
                        "download_id": download_id,
                    },
                )
            finally:
                release_download_id(download_id)

        @PromptServer.instance.routes.post("/smart-model-loader/civitai/download/cancel")
        async def civitai_download_cancel_endpoint(request):
            denial = global_mutation_denial(request)
            if denial is not None:
                return denial
            data = await read_json_object_request(request)
            download_id = data.get("download_id")
            if not isinstance(download_id, str) or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]{19,127}", download_id,
            ) is None:
                return web.json_response(
                    {"success": False, "error": "Invalid download identity"},
                    status=400,
                )
            result = await asyncio.to_thread(cancel_active_download, download_id)
            if result == "cancelling":
                return web.json_response(
                    {
                        "success": True,
                        "status": "cancelling",
                        "download_id": download_id,
                    },
                )
            if result == "not-transferring":
                return web.json_response(
                    {
                        "success": False,
                        "error": "Download is no longer in the transferable phase",
                        "download_id": download_id,
                    },
                    status=409,
                )
            return web.json_response(
                {
                    "success": False,
                    "error": "Active download was not found",
                    "download_id": download_id,
                },
                status=404,
            )

        # ==================== INTEGRITY PROMOTE (rename retry → original) ====================

        @PromptServer.instance.routes.post("/smart-model-loader/integrity/promote")
        async def integrity_promote_endpoint(request):
            # After a successful re-download, rename the verified file to the original name
            # and delete all previous retry files (garbage from earlier failed attempts).
            # Body: {target_role, original_filename, replacement_filename, cleanup_filenames[]}
            denial = global_mutation_denial(request)
            if denial is not None:
                return denial
            try:
                bounded_data = await read_json_object_request(request)
                deleted = await asyncio.to_thread(
                    promote_verified_replacement,
                    role=str(bounded_data.get("target_role") or "").strip(),
                    original_filename=str(
                        bounded_data.get("original_filename") or "",
                    ).strip(),
                    replacement_filename=str(
                        bounded_data.get("replacement_filename") or "",
                    ).strip(),
                    expected_sha256=str(
                        bounded_data.get("expected_sha256") or "",
                    ).strip(),
                    cleanup_filenames=bounded_data.get("cleanup_filenames")
                    if isinstance(bounded_data.get("cleanup_filenames"), list)
                    else [],
                )
                return web.json_response({"success": True, "deleted": deleted})
            except BlockingIOError:
                return web.json_response(
                    {"success": False, "error": "Prompt queue is active"}, status=409,
                )
            except FileNotFoundError:
                return web.json_response(
                    {"success": False, "error": "Replacement file not found"}, status=404,
                )
            except ValueError:
                return web.json_response(
                    {"success": False, "error": "Replacement failed integrity validation"},
                    status=422,
                )
            except web.HTTPException:
                raise
            except OSError as error:
                log.error("Promote", f"Promotion failed: {type(error).__name__}")
                return web.json_response(
                    {"success": False, "error": "Promotion failed"}, status=500,
                )

        # ==================== INTEGRITY VERIFY (present files) ====================

        @PromptServer.instance.routes.post("/smart-model-loader/integrity/verify")
        async def integrity_verify_endpoint(request):
            # Verify a present model file's SHA256 against an entered expected value.
            # Persists the expected value into <file>.eclipse.json first, then compares.
            denial = global_mutation_denial(request)
            if denial is not None:
                return denial
            try:
                bounded_data = await read_json_object_request(request)
            except web.HTTPException:
                raise
            except Exception:  # noqa: BLE001 - endpoint boundary sanitizes failures
                return web.json_response(
                    {"success": False, "error": "Invalid JSON body"}, status=400,
                )

            bounded_role = str(bounded_data.get("target_role") or "").strip()
            bounded_filename = str(bounded_data.get("filename") or "").strip()
            bounded_expected = str(bounded_data.get("air_or_hash") or "").strip()
            bounded_preference = str(
                bounded_data.get("download_preference") or "default",
            ).strip()
            try:
                _root, bounded_path, bounded_relative = await asyncio.to_thread(
                    resolve_role_target, bounded_role, bounded_filename,
                )
            except FileNotFoundError:
                return web.json_response(
                    {"success": False, "error": "File not found"}, status=404,
                )
            except ValueError:
                return web.json_response(
                    {"success": False, "error": "Invalid model target"}, status=400,
                )

            bounded_sha = None
            bounded_air = None
            if bounded_expected.lower().startswith("urn:air:"):
                bounded_air = bounded_expected
                try:
                    resolved_identity = await asyncio.to_thread(
                        resolve_file_for_download,
                        air=bounded_air,
                        sha256=None,
                        api_key=str(get_config_value("civitai_api_key", "") or "") or None,
                        download_preference=bounded_preference,
                    )
                    bounded_sha = resolved_identity["sha256"] if resolved_identity else None
                except (OSError, ValueError, requests.RequestException):
                    return web.json_response(
                        {"success": False, "error": "CivitAI identity could not be verified"},
                        status=422,
                    )
            elif re.fullmatch(r"[0-9a-fA-F]{64}", bounded_expected):
                bounded_sha = bounded_expected.lower()
            else:
                disk_identity = await asyncio.to_thread(read_expected, bounded_path)
                if disk_identity:
                    bounded_sha = disk_identity.get("sha256")
                    bounded_air = disk_identity.get("air")
            if not bounded_sha:
                return web.json_response(
                    {"success": False, "error": "A verified expected SHA-256 is required"},
                    status=422,
                )

            bounded_result = await asyncio.to_thread(
                verify_hash,
                bounded_path,
                bounded_sha,
                on_mismatch="error",
                folder_role=bounded_role,
                relative_path=bounded_relative,
            )
            if bounded_result.get("status") != "ok":
                return web.json_response(
                    {
                        "success": False,
                        "status": bounded_result.get("status"),
                        "actual": bounded_result.get("actual"),
                        "expected": bounded_sha,
                        "expected_precision": bounded_preference,
                        "filename": Path(bounded_filename).name,
                        "error": "Integrity verification failed",
                    },
                    status=422,
                )
            metadata_written = await asyncio.to_thread(
                write_expected,
                bounded_path,
                air=bounded_air,
                sha256=bounded_sha,
                precision=bounded_preference,
                reference_type="civitai" if bounded_air else "expected",
                folder_role=bounded_role,
                relative_path=bounded_relative,
            )
            if not metadata_written:
                return web.json_response(
                    {"success": False, "error": "Verified metadata could not be persisted"},
                    status=500,
                )
            return web.json_response(
                {
                    "success": True,
                    "status": "ok",
                    "actual": bounded_result.get("actual"),
                    "expected": bounded_sha,
                    "expected_precision": bounded_preference,
                    "filename": Path(bounded_filename).name,
                },
            )

        # ==================== MODEL FILE LISTS ====================

        @PromptServer.instance.routes.get("/smart-model-loader/model-files")
        async def get_all_model_files(request):
            # GET /smart-model-loader/model-files
            #
            # Returns all model file lists in one request for efficiency.
            def collect_model_files():
                result = {}
                folders = [
                    "checkpoints",
                    "diffusion_models",
                    "vae",
                    "loras",
                    "clip",
                    "text_encoders",
                ]
                if "diffusion_models_gguf" in folder_paths.folder_names_and_paths:
                    folders.append("diffusion_models_gguf")
                for folder_type in folders:
                    try:
                        files = folder_paths.get_filename_list(folder_type)
                        result[folder_type] = ["None", *files]
                    except Exception:  # noqa: BLE001 - optional reload boundary
                        result[folder_type] = ["None"]
                clip_combined = set(result.get("clip", ["None"]))
                clip_combined.update(result.get("text_encoders", []))
                result["clip_combined"] = sorted(clip_combined)
                return result

            return web.json_response(await asyncio.to_thread(collect_model_files))

        # ==================== RELOAD ALL ====================
class StandaloneConfigEndpoints:
    def __init__(self) -> None:
        self._register_endpoints()

    def _register_endpoints(self) -> None:
        from .credentials import get_auth_token_status

        @PromptServer.instance.routes.get("/smart-model-loader/config/all")
        async def get_all_config(_request):
            hf_configured, hf_source = get_auth_token_status("huggingface")
            try:
                chip_color = normalize_chip_color(
                    get_config_value("chip_color", DEFAULT_CHIP_COLOR),
                )
            except ValueError:
                chip_color = DEFAULT_CHIP_COLOR
            return web.json_response(
                {
                    "log_level": get_config_value("log_level", "warning"),
                    "use_sliders": get_config_value("use_sliders", True),
                    "allow_legacy_model_formats": get_config_value(
                        "allow_legacy_model_formats", False,
                    ),
                    "retry_download_attempts": get_config_value(
                        "retry_download_attempts", 2,
                    ),
                    "chip_color": chip_color,
                    "civitai_api_key_configured": bool(
                        get_config_value("civitai_api_key", ""),
                    ),
                    "hf_token_configured": hf_configured,
                    "hf_token_source": hf_source,
                    "has_native_dynamic_vram": _HAS_NATIVE_DYNAMIC_VRAM,
                },
            )

        @PromptServer.instance.routes.post("/smart-model-loader/config/update")
        async def update_standalone_config(request):
            denial = global_mutation_denial(request)
            if denial is not None:
                return denial
            data = await read_json_object_request(request, max_bytes=16 * 1024)
            allowed = {
                "log_level",
                "use_sliders",
                "allow_legacy_model_formats",
                "retry_download_attempts",
                "chip_color",
                "civitai_api_key",
                "hf_token",
            }
            if set(data) - allowed:
                return web.json_response(
                    {"success": False, "error": "Unknown configuration key"},
                    status=400,
                )
            updates: dict[str, Any] = {}
            for key, value in data.items():
                if key == "log_level":
                    if value not in {"error", "warning", "info", "debug"}:
                        return web.json_response(
                            {"success": False, "error": "Invalid log level"}, status=400,
                        )
                elif key in {"use_sliders", "allow_legacy_model_formats"}:
                    if not isinstance(value, bool):
                        return web.json_response(
                            {"success": False, "error": f"{key} must be boolean"},
                            status=400,
                        )
                elif key == "retry_download_attempts":
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, int)
                        or not 0 <= value <= 10
                    ):
                        return web.json_response(
                            {"success": False, "error": "Retries must be from 0 through 10"},
                            status=400,
                        )
                elif key == "chip_color":
                    try:
                        value = normalize_chip_color(value)
                    except ValueError as error:
                        return web.json_response(
                            {"success": False, "error": str(error)}, status=400,
                        )
                elif not isinstance(value, str) or len(value) > 8192:
                    return web.json_response(
                        {"success": False, "error": f"{key} must be a bounded string"},
                        status=400,
                    )
                updates[key] = value
            if updates and not update_config_values(updates):
                return web.json_response(
                    {"success": False, "error": "Configuration update failed"},
                    status=500,
                )
            log._reload_config()
            return web.json_response(
                {
                    "success": True,
                    "updated": {
                        key: bool(value) if key in {"civitai_api_key", "hf_token"} else value
                        for key, value in updates.items()
                    },
                },
            )


_STANDALONE_ENDPOINTS_REGISTERED = False


def initialize_endpoints() -> None:
    global _STANDALONE_ENDPOINTS_REGISTERED
    if _STANDALONE_ENDPOINTS_REGISTERED:
        return
    StandaloneConfigEndpoints()
    LoaderEndpoints()
    _STANDALONE_ENDPOINTS_REGISTERED = True
    log.msg("", "Loader endpoints initialized")
