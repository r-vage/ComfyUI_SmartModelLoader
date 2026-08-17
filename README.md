# ComfyUI Smart Model Loader

Version 1.0.0 is the standalone home of Eclipse's six diffusion loader nodes
and verified Download Manager. Install this directory beside
`comfyui_eclipse` in `ComfyUI/custom_nodes` and restart ComfyUI.

The node IDs remain unchanged, including their `[Eclipse]` suffixes, so saved
workflows resolve without node replacement:

- Smart Model Loader
- Model Loader
- Model Loader Pipe
- CLIP Loader
- VAE Loader
- VAE Loader Video+Audio

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

- [Smart Model Loader](Readme/Smart_Loaders.md)
- [Focused loaders](Readme/Checkpoint_Loaders.md)
- [Download Manager](Readme/Download_Manager.md)
- [Security model](Readme/Model_Loader_Security.md)

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
