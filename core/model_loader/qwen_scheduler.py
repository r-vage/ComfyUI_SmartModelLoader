"""Qwen Image 2.1 flow schedule, independent of model/encoder loading."""

import math

import torch


def qwen_image21_dimensions(pipe, latent, width: int, height: int) -> tuple:
    """Prefer the target latent, then pipe dimensions, then widget dimensions."""
    resolved = latent if latent is not None else pipe.get("latent")
    if resolved is not None:
        samples = resolved.get("samples") if isinstance(resolved, dict) else None
        if (
            not isinstance(samples, torch.Tensor)
            or samples.is_nested
            or samples.ndim not in (4, 5)
            or (samples.ndim == 5 and samples.shape[2] != 1)
            or min(samples.shape) < 1
        ):
            raise ValueError(
                "Qwen Image 2.1 Scheduler needs a 64-channel image latent or a compatible empty image latent.",
            )
        latent_height, latent_width = samples.shape[-2:]
        downscale = resolved.get("downscale_ratio_spacial")
        if samples.shape[1] != 64 or downscale not in (None, 16):
            # ComfyUI adapts zero-filled placeholders before sampling. Derive
            # that grid without allocating a converted latent or altering it.
            is_empty = samples.device.type != "meta" and torch.count_nonzero(samples).item() == 0
            if samples.shape[1] != 64 and not is_empty:
                raise ValueError(
                    "Qwen Image 2.1 Scheduler needs a 64-channel encoded latent; "
                    "latents with other channel counts must be zero-filled empty placeholders.",
                )
            if is_empty and downscale is not None:
                if (
                    not isinstance(downscale, (int, float)) or isinstance(downscale, bool)
                    or not math.isfinite(downscale) or downscale <= 0
                ):
                    raise ValueError("Empty latent downscale_ratio_spacial must be finite and greater than zero.")
                # Match comfy.sample.fix_empty_latent_channels, including round
                # for image dimensions that fall between Qwen latent pixels.
                ratio = downscale / 16
                latent_width = round(latent_width * ratio)
                latent_height = round(latent_height * ratio)
                if min(latent_width, latent_height) < 1:
                    raise ValueError("Empty latent dimensions are too small after Qwen's spatial conversion.")
        return resolved, latent_width * 16, latent_height * 16

    width = pipe.get("width") if pipe.get("width") is not None else width
    height = pipe.get("height") if pipe.get("height") is not None else height
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 16 for value in (width, height)):
        raise ValueError("Qwen Image 2.1 Scheduler width and height must be integers of at least 16 pixels.")
    return None, (width // 16) * 16, (height // 16) * 16


def qwen_image21_sigmas(
    *,
    image_seq_len: int,
    steps: int = 40,
    denoise: float = 1.0,
    base_image_seq_len: int = 256,
    base_shift: float = 0.5,
    max_image_seq_len: int = 8192,
    max_shift: float = 0.9,
    use_dynamic_shifting: bool = True,
    time_shift_type: str = "exponential",
    shift_terminal: float = 0.02,
    num_train_timesteps: int = 1000,
    shift: float = 1.0,
) -> torch.Tensor:
    """Return normalized SIGMAS, shifted and stretched before denoise slicing.

    Matches Qwen's explicit 1..1/steps inference grid with the Diffusers
    FlowMatchEulerDiscreteScheduler transforms. Training timestep units cancel
    when normalized; num_train_timesteps does not change this inference grid.
    No Diffusers runtime dependency or model sampling patch is needed.
    """
    integers = (image_seq_len, steps, base_image_seq_len, max_image_seq_len, num_train_timesteps)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in integers):
        raise ValueError("Sequence lengths, steps and num_train_timesteps must be positive integers.")
    if steps > 10000:
        raise ValueError("Qwen Image 2.1 Scheduler supports at most 10000 steps.")
    if not all(math.isfinite(value) for value in (base_shift, max_shift, shift, shift_terminal, denoise)):
        raise ValueError("Shifts, shift_terminal and denoise must be finite.")
    if not 0 <= denoise <= 1 or not 0 <= shift_terminal < 1:
        raise ValueError("denoise must be in [0, 1] and shift_terminal in [0, 1).")
    if time_shift_type not in {"exponential", "linear"}:
        raise ValueError("time_shift_type must be exponential or linear.")

    factor = shift
    if use_dynamic_shifting:
        if max_image_seq_len <= base_image_seq_len:
            raise ValueError("max_image_seq_len must be greater than base_image_seq_len.")
        mu = base_shift + (max_shift - base_shift) * (
            (image_seq_len - base_image_seq_len) / (max_image_seq_len - base_image_seq_len)
        )
        try:
            factor = math.exp(mu) if time_shift_type == "exponential" else mu
        except OverflowError as error:
            raise ValueError("The resolution and shift anchors produce an excessive exponential shift.") from error
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("The resulting shift factor must be finite and greater than zero.")
    if denoise == 0:
        return torch.empty(0, dtype=torch.float32)

    # Generate only the retained tail, avoiding huge allocations at low denoise.
    total_steps_float = steps / denoise
    if not math.isfinite(total_steps_float):
        raise ValueError("denoise is too small to construct a finite schedule.")
    total_steps = int(total_steps_float)
    timesteps = torch.arange(steps, 0, -1, dtype=torch.float64) * (num_train_timesteps / total_steps)
    sigmas = timesteps / num_train_timesteps
    sigmas = factor / (factor + (1 / sigmas - 1))

    # A one-step schedule is [1, 0]; there is no interval to stretch.
    if shift_terminal > 0 and total_steps > 1:
        last_gap = 1 - sigmas[-1]
        if last_gap <= 0:
            raise ValueError("The shift is too large to stretch a finite schedule; reduce the shift values.")
        sigmas = 1 - (1 - sigmas) * ((1 - shift_terminal) / last_gap)

    sigmas = torch.cat((sigmas, sigmas.new_zeros(1))).to(dtype=torch.float32)
    if not torch.isfinite(sigmas).all() or (sigmas[:-1] <= sigmas[1:]).any():
        raise ValueError("The settings do not produce a finite, strictly descending sigma schedule.")
    return sigmas
