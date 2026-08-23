# Vendored from ComfyUI-GGUF by City96
# License: Apache-2.0 (apache.org/licenses/LICENSE-2.0)
# Source: https://github.com/city96/ComfyUI-GGUF
#
# This is a frozen copy to prevent breakage from upstream updates.
# The `gguf` pip package is still required at runtime.

from .dequant import dequantize_tensor, is_quantized, is_torch_compatible
from .loader import gguf_clip_loader, gguf_sd_loader
from .nodes import GGUFModelPatcher
from .ops import GGMLLayer, GGMLOps, GGMLTensor, move_patch_to_device
