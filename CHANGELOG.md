# Changelog

## 2026-08-24

### Version: 1.0.5

- **Feat**
  - Add a 0.0–1.0 `denoise` control below `cfg` in the Smart Model Loader sampler chip, persist it in templates, include it in the emitted PIPE, and append it to IO Checkpoint Loader inputs and outputs.
  - Automatically detect and migrate previous compact and seed-button positional Smart Model Loader layouts before node configuration, preserving `flux_guidance` and every later widget value when older workflows load.

- **Fix**
  - Let ComfyUI report one field-specific prompt-validation error for a missing Smart Model Loader primary model instead of repeating one node-wide error for every widget.
  - Preserve the Pipe sampler's manually resized height when tiled-decode controls change while previews are enabled so the preview absorbs row changes, while retaining automatic resizing when preview is `None`.

**Changed files:**
- `Readme/Smart_Loaders.md`
- `core/model_loader/pipes.py`
- `core/model_loader/smart.py`
- `js/eclipse-sampler-tiled-decode.js`
- `js/eclipse-smart-model-loader.js`
- `js/smart-model-loader-widget-migration.js` (new)
- `py/RvLoader_SmartModelLoader.py`
- `py/RvPipe_IO_CheckpointLoader.py`
- `pyproject.toml`
- `tests/test_pipeline_nodes.py`
- `tools/pipeline-frontend-harness.mjs`

### Version: 1.0.4

- **Fix**
  - Bundle the missing `Krea2_GPT` Smart Model Loader template used by iGEN Simple, including verified CivitAI acquisition metadata for its primary diffusion model.
  - Isolate bundled GGUF/Nunchaku mutable defaults, correct GGUF tokenizer model-type assignment, bind replacement callbacks to their intended blocks, and preserve causal exception chains.
  - Ignore stale hidden integrity modes during execution and expose verified CivitAI re-download recovery when a present model file has a hash mismatch.
  - Update the copied pipe sampler's tiled-decode controls immediately in classic and Nodes 2.0 views when `tiled_decode` changes.

- **Refactor**
  - Modernize tracked first-party and bundled Python imports, typing syntax, collections, dictionary iteration, control flow, and formatting without changing node IDs, schemas, routes, or loader contracts.

- **Chore**
  - Enable Ruff's complete rule set for tracked Python with documented, scoped exceptions for ComfyUI callbacks, serialized identifiers, hardware orchestration, and maintained bundled integrations.

**Changed files:**
- `.defaults/.manifest.json`
- `.defaults/templates/Krea2_GPT.json.example` (new)
- `pyproject.toml`
- `core/common.py`
- `core/config_store.py`
- `core/download_manager/endpoints.py`
- `core/download_manager/manager.py`
- `core/download_manager/providers.py`
- `core/gguf_wrapper.py`
- `core/json_store.py`
- `core/keys.py`
- `core/logger.py`
- `core/migration.py`
- `core/model_loader/acquisition.py`
- `core/model_loader/endpoints.py`
- `core/model_loader/integrity.py`
- `core/model_loader/lifecycle.py`
- `core/model_loader/smart.py`
- `core/model_loader/templates.py`
- `core/model_loader/validation.py`
- `core/model_loader_common.py`
- `core/network_security.py`
- `core/nunchaku_wrapper.py`
- `core/server_endpoints.py`
- `extern/gguf/__init__.py`
- `extern/gguf/dequant.py`
- `extern/gguf/loader.py`
- `extern/gguf/nodes.py`
- `extern/gguf/ops.py`
- `extern/gguf/tools/convert.py`
- `extern/nunchaku/__init__.py`
- `extern/nunchaku/mixins/model.py`
- `extern/nunchaku/model_base/qwenimage.py`
- `extern/nunchaku/model_configs/qwenimage.py`
- `extern/nunchaku/model_configs/zimage.py`
- `extern/nunchaku/model_patcher/common.py`
- `extern/nunchaku/model_patcher/zimage.py`
- `extern/nunchaku/models/qwenimage.py`
- `extern/nunchaku/models/zimage.py`
- `extern/nunchaku/wrappers/flux.py`
- `js/eclipse-smart-model-loader.js`
- `js/eclipse-sampler-tiled-decode.js`
- `js/smart-model-loader-integrity-flow.js` (new)
- `py/RvCond_CLIPTextEncode.py`
- `py/RvCond_CLIPTextEncodeAdvanced.py`
- `py/RvCond_ConditioningZeroOut.py`
- `py/RvLoader_ClipLoader.py`
- `py/RvLoader_SmartModelLoader.py`
- `py/RvLoader_VaeLoaderVideoAudio.py`
- `py/RvPipe_IO_CheckpointLoader.py`
- `py/RvSampler_KSamplerPipe.py`
- `tests/test_integrity_flow.py` (new)
- `tools/pipeline-frontend-harness.mjs`
- `workflows/iGEN_Simple.json` (new)

