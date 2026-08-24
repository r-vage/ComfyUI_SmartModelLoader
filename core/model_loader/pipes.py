# Stable pipe construction shared by all diffusion model loaders.


class _OmitType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "OMIT"

    def __bool__(self) -> bool:
        return False


OMIT = _OmitType()


def build_pipe(**kwargs) -> dict:
    return {key: value for key, value in kwargs.items() if value is not OMIT}


def build_smart_sampler_fields(
    *,
    enabled: bool,
    model_type: str,
    clip_type: str,
    sampler_name: str,
    scheduler: str,
    steps: int,
    cfg: float,
    denoise: float,
    flux_guidance: float,
) -> dict:
    supports_flux_guidance = model_type == "Nunchaku Flux" or (
        model_type in {"UNet Model", "GGUF Model"}
        and clip_type in {"flux", "flux2"}
    )
    return build_pipe(
        configure_sampler=enabled,
        sampler_name=sampler_name if enabled else OMIT,
        scheduler=scheduler if enabled else OMIT,
        steps=steps if enabled else OMIT,
        cfg=cfg if enabled else OMIT,
        denoise=denoise if enabled else OMIT,
        flux_guidance=(flux_guidance if enabled and supports_flux_guidance else OMIT),
        _allow_overwrite=False if enabled else OMIT,
    )
