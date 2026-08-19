# Changelog

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