## 2026-08-22

### Version: 1.0.3

- **Fix**
  - Omit hidden `flux_guidance` defaults from Smart Model Loader pipes for Krea2 and other non-Flux model/CLIP combinations while retaining it for supported Flux and Flux2 loaders.

**Changed files:**
- `pyproject.toml`
- `core/model_loader/pipes.py`
- `core/model_loader/smart.py`
- `Readme/Smart_Loaders.md`
- `tests/test_pipeline_nodes.py`

### Version: 1.0.2

- **Feat**
  - Add a persisted color picker for loader chip bars and selected chips, with derived hover, border, and contrast colors.
  - Match loader combo-chip popup widths to their rendered trigger bars without stretching or shrinking individual chips.

- **Fix**
  - Set the Download Manager dialog background to `#3a3a3a`.

**Changed files:**
- `pyproject.toml`
- `.defaults/config.json.example`
- `.defaults/.manifest.json`
- `core/config_store.py`
- `core/server_endpoints.py`
- `js/eclipse-combo-chip.js`
- `js/smart-model-loader-download-manager.js`
- `js/smart-model-loader-settings.js`
- `README.md`
- `Readme/Model_Loader_Security.md`
- `tests/test_config_store.py` (new)
- `tools/chip-color-harness.mjs` (new)

## 2026-08-19

### Version: 1.0.1

- **Feat**
  - Add workflow-compatible basic and Advanced CLIP encoding, model-aware Conditioning Zero Out, checkpoint pipe IO, and pipe sampling so the standalone pack supplies a complete loader-to-image pipeline.
  - Add standalone queue-time special-seed controls plus tiled-decode and live/final preview behavior for `Eclipse KSampler (Pipe) [Eclipse]`.
  - Place all eleven nodes under their own `Smart Model Loader` top-level menu while retaining the historical workflow node IDs.

- **Refactor**
  - Take exclusive runtime and frontend ownership of the five transferred node IDs without cross-pack imports, endpoint probes, configuration sharing, or workflow migration.

- **Docs**
  - Document the complete pipeline, optional Eclipse integrations, independent installation, correct template path, support links, and Smart Model Loader branding.
  - Add a Nodes 2.0 visual walkthrough with annotated loader modes, feature chips, template loading and missing-model recovery, conditioning, pipe sampling, menu discovery, and Download Manager views.

**Changed files:**
- `py/RvCond_CLIPTextEncode.py` (new)
- `py/RvCond_CLIPTextEncodeAdvanced.py` (new)
- `py/RvCond_ConditioningZeroOut.py` (new)
- `py/RvPipe_IO_CheckpointLoader.py` (new)
- `py/RvSampler_KSamplerPipe.py` (new)
- `js/eclipse-clip-text-encode-advanced.js` (new)
- `js/eclipse-seed.js` (new)
- `js/eclipse-sampler-tiled-decode.js` (new)
- `tests/test_pipeline_nodes.py` (new)
- `tools/pipeline-frontend-harness.mjs` (new)
- `README.md`
- `Readme/Pipeline_Nodes.md` (new)
- `Readme/Smart_Loaders.md`
- `Readme/Checkpoint_Loaders.md`
- `Readme/Model_Loader_Security.md`
- `Readme/assets/*.png` (new)
- `pyproject.toml`
- `core/keys.py`

## 2026-08-17

### Version: 1.0.0

- **Feat (New)**
  - Extract the six workflow-compatible Eclipse diffusion loaders into a standalone ComfyUI pack.
  - Include the verified CivitAI/Hugging Face Download Manager with persistent queue recovery and portable bundle compatibility.
  - Add copy-only migration for Eclipse templates, relevant configuration values, and queue state.

- **Fix**
  - Guard every backend-writing setting against ComfyUI's automatic first change callback while hydrating defaults and credential masks only from the pack's redacted config endpoint.

- **Refactor**
  - Give `Smart Model Loader → General` exclusive ownership of stable `SmartModelLoader.*` settings, endpoints, credentials, log level, sliders, retry policy, and legacy-format policy.
  - Upgrade migration markers atomically with value-free examined-key confirmation while preserving non-default destination values on conflicts.

- **Docs**
  - Document independent Eclipse, Smart Model Loader, and Smart LM Loader settings and configuration ownership.

- **Security**
  - Retain immutable provider identity, bounded same-origin mutations, registered-root containment, resumable partial validation, integrity sidecars, and atomic promotion.

- **Breaking**
  - Replace Eclipse-owned HTTP routes and Download Manager identifiers with the `/smart-model-loader` namespace; API clients must migrate.

**Changed files:**
- `core/migration.py`
- `js/smart-model-loader-settings.js`
- `README.md`
