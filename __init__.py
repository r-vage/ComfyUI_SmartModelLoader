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
        from .py.RvLoader_ClipLoader import RvLoader_ClipLoader
        from .py.RvLoader_ModelLoader import RvLoader_ModelLoader
        from .py.RvLoader_ModelLoaderPipe import RvLoader_ModelLoaderPipe
        from .py.RvLoader_SmartModelLoader import RvLoader_SmartModelLoader
        from .py.RvLoader_VaeLoader import RvLoader_VaeLoader
        from .py.RvLoader_VaeLoaderVideoAudio import RvLoader_VaeLoaderVideoAudio

        return [
            RvLoader_SmartModelLoader,
            RvLoader_ModelLoader,
            RvLoader_ModelLoaderPipe,
            RvLoader_ClipLoader,
            RvLoader_VaeLoader,
            RvLoader_VaeLoaderVideoAudio,
        ]


async def comfy_entrypoint() -> SmartModelLoaderExtension:
    return SmartModelLoaderExtension()
