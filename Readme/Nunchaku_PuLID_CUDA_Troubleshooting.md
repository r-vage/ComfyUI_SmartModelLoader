# Nunchaku PuLID CUDA Troubleshooting

Use this guide when Nunchaku PuLID fails with
`CUDNN_STATUS_SUBLIBRARY_VERSION_MISMATCH`, when ONNX Runtime reports multiple
packages in the same location, or when ordinary PyTorch CUDA convolutions fail
after a dependency update.

## What the error means

CUDA 12.x and cuDNN 9.x are compatible with current ONNX Runtime GPU builds. The
error means the running process loaded cuDNN components from different releases
or from an installation whose files no longer match its package metadata. It is
not, by itself, evidence that cuDNN 9 is too old.

`onnxruntime` and `onnxruntime-gpu` are separate Python distributions that install
the same `onnxruntime` module. They must not coexist in one environment. This is
easy to trigger because InsightFace declares the CPU distribution by name even
when the GPU distribution provides the runtime module.

Smart Model Loader does not pin either distribution in its main
`requirements.txt`: a normal requirements file cannot express that installing
one must uninstall the other, cannot choose a GPU from platform markers, and
cannot repair binary files that pip already considers satisfied.

## Before repairing the environment

Stop ComfyUI completely. Identify the Python executable used by ComfyUI from its
startup log, then save the current package state. This example uses the Eclipse
development environment path; replace it for other installations.

```bash
COMFY_PYTHON=/mnt/data/AI/comfy_env/bin/python
"$COMFY_PYTHON" -m pip freeze --all > comfy-env-before-onnx-repair.txt
"$COMFY_PYTHON" -m pip show onnxruntime onnxruntime-gpu nvidia-cudnn-cu12 nvidia-cublas-cu12 torch
```

Check the NVIDIA versions required by the installed PyTorch build before copying
any pins from another machine:

```bash
"$COMFY_PYTHON" - <<'PY'
from importlib.metadata import requires

for requirement in requires("torch") or ():
    if "nvidia-cudnn" in requirement or "nvidia-cublas" in requirement:
        print(requirement)
PY
```

## Validated Linux repair

The following versions were validated together on Linux with Python 3.12,
PyTorch `2.9.1+cu128`, and Nunchaku `1.2.1+cu12.8torch2.9`:

| Component | Validated version |
| --- | --- |
| ONNX Runtime GPU | `1.21.1` |
| NVIDIA cuDNN CUDA 12 | `9.10.2.21` |
| NVIDIA cuBLAS CUDA 12 | `12.8.4.1` |

Do not reuse these cuDNN/cuBLAS pins when PyTorch reports different requirements.
With ComfyUI stopped, remove both ONNX distributions and reinstall one GPU
runtime plus PyTorch's exact CUDA libraries:

```bash
"$COMFY_PYTHON" -m pip uninstall -y \
  onnxruntime onnxruntime-gpu nvidia-cudnn-cu12 nvidia-cublas-cu12

"$COMFY_PYTHON" -m pip install --no-cache-dir --force-reinstall --no-deps \
  nvidia-cublas-cu12==12.8.4.1 \
  nvidia-cudnn-cu12==9.10.2.21 \
  onnxruntime-gpu==1.21.1
```

`--no-deps` prevents this focused repair from replacing unrelated packages. The
three required binary distributions are installed explicitly.

InsightFace may make `pip check` report that the distribution named
`onnxruntime` is absent. Do not reinstall the CPU wheel merely to silence that
metadata warning: doing so recreates the duplicate module installation. Confirm
runtime behavior instead.

## Verify before restarting ComfyUI

This check must show `CUDAExecutionProvider`, report the cuDNN version required by
PyTorch, and complete the convolution without an exception:

```bash
"$COMFY_PYTHON" - <<'PY'
import onnxruntime as ort
import torch

print("torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("cuDNN:", torch.backends.cudnn.version())
print("ONNX Runtime:", ort.__version__)
print("providers:", ort.get_available_providers())

image = torch.randn(1, 3, 64, 64, device="cuda")
convolution = torch.nn.Conv2d(3, 8, 3).cuda()
print("convolution:", tuple(convolution(image).shape))
PY
```

Restart ComfyUI and queue the PuLID workflow with the loader's **CUDA** provider.
If CUDA still fails, use **CPU** as the face-preprocessing compatibility path and
inspect ONNX Runtime's official CUDA/cuDNN compatibility matrix before selecting
different package versions:

<https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html>

## Warnings after a successful generation

Smart Model Loader suppresses known dependency deprecations at their
integration boundary and replaces Nunchaku's deprecated list-based tensor
indexing with equivalent tuple indexing. It does not modify the installed
package. Restart ComfyUI after updating the node pack so these compatibility
changes are active.

The compatibility layer also accepts the Qwen transformer exports used by both
the stable Nunchaku package and the `1.3.0.dev20260306` nightly. The nightly moves
that class out of the legacy `nunchaku.models.qwenimage` module; without this
adapter, Nunchaku Qwen loading appears unavailable even though Flux still works.

The following remaining messages do not indicate a failed PuLID generation:

- `Rebalancing is only supported for Krea2 models` means a Krea2-only rebalance
  preset reached a non-Krea model. Use the global multiplier alone for Flux.
- `No selection confirmed` followed by `Processing interrupted` is the expected
  Image Selector pause when no image has been confirmed; it is unrelated to
  PuLID or CUDA.

With **CPU** selected for `insight_face_provider`, the face-analysis ONNX models
run on the CPU while the PuLID and Flux torch modules can still use CUDA. The log
line `provider=CPU, face cuDNN disabled` confirms that compatibility path.
