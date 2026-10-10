"""Per-model dense attention selection using ComfyUI's native patcher API."""

from ..logger import log

ATTENTION_BACKEND_DEFAULT = "pytorch attention"
ATTENTION_BACKENDS = {
    "pytorch attention": "pytorch",
    "comfy kitchen attention": "comfy_kitchen_int8",
}
ATTENTION_BACKEND_TOOLTIP = (
    "Dense attention backend for the diffusion model, not CLIP. "
    "PyTorch is the default. Comfy Kitchen uses quantized INT8 attention on supported Nvidia/AMD GPUs. "
    "Custom kernels that bypass ComfyUI attention retain their own backend."
)


def get_attention_backend_options() -> list[str]:
    from comfy.ldm.modules import attention

    options = [ATTENTION_BACKEND_DEFAULT]
    if getattr(attention, "COMFY_KITCHEN_INT8_ATTENTION_IS_AVAILABLE", False):
        options.append("comfy kitchen attention")
    return options


def apply_attention_backend(model, backend: str = ATTENTION_BACKEND_DEFAULT):
    if backend not in ATTENTION_BACKENDS:
        raise ValueError("Invalid attention_backend")
    if model is None:
        return None

    from comfy.ldm.modules import attention

    attention_function = attention.get_attention_function(ATTENTION_BACKENDS[backend], None)
    if attention_function is None:
        log.warning(
            "Attention Backend",
            "Comfy Kitchen attention is unavailable; using PyTorch attention.",
            notify=True,
        )
        attention_function = attention.get_attention_function("pytorch")
    patched = model.clone()
    patched.set_model_optimized_attention(attention_function)
    return patched
