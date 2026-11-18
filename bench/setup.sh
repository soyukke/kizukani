#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
(cd envs/mlx && uv sync --python 3.12)
(cd envs/omlx && uv sync --python 3.12)
mkdir -p .work
nix shell nixpkgs/nixpkgs-unstable#rustc nixpkgs/nixpkgs-unstable#cargo -c cargo build --release --manifest-path drivers/mackani/Cargo.toml --target-dir .work/mackani-target
cp .work/mackani-target/release/mackani-bench-driver .work/mackani-driver
envs/mlx/.venv/bin/python prompts/build.py ../models/qwen38-27b-speed
