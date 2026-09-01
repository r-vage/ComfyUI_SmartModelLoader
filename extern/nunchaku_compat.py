"""Compatibility helpers for the separately installed Nunchaku runtime.

The vendored ComfyUI glue stays stable while this module applies narrowly scoped
runtime compatibility fixes that cannot be expressed through package pins.
"""

import logging
import sys
import warnings
from contextlib import contextmanager

import torch  # type: ignore

_EMPTY_FP32_MESSAGE = (
    "There are modules in NunchakuFluxTransformer2dModel that should be kept "
    "in float32: []. Casting directly with `to()` can lead to inconsistent "
    "results;"
)


class _EmptyFP32ModuleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.getMessage().startswith(_EMPTY_FP32_MESSAGE)


def get_declared_attribute(instance: object, name: str, default=None):
    """Read a declared attribute without invoking a warning-only ``__getattr__``."""
    instance_attributes = vars(instance)
    if name in instance_attributes:
        return instance_attributes[name]
    for owner in type(instance).__mro__:
        if name in vars(owner):
            return getattr(instance, name)
    return default


def resolve_nunchaku_qwen_transformer() -> type:
    """Resolve the Qwen transformer across stable and nightly module layouts."""
    try:
        from nunchaku import NunchakuQwenImageTransformer2DModel  # type: ignore
    except ImportError:
        from nunchaku.models.qwenimage import (  # type: ignore
            NunchakuQwenImageTransformer2DModel,
        )
    return NunchakuQwenImageTransformer2DModel


def _pad_tensor_compat(
    tensor: torch.Tensor | None,
    multiples: int,
    dim: int,
    fill: complex = 0,
) -> torch.Tensor | None:
    """Match Nunchaku's padding while using PyTorch-compatible tuple indexing."""
    if multiples <= 1 or tensor is None:
        return tensor
    shape = list(tensor.shape)
    if shape[dim] % multiples == 0:
        return tensor
    shape[dim] = ((shape[dim] + multiples - 1) // multiples) * multiples
    result = torch.empty(shape, dtype=tensor.dtype, device=tensor.device)
    result.fill_(fill)
    result[tuple(slice(0, extent) for extent in tensor.shape)] = tensor
    return result


def install_pad_tensor_compatibility() -> bool:
    """Replace only the Nunchaku pad helper that triggers the indexing warning."""
    try:
        from nunchaku import utils as nunchaku_utils  # type: ignore
    except (ImportError, ModuleNotFoundError):
        return False

    original = getattr(nunchaku_utils, "pad_tensor", None)
    if not callable(original) or original is _pad_tensor_compat:
        return False

    probe = torch.tensor([[1.0, 2.0]])
    needs_patch = False
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            padded = original(probe, 4, 1)
        expected = torch.tensor([[1.0, 2.0, 0.0, 0.0]])
        needs_patch = not isinstance(padded, torch.Tensor) or not torch.equal(
            padded,
            expected,
        )
        needs_patch = needs_patch or any(
            "non-tuple sequence for multidimensional indexing" in str(item.message)
            for item in caught
        )
    except (IndexError, RuntimeError, TypeError):
        needs_patch = True

    if not needs_patch:
        return False

    nunchaku_utils.pad_tensor = _pad_tensor_compat
    for module_name, module in tuple(sys.modules.items()):
        if not module_name.startswith("nunchaku.") or module is None:
            continue
        if getattr(module, "pad_tensor", None) is original:
            module.pad_tensor = _pad_tensor_compat
    return True


def validate_nunchaku_hardware(
    quantization_config: dict,
    device: str | torch.device,
) -> None:
    """Validate CUDA availability and the model/GPU quantization pairing."""
    resolved_device = torch.device(device)
    if resolved_device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError(
            "Nunchaku quantized models require a CUDA-capable NVIDIA GPU. "
            f"The selected model device is '{resolved_device}'.",
        )

    from nunchaku.utils import check_hardware_compatibility  # type: ignore

    check_hardware_compatibility(quantization_config, resolved_device)


@contextmanager
def suppress_empty_fp32_module_warning():
    """Hide Diffusers' false-positive warning when the FP32 module list is empty."""
    diffusers_logger = logging.getLogger("diffusers.models.modeling_utils")
    log_filter = _EmptyFP32ModuleFilter()
    diffusers_logger.addFilter(log_filter)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=(
                r"There are modules in NunchakuFluxTransformer2dModel that should "
                r"be kept in float32: \[\]\. Casting directly with `to\(\)` can lead "
                r"to inconsistent results;.*"
            ),
            category=UserWarning,
        )
        try:
            yield
        finally:
            diffusers_logger.removeFilter(log_filter)


@contextmanager
def suppress_pulid_dependency_deprecations():
    """Hide only known PuLID dependency migration notices at its boundary."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Importing from timm\.models\.layers is deprecated.*",
            category=FutureWarning,
            module=r"timm\.models\.layers",
        )
        warnings.filterwarnings(
            "ignore",
            message=r"The parameter 'pretrained' is deprecated since 0\.13.*",
            category=UserWarning,
            module=r"torchvision\.models\._utils",
        )
        warnings.filterwarnings(
            "ignore",
            message=r"Arguments other than a weight enum or `None` for 'weights'.*",
            category=UserWarning,
            module=r"torchvision\.models\._utils",
        )
        yield
