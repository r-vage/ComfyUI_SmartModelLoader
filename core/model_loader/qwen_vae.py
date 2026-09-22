# Qwen Image 2.1 Diffusers weights use Wan 2.2 blocks with 2D convolutions.
# Conversion is deliberately restricted to the RGBA, 64-channel architecture.
from __future__ import annotations

import re

import torch


def _is_qwen21_diffusers(state_dict):
    # Independent structural and shape anchors tolerate a damaged anchor while
    # excluding ordinary Diffusers AutoencoderKL and Wan video VAEs.
    anchors = {
        "encoder.conv_in.weight": (96, 4, 3, 3),
        "decoder.conv_out.weight": (4, 144, 3, 3),
        "post_quant_conv.weight": (64, 64, 1, 1),
    }
    matches = sum(
        tuple(state_dict[key].shape) == shape
        for key, shape in anchors.items() if key in state_dict
    )
    return matches >= 2 and any(
        key.startswith(("encoder.down_blocks.4.", "decoder.up_blocks.4."))
        and key.endswith(".gamma") for key in state_dict
    )


def _native_key(key: str) -> str:
    key = re.sub(r"^quant_conv\.", "conv1.", key)
    key = re.sub(r"^post_quant_conv\.", "conv2.", key)
    key = re.sub(r"^(encoder|decoder)\.conv_in\.", r"\1.conv1.", key)
    key = re.sub(r"^(encoder|decoder)\.conv_out\.", r"\1.head.2.", key)
    key = re.sub(r"^(encoder|decoder)\.norm_out\.", r"\1.head.0.", key)
    key = key.replace(".mid_block.attentions.0.", ".middle.1.")
    for index, native_index in ((0, 0), (1, 2)):
        key = key.replace(f".mid_block.resnets.{index}.", f".middle.{native_index}.")
    for side, direction, count in (("encoder", "down", 2), ("decoder", "up", 3)):
        key = re.sub(
            rf"^{side}\.{direction}_blocks\.(\d+)\.resnets\.(\d+)\.",
            rf"{side}.{direction}samples.\1.{direction}samples.\2.", key,
        )
        key = re.sub(
            rf"^{side}\.{direction}_blocks\.(\d+)\.{direction}sampler\.",
            rf"{side}.{direction}samples.\1.{direction}samples.{count}.", key,
        )
    # Only residual blocks have these components; conv1 at the root stays intact.
    if re.match(r"^(encoder|decoder)\.(middle\.\d+|(?:down|up)samples\.\d+\.(?:down|up)samples\.\d+)\.", key):
        for source, target in (
            ("norm1", "residual.0"), ("conv1", "residual.2"),
            ("norm2", "residual.3"), ("conv2", "residual.6"),
            ("conv_shortcut", "shortcut"),
        ):
            key = key.replace(f".{source}.", f".{target}.")
    return key


def normalize_qwen_vae(state_dict):
    # Native and unrelated formats preserve identity and upstream handling.
    if not _is_qwen21_diffusers(state_dict):
        return state_dict

    from comfy.ldm.wan.vae2_2 import WanVAE  # type: ignore

    try:
        # Meta construction validates against the installed architecture without
        # allocating a second set of weights or consuming random-number state.
        with torch.device("meta"):
            model = WanVAE(
                dim=96, dec_dim=144, z_dim=64, dim_mult=[1, 2, 4, 8, 8],
                num_res_blocks=2, attn_scales=[],
                temperal_downsample=[False, True, True, True], dropout=0.0,
                image_channels=4, patch_size=1, temporal_kernel=1,
            )
        expected = {key: tuple(value.shape) for key, value in model.state_dict().items()}
    except TypeError as error:
        raise RuntimeError("Qwen Image 2.1 VAE support requires an updated ComfyUI.") from error

    converted = {}
    for key, value in state_dict.items():
        target = _native_key(key)
        if target not in expected or target in converted:
            raise ValueError(f"Malformed Qwen Image 2.1 VAE: unexpected or duplicate weight {key!r}.")
        shape = expected[target]
        if len(shape) == 5 and value.ndim == 4 and shape[2] == 1:
            value = value.unsqueeze(2)  # noqa: PLW2901
        if tuple(value.shape) != shape:
            raise ValueError(
                f"Malformed Qwen Image 2.1 VAE: {key!r} has shape {tuple(value.shape)}, expected {shape}.",
            )
        converted[target] = value
    missing = expected.keys() - converted.keys()
    if missing:
        raise ValueError(f"Malformed Qwen Image 2.1 VAE: missing weights {sorted(missing)}.")
    return converted
