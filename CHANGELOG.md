# Changelog

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
