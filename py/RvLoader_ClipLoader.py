from __future__ import annotations

# CLIP Loader [Eclipse] — Standalone external CLIP loader
#
# Loads 1-4 CLIP models from files with configurable architecture type.
# For baked CLIP from checkpoints, use Model Loader instead.
from pathlib import Path

import comfy  # type: ignore
import comfy.sd  # type: ignore
import folder_paths  # type: ignore
from comfy_api.latest import io  # type: ignore

from ..core import CATEGORY, SLIDER_DISPLAY
from ..core.gguf_wrapper import GGUF_AVAILABLE, load_gguf_clip
from ..core.logger import log
from ..core.model_loader.validation import (
    get_clip_type_options,
    resolve_clip_type,
)

_LOG_PREFIX = "CLIP Loader"


class RvLoader_ClipLoader(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        clip_type_options = get_clip_type_options(comfy.sd.CLIPType)
        clip_type_default = (
            "flux" if "flux" in clip_type_options else clip_type_options[0]
        )

        # Get available CLIP files from both clip and text_encoders folders (deduplicated)
        clip_files = list(folder_paths.get_filename_list("clip"))
        if "text_encoders" in folder_paths.folder_names_and_paths:
            clip_files.extend(folder_paths.get_filename_list("text_encoders"))
        clips = ["None", *sorted(set(clip_files))]

        return io.Schema(
            node_id="CLIP Loader [Eclipse]",
            display_name="CLIP Loader",
            category=CATEGORY.MAIN.value + CATEGORY.LOADER.value,
            description="Load 1-4 external CLIP models. For baked CLIP from checkpoints, use Model Loader.",
            inputs=[
                io.Int.Input(
                    "clip_count",
                    default=1,
                    min=1,
                    max=4,
                    step=1,
                    display_mode=SLIDER_DISPLAY,
                    tooltip="Number of CLIP models to load",
                ),
                io.Combo.Input(
                    "clip_name1",
                    options=clips,
                    default="None",
                    tooltip="Primary CLIP model",
                ),
                io.Combo.Input(
                    "clip_name2",
                    options=clips,
                    default="None",
                    tooltip="Secondary CLIP model",
                ),
                io.Combo.Input(
                    "clip_name3",
                    options=clips,
                    default="None",
                    tooltip="Third CLIP model",
                ),
                io.Combo.Input(
                    "clip_name4",
                    options=clips,
                    default="None",
                    tooltip="Fourth CLIP model",
                ),
                io.Combo.Input(
                    "clip_type",
                    options=list(clip_type_options),
                    default=clip_type_default,
                    tooltip="CLIP architecture type",
                ),
            ],
            outputs=[
                io.Clip.Output("clip"),
            ],
        )

    @classmethod
    def validate_inputs(cls, **kwargs):
        return True

    @classmethod
    def execute(cls, **kwargs):
        clip_count = kwargs.get("clip_count", 1)
        clip_name1 = kwargs.get("clip_name1", "None")
        clip_name2 = kwargs.get("clip_name2", "None")
        clip_name3 = kwargs.get("clip_name3", "None")
        clip_name4 = kwargs.get("clip_name4", "None")
        clip_type_options = get_clip_type_options(comfy.sd.CLIPType)
        clip_type = kwargs.get(
            "clip_type",
            "flux" if "flux" in clip_type_options else clip_type_options[0],
        )
        resolved_clip_type = resolve_clip_type(clip_type, comfy.sd.CLIPType)

        clip_names = [clip_name1, clip_name2, clip_name3, clip_name4]
        clip_paths = []

        for i in range(clip_count):
            clip_name = clip_names[i] if i < len(clip_names) else "None"
            if clip_name not in (None, "", "None"):
                clip_path = folder_paths.get_full_path("clip", clip_name)
                if clip_path and Path(clip_path).is_file():
                    clip_paths.append(clip_path)
                else:
                    log.warning(
                        _LOG_PREFIX, f"CLIP file '{clip_name}' not found, skipping",
                    )

        if not clip_paths:
            raise ValueError(
                "No valid CLIP files found. Please select at least one CLIP model.",
            )

        # Check if any CLIP file is GGUF — requires special loading path
        has_gguf_clip = any(p.lower().endswith(".gguf") for p in clip_paths)

        if has_gguf_clip:
            if not GGUF_AVAILABLE:
                raise ImportError(
                    "GGUF text encoder selected but GGUF support is not available. Install the 'gguf' pip package.",
                )
            loaded_clip = load_gguf_clip(
                clip_paths=clip_paths,
                clip_type=resolved_clip_type,
            )
        else:
            loaded_clip = comfy.sd.load_clip(
                ckpt_paths=clip_paths,
                embedding_directory=folder_paths.get_folder_paths("embeddings"),
                clip_type=resolved_clip_type,
            )

        log.msg(
            _LOG_PREFIX, f"Loaded {len(clip_paths)} CLIP model(s) as type '{clip_type}'",
        )

        return io.NodeOutput(loaded_clip)
