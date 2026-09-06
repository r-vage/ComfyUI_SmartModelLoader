from __future__ import annotations

# VAE Loader Video+Audio [Eclipse] — Dual video/image and audio VAE loader
#
# Loads a video/image VAE and any ComfyUI-supported audio VAE in one node, both
# from the vae folder, and outputs them on separate sockets.
import folder_paths  # type: ignore
from comfy_api.latest import io  # type: ignore

from ..core import CATEGORY
from ..core.logger import log
from ..core.model_loader.validation import LoaderValidationError, resolve_model_file
from ..core.model_loader_common import load_custom_vae

_LOG_PREFIX = "VAE Loader Video+Audio"


class RvLoader_VaeLoaderVideoAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        vaes = ["None", *folder_paths.get_filename_list("vae")]

        return io.Schema(
            node_id="VAE Loader Video+Audio [Eclipse]",
            display_name="VAE Loader Video+Audio",
            category=CATEGORY.MAIN.value + CATEGORY.LOADER.value,
            description="Load a video/image VAE and a ComfyUI-supported audio VAE "
            "in one node (both from the vae folder), including MiniMax H3 and LTX.",
            inputs=[
                io.Combo.Input(
                    "video_vae",
                    options=vaes,
                    default="None",
                    tooltip="Video/image VAE file (vae folder). Set to None to skip.",
                ),
                io.Combo.Input(
                    "audio_vae",
                    options=vaes,
                    default="None",
                    tooltip="ComfyUI-supported audio VAE file, such as MiniMax H3 or LTX, from the vae folder. Set to None to skip.",
                ),
                io.Boolean.Input(
                    "disable_offload",
                    default=True,
                    tooltip="Keep VAEs on GPU (disable offloading).",
                ),
            ],
            outputs=[
                io.Vae.Output("video_vae"),
                io.Vae.Output("audio_vae"),
            ],
        )

    @classmethod
    def validate_inputs(cls, **kwargs):
        try:
            for field in ("video_vae", "audio_vae"):
                name = kwargs.get(field, "None")
                if name not in (None, "", "None"):
                    resolve_model_file("vae", name, reference_type="vae")
        except LoaderValidationError as error:
            return str(error)
        return True

    @classmethod
    def execute(cls, video_vae="None", audio_vae="None", disable_offload=True):
        loaded_video_vae = None
        loaded_audio_vae = None

        if video_vae not in (None, "", "None"):
            loaded_video_vae = load_custom_vae(
                video_vae, disable_offload=disable_offload,
            )
            log.msg(_LOG_PREFIX, f"Loaded video VAE: {video_vae}")

        if audio_vae not in (None, "", "None"):
            loaded_audio_vae = load_custom_vae(
                audio_vae, disable_offload=disable_offload,
            )
            log.msg(_LOG_PREFIX, f"Loaded audio VAE: {audio_vae}")

        return io.NodeOutput(loaded_video_vae, loaded_audio_vae)
