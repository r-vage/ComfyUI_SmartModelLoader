# ComfyUI Smart Model Loader

Version 1.0.1 provides a complete diffusion pipeline: secure model loading,
text conditioning, pipe inspection, sampling, and the verified Download
Manager. Install this repository in `ComfyUI/custom_nodes` and restart ComfyUI.
ComfyUI Eclipse is optional.

The node IDs remain unchanged, including their `[Eclipse]` suffixes, so saved
workflows resolve without node replacement:

- Smart Model Loader
- Model Loader
- Model Loader Pipe
- CLIP Loader
- VAE Loader
- VAE Loader Video+Audio
- CLIP Text Encode
- CLIP Text Encode (Advanced)
- Conditioning Zero Out
- IO Checkpoint Loader
- Eclipse KSampler (Pipe)

The pack includes Nunchaku and GGUF adapters, loader templates, integrity
metadata, CivitAI acquisition, and the CivitAI/Hugging Face Download Manager.
Its HTTP surface is `/smart-model-loader/...`, with Download Manager routes at
`/smart-model-loader/download-manager/...`.

Settings appear under **Smart Model Loader → General** and use the stable
`SmartModelLoader.*` IDs. This pack exclusively owns its log level, slider
preference, legacy-format policy, download retries, CivitAI key, Hugging Face
token, `/smart-model-loader/config/...` endpoints, and private `config.json`.
These values are independent from the **Eclipse** and **Smart LM Loader**
settings categories regardless of installation or extension load order.

On first startup, the pack copies missing templates, relevant settings, and an
existing Eclipse Download Manager queue into its own storage. Originals,
partial model downloads, and lock files are not moved or deleted. Active queue
states are recovered by the queue's existing restart contract. Its atomic
migration marker records only the names—not values—of Eclipse config keys that
were examined, allowing Eclipse to remove extracted loader fields only after
the destination has had a chance to preserve or migrate them.

Guides:

- [Pipeline nodes](Readme/Pipeline_Nodes.md)
- [Smart Model Loader](Readme/Smart_Loaders.md)
- [Focused loaders](Readme/Checkpoint_Loaders.md)
- [Download Manager](Readme/Download_Manager.md)
- [Security model](Readme/Model_Loader_Security.md)

The unchanged `PIPE` dictionary can also be used with optional Eclipse nodes.
Context Image, Generation Data, generic channel pipes, Concat Pipe Multi,
Smart Sampler Settings, Save Images, Kargim, and Conditioning Passer remain
Eclipse integrations and are not required by this pack.

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
