from comfy_api.latest import io  # type: ignore

from ..core import CATEGORY
from ..core.model_loader.qwen_scheduler import qwen_image21_dimensions, qwen_image21_sigmas


class RvSampler_QwenImage21Scheduler(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Qwen Image 2.1 Scheduler [Smart Model Loader]",
            display_name="Qwen Image 2.1 Scheduler",
            category=CATEGORY.MAIN.value + CATEGORY.SAMPLER.value,
            description=(
                "Build Qwen Image 2.1 SIGMAS with resolution-dependent shifting and terminal stretching. "
                "Use the SIGMAS output with SamplerCustomAdvanced, directly or through IO Checkpoint Loader. "
                "Steps and denoise here determine the schedule and replace those values in the output pipe."
            ),
            inputs=[
                io.Int.Input("steps", default=40, min=1, max=10000,
                             tooltip="Sampling steps for this schedule; also written to the output pipe."),
                io.Float.Input("denoise", default=1.0, min=0.0, max=1.0, step=0.01,
                               tooltip="Keep the final steps of a longer schedule for img2img. 0 disables sampling."),
                io.Int.Input("width", default=1024, min=16, max=32768, step=16,
                             tooltip="Fallback pixel width. A connected target latent, pipe latent or pipe width wins."),
                io.Int.Input("height", default=1024, min=16, max=32768, step=16,
                             tooltip="Fallback pixel height. A connected target latent, pipe latent or pipe height wins."),
                io.Int.Input("base_image_seq_len", default=256, min=1, max=4194304),
                io.Float.Input("base_shift", default=0.5, min=0.0, max=100.0, step=0.01),
                io.Int.Input("max_image_seq_len", default=8192, min=2, max=4194304,
                             tooltip="Upper shift anchor; larger images extrapolate beyond max_shift."),
                io.Float.Input("max_shift", default=0.9, min=0.0, max=100.0, step=0.01),
                io.Boolean.Input("use_dynamic_shifting", default=True,
                                 tooltip="Compute the shift from target image tokens and both shift anchors."),
                io.Combo.Input("time_shift_type", options=["exponential", "linear"], default="exponential",
                               tooltip="Dynamic shift transform. Qwen Image 2.1 uses exponential."),
                io.Float.Input("shift_terminal", default=0.02, min=0.0, max=0.999, step=0.001,
                               tooltip="Last positive sigma before the final zero. 0 disables terminal stretching."),
                io.Int.Input("num_train_timesteps", default=1000, min=1, max=1000000,
                             tooltip="Training timestep units. They cancel in Qwen's normalized inference SIGMAS."),
                io.Float.Input("shift", default=1.0, min=0.01, max=100.0, step=0.01,
                               tooltip="Fixed multiplicative shift, used only when dynamic shifting is disabled."),
                io.Custom("PIPE").Input("pipe", optional=True,
                                        tooltip="Optional loader pipe. Adds SIGMAS while retaining its contents."),
                io.Latent.Input("latent", optional=True,
                                tooltip="Actual Qwen 2.1 target latent, including from the text encoder. Overrides pipe latent."),
            ],
            outputs=[io.Custom("PIPE").Output("pipe"), io.Sigmas.Output("sigmas")],
        )

    @classmethod
    def execute(  # noqa: PLR0913, PLR0917
        cls, steps=40, denoise=1.0, width=1024, height=1024,
        base_image_seq_len=256, base_shift=0.5, max_image_seq_len=8192, max_shift=0.9,
        use_dynamic_shifting=True, time_shift_type="exponential", shift_terminal=0.02,
        num_train_timesteps=1000, shift=1.0, pipe=None, latent=None,
    ) -> io.NodeOutput:
        if pipe is not None and not isinstance(pipe, dict):
            raise ValueError("Qwen Image 2.1 Scheduler pipe must be a PIPE dictionary.")
        pipe_out = {} if pipe is None else pipe.copy()
        latent, width, height = qwen_image21_dimensions(pipe_out, latent, width, height)
        sigmas = qwen_image21_sigmas(
            image_seq_len=(width // 16) * (height // 16), steps=steps, denoise=denoise,
            base_image_seq_len=base_image_seq_len, base_shift=base_shift,
            max_image_seq_len=max_image_seq_len, max_shift=max_shift,
            use_dynamic_shifting=use_dynamic_shifting, time_shift_type=time_shift_type,
            shift_terminal=shift_terminal, num_train_timesteps=num_train_timesteps, shift=shift,
        )
        pipe_out.update(sigmas=sigmas, steps=steps, denoise=denoise, width=width, height=height)
        if latent is not None:
            pipe_out["latent"] = latent
            pipe_out["batch_size"] = latent["samples"].shape[0]
        return io.NodeOutput(pipe_out, sigmas)
