# Changelog

Notable changes to the AI Command Interface are documented here.
This file follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
principles and [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-12

### Added

- Connected dashboard chat to a local llama.cpp server using Vulkan on Windows.
- Added discovery of installed GGUF models and live loaded-model status.
- Added model switching from the chat dropdown and model cards. The backend
  validates the server process, restarts it for the selected model, confirms
  the new model is loaded, and attempts to restore the prior model on failure.
- Added Windows GPU load and dedicated VRAM telemetry, plus live CPU and
  system RAM readings in the Host Monitor.
- Added explicit web-research mode using SearXNG, with source links in
  responses. SearXNG must be installed and configured before searches work.
- Added Windows setup and launch scripts, including an ONNX Runtime DirectML
  smoke test.
- Documented the Windows test environment, model setup, API, architecture,
  GPU plans, and Linux/Proxmox deployment considerations.
- Added focused backend tests for model switching and web research.

### Changed

- Updated the Models page and AI Interface dropdown to reflect the GGUF files
  installed on the test machine.
- Updated project documentation and the README to describe the current
  Windows test setup and distinguish working features from planned deployment
  work.

### Fixed

- Replaced simulated GPU load, VRAM, and Host Monitor RAM values with live
  readings; unavailable GPU telemetry is reported as unavailable rather than
  presented as a simulated measurement.
- Removed stale setup instructions and unresolved merge-conflict markers from
  the README.

### Model test assets

- Qwen2.5 1.5B Instruct Q4_K_M — used for dashboard chat testing.
- Stories15M Q4_0 — installed smoke-test model.
- Qwen3-8B Q4_K_M and Qwen2.5-Coder-7B-Instruct Q4_K_M — each passed a short
  Vulkan inference test with GPU layer offload on the RX 6800 XT.

### Known limitations

- SearXNG is not yet installed or configured.
- Linux/Proxmox GPU telemetry and production GPU runtime support remain future
  work; Windows DirectML testing does not establish Linux deployment support.
- Vision and image-generation integrations are not yet connected to production
  models. VM, game-server, and network-service panels are planning views, and
  Discord bot status/logs remain placeholders.

## [0.1.0] — Initial Commit

### Added

- Initial project structure, FastAPI backend, dashboard UI, and Discord bot
  connection logic.
- Placeholder endpoints and GPU/LLM stubs for development.
- Initial documentation, dashboard navigation and panels, model cards,
  system-monitor bars, chat layout, backend status indicator, and theme
  swatches.

