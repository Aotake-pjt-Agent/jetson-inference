# Repository Guidelines

## Project Structure & Module Organization
Inference backends live in `c/` (`*Net.cpp/.cu` and helpers). Python bindings, Dash UI, and notebooks are under `python/`, while C++ samples mirror them in `examples/`. The WebRTC pipeline sits in `jetson-webrtc-detection/`. Supporting assets are grouped in `docker/`, `tools/`, `docs/`, and `data/`. Generated builds belong under `build/aarch64/{bin,lib,include}` and must stay untracked.

## Build, Test, and Development Commands
Configure locally with:
```bash
mkdir -p build && cd build
cmake .. && make -j$(nproc)
sudo make install && sudo ldconfig
```
`cmake` triggers `CMakePreBuild.sh` to fetch dependencies and reference models. Re-run `./build/install-pytorch.sh` when enabling transfer-learning. Launch the WebRTC server through `./run_webrtc_detection.sh --camera /dev/video0 --network ssd-mobilenet-v2`; add spreadsheet logging via `--sheet-credentials service.json --sheet-id <ID>`. Container workflows use `docker/run.sh`.

## Coding Style & Naming Conventions
`.editorconfig` enforces tabs (size 5) for CUDA/C++. Follow existing brace placement and PascalCase classes with camelCase methods; reuse `*Net`/`tensor*` naming for shared utilities. Python code uses 4-space indentation, `snake_case` functions, and uppercase constants. CLI output should remain bilingual or icon-free unless matching current UX.

## Testing Guidelines
Validate network accuracy with `python3 tools/test-models.py --module=<name>` and document any regenerated fixtures (`--generate`). Dash cards can be smoke-tested using `pytest python/www/dash/layout/test_card.py`. When touching camera or WebRTC code, note the peripherals and network services exercised, and keep build artifacts under `build/` rather than committed paths.

## Commit & Pull Request Guidelines
Git history favors concise Japanese subjects (e.g., “WebRTC検知サーバーの実装…”). PRs should outline behaviour changes, commands executed, and linked issues. Attach screenshots or logs for streaming/UI updates, highlight required model downloads, and avoid committing large binaries. Flag breaking API changes early and supply migration notes for shared headers or Python bindings.

## Model Assets & Configuration Tips
Auto-downloaded networks land in `build/aarch64/bin/networks`; never check them in. Register new models inside `tools/download-models.sh` and document activation flags. Prefer environment/config flags (see `run_webrtc_detection.sh`) over hard-coded credentials, and keep secrets or service-account JSON outside version control while referencing them through paths or env vars.
