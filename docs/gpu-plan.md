# GPU Integration Plan

## Hardware

- AMD RX 6800 XT (currently in main PC)
- Dedicated server planned for ROCm

## Windows Support

- llama.cpp (HIP/DirectML)
- ONNX Runtime + DirectML
- Stable Diffusion (DirectML)

## Linux Support (Server)

- ROCm
- vLLM GPU mode
- Triton kernels

## Strategy

1. Develop using stubs
2. Add llama.cpp for Windows GPU inference
3. Migrate backend to Linux server
4. Enable ROCm + vLLM
5. Connect dashboard to real inference
