# Pipeline Nodes

Smart Model Loader includes the complete loader → conditioning → sampling path.
All published node IDs retain their historical `[Eclipse]` suffix so existing
workflows save and reload without replacement. The nodes appear under the
top-level `Smart Model Loader` menu.

## Text conditioning

`CLIP Text Encode [Eclipse]` accepts a CLIP model and a connected text string,
then returns scheduled ComfyUI conditioning. A missing or invalid CLIP raises the
same explicit checkpoint/encoder error used by existing workflows.

`CLIP Text Encode (Advanced) [Eclipse]` adds a global multiplier plus Krea2
multi-layer rebalancing. Choose `balanced`, `detail`, `subtle`, `uniform`, or
`custom`; the custom preset accepts comma- or semicolon-separated weights.
`renormalize` preserves the original RMS after layer weighting, while
`krea2_only_multiplier` leaves non-Krea2 conditioning unscaled. Non-Krea2 models
skip layer rebalancing and retain the documented multiplier behavior.

`Conditioning Zero Out [Eclipse]` clears conditioning tensors and pooled output.
Set `max_tokens` for explicit truncation, or connect a model and leave it at zero
to select the known architecture's base token length automatically. Unknown or
absent models keep the original token length. Tensor dtype/device and input
metadata are preserved without mutating the input conditioning.

## Pipe extraction and sampling

`IO Checkpoint Loader [Eclipse]` merges optional direct values over an input
`PIPE`, returns a new pipe, and exposes every checkpoint, latent, sampler,
dimension, name, and seed field in stable socket order. Missing values remain
`None`. When dimensions are absent, a latent supplies width and height using its
spatial downscale ratio (8 by default).

`Eclipse KSampler (Pipe) [Eclipse]` consumes the model and VAE from a `PIPE`,
plus positive and negative conditioning. A directly connected image is
VAE-encoded in preference to a latent; otherwise direct values fall back to pipe
values. `allow_overwrite` lets pipe sampler settings take priority over widgets.
Seeds `-1`, `-2`, and `-3` provide random, increment, and decrement queue-time
behavior. The node supports standard or tiled VAE encode/decode and can show or
hide both live and final previews. Its output is a copied pipe containing the
sampled latent, decoded image, dimensions, conditioning, and resolved settings.

## Optional Eclipse integrations

ComfyUI Eclipse is not required. If installed, its Context Image, Generation
Data, generic channel pipes, Concat Pipe Multi, Smart Sampler Settings, Save
Images, Kargim, and Conditioning Passer nodes can consume or enrich the same
unchanged `PIPE` contract.
