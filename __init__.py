# ComfyUI Smart Model Loader extension entry point.
# ruff: noqa: N999

WEB_DIRECTORY = "./js"

import os

from .core import version
from .core.logger import log
from .core.migration import run_migrations

log.msg("", f"Version: {version}")
run_migrations()

try:
    from .core.server_endpoints import initialize_endpoints

    initialize_endpoints()
except (AttributeError, ImportError, OSError, RuntimeError, ValueError) as error:
    log.warning("Endpoints", f"Failed to initialize loader endpoints: {error}")

try:
    from .core.download_manager import (
        initialize_endpoints as initialize_download_manager,
    )

    initialize_download_manager()
except (AttributeError, ImportError, OSError, RuntimeError, ValueError) as error:
    log.warning("Download Manager", f"Failed to initialize endpoints: {error}")

# Retain the high-performance Hugging Face transfer policy used by Eclipse.
os.environ["HF_XET_HIGH_PERFORMANCE"] = "1"

from comfy_api.latest import ComfyExtension, io  # type: ignore


class SmartModelLoaderExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        from .py.RvCond_CLIPTextEncode import RvCond_CLIPTextEncode
        from .py.RvCond_CLIPTextEncodeAdvanced import RvCond_CLIPTextEncodeAdvanced
        from .py.RvCond_ConditioningZeroOut import RvCond_ConditioningZeroOut
        from .py.RvLoader_ClipLoader import RvLoader_ClipLoader
        from .py.RvLoader_ModelLoader import RvLoader_ModelLoader
        from .py.RvLoader_ModelLoaderPipe import RvLoader_ModelLoaderPipe
        from .py.RvLoader_SmartModelLoader import RvLoader_SmartModelLoader
        from .py.RvLoader_VaeLoader import RvLoader_VaeLoader
        from .py.RvLoader_VaeLoaderVideoAudio import RvLoader_VaeLoaderVideoAudio
        from .py.RvPipe_IO_CheckpointLoader import RvPipe_IO_CheckpointLoader
        from .py.RvSampler_KSamplerPipe import RvSampler_KSamplerPipe
        from .py.RvTools_LoraStack import RvTools_LoraStack
        from .py.RvTools_LoraStack_Apply import RvTools_LoraStack_Apply

        try:
            from .py.RvTools_NunchakuPuLID import (
                RvTools_NunchakuPuLIDApply,
                RvTools_NunchakuPuLIDLoader,
            )

            nunchaku_pulid_available = True
        except (ImportError, ModuleNotFoundError, RuntimeError) as error:
            log.warning("NunchakuPuLID", f"Nunchaku PuLID nodes unavailable: {error}")
            nunchaku_pulid_available = False

        node_list: list[type[io.ComfyNode]] = [
            RvLoader_SmartModelLoader,
            RvLoader_ModelLoader,
            RvLoader_ModelLoaderPipe,
            RvLoader_ClipLoader,
            RvLoader_VaeLoader,
            RvLoader_VaeLoaderVideoAudio,
            RvCond_CLIPTextEncode,
            RvCond_CLIPTextEncodeAdvanced,
            RvCond_ConditioningZeroOut,
            RvPipe_IO_CheckpointLoader,
            RvSampler_KSamplerPipe,
            RvTools_LoraStack,
            RvTools_LoraStack_Apply,
        ]

        if nunchaku_pulid_available:
            node_list.extend([RvTools_NunchakuPuLIDLoader, RvTools_NunchakuPuLIDApply])

        return node_list


async def comfy_entrypoint() -> SmartModelLoaderExtension:
    return SmartModelLoaderExtension()
