from comfy_api.latest import io  # type: ignore

from ..core import CATEGORY
from ..core.minimax_music3 import parse_song_json


class RvCond_TextEncodeMiniMaxMusic3(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Text Encode MiniMax Music 3 [Smart Model Loader]",
            display_name="Text Encode MiniMax Music 3",
            category=CATEGORY.MAIN.value + CATEGORY.CONDITIONING.value,
            description="Encode caption/lyrics JSON using ComfyUI's native MiniMax Music 3 encoder.",
            inputs=[
                io.Clip.Input("clip"),
                io.String.Input("song_json", multiline=True, dynamic_prompts=False),
                io.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff, control_after_generate=True),
                io.Float.Input(
                    "max_duration", default=120.0, min=0.04, max=360.0, step=0.04,
                    tooltip="Maximum duration in seconds; the model can end the song earlier.",
                ),
                io.Float.Input("cfg_scale", default=1.5, min=0.0, max=100.0, step=0.1, round=0.01, advanced=True),
                io.Int.Input("top_k", default=50, min=1, max=16384, advanced=True),
            ],
            outputs=[io.Conditioning.Output(), io.Float.Output(display_name="seconds")],
        )

    @classmethod
    def execute(cls, clip, song_json, seed, max_duration, cfg_scale, top_k):  # noqa: PLR0913, PLR0917
        song = parse_song_json(song_json)
        try:
            from comfy_extras.nodes_minimax_music import MiniMaxMusic3TextEncode  # noqa: PLC0415
        except ImportError as error:
            raise RuntimeError(
                "MiniMax Music 3 encoding requires ComfyUI with MiniMaxMusic3TextEncode support. Update ComfyUI.",
            ) from error
        return MiniMaxMusic3TextEncode.execute(
            clip=clip, caption=song["caption"], lyrics=song["lyrics"], seed=seed,
            max_duration=max_duration, cfg_scale=cfg_scale, top_k=top_k,
        )
