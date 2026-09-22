from comfy_api.latest import io  # type: ignore

from ..core import CATEGORY


class RvCond_TextEncodeQwenImage21(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Text Encode Qwen Image 2.1 [Smart Model Loader]",
            display_name="Text Encode Qwen Image 2.1",
            category=CATEGORY.MAIN.value + CATEGORY.CONDITIONING.value,
            description="Encode Qwen Image 2.1 prompts and optional references using ComfyUI's native encoder.",
            inputs=[
                io.Clip.Input("clip"),
                io.Vae.Input("vae"),
                io.String.Input("positive", force_input=True),
                io.String.Input("negative", force_input=True),
                io.Int.Input(
                    "resolution", default=1024, min=0, max=4096, step=32,
                    tooltip="Resize references to about resolution squared pixels, preserving aspect ratio at multiples of 32. 0 keeps their own size, rounded to multiples of 32.",
                ),
                # Keep image_1 fixed: native autogrow's prefix lookup can confuse
                # image_1 with image_10..16 when restoring a saved workflow.
                io.Image.Input("image_1", optional=True),
                io.Autogrow.Input(
                    "images",
                    template=io.Autogrow.TemplateNames(
                        io.Image.Input("image", optional=True),
                        names=[f"image_{i}" for i in range(2, 17)],
                        # One spare plus the fixed image_1 gives two sockets.
                        min=0,
                    ),
                    optional=True,
                    tooltip="Optional references in socket order; use the first image of each input batch.",
                ),
            ],
            outputs=[
                io.Conditioning.Output(display_name="positive"),
                io.Conditioning.Output(display_name="negative"),
                io.Latent.Output(display_name="latent"),
            ],
        )

    @classmethod
    def execute(cls, clip, vae, positive, negative, resolution=1024, image_1=None, images=None):  # noqa: PLR0913, PLR0917
        try:
            from comfy_extras.nodes_qwen import TextEncodeQwenImage21  # noqa: PLC0415
        except ImportError as error:
            raise RuntimeError(
                "Qwen Image 2.1 encoding requires ComfyUI with TextEncodeQwenImage21 support. Update ComfyUI.",
            ) from error
        if image_1 is not None:
            images = {**(images or {}), "image_1": image_1}
        return TextEncodeQwenImage21.execute(
            clip=clip, vae=vae, prompt=positive, negative_prompt=negative,
            resolution=resolution, images=images,
        )
