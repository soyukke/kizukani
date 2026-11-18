# Benchmark

Measures kizukani and other Apple Silicon engines running Qwen3.8-27B on the same prompts.

| Engine name | What runs |
|---|---|
| `kizukani-speed`, `kizukani-quality` | kizukani with the YASAKANI models and speculative decoding |
| `mlx-4bit` | mlx-lm 0.32.2 with `mlx-community/Qwen3.8-27B-4bit`, no speculation |
| `mlx-4bit-mtp` | mlx-vlm 0.8.0 with the same model and `mlx-community/Qwen3.8-27B-MTP-4bit` |
| `omlx-4bit-dflash2` | oMLX 0.8.0 with the same model and `z-lab/Qwen3.8-27B-DFlash2` |
| `llama.cpp-q4` | llama-server on Metal with `unsloth/Qwen3.8-27B-GGUF` `UD-Q4_K_M` |
| `mackani-speed` | Mackani 0.1.0 with the YASAKANI fastest model |

The engines use different quantizations and model sizes, so these numbers compare speed only.

## Setup

Build kizukani first, then place the models under `bench/models` (or point `BENCH_MODELS` elsewhere) as `mlx-4bit/`, `mlx-mtp-4bit/`, `dflash2/` and `gguf/`.

```sh
bench/setup.sh
```

`llama-server`, `uv` and `nix` must be on `PATH`.

## Run

```sh
python3 bench/preflight.py
python3 bench/run.py
```

`preflight.py` lists the apps that are using the CPU or GPU and never stops anything. `run.py` refuses to measure unless the Mac is on AC power in High Power mode with little other load, and unless plain MLX reaches 25 tok/s on a calibration prompt.

To start the run later, `python3 bench/run.py --wait-hours 12` keeps checking and begins once the Mac has stayed idle and passes the calibration.

`python3 bench/run.py --force` measures immediately without those checks, and records the machine state with the results.

Each engine answers six prompts (prose, code and thinking, at about 30 and 2,000 tokens of input) for 256 tokens per prompt, in two rounds. A warm-up prompt is discarded at the start of each engine's round. Results are written to `bench/results`.
