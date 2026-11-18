# kizukani

An unofficial Apple Silicon engine for [YASAKANI](https://github.com/yasakani-dev/yasakani) model files, written in [Kizu](https://github.com/kizu-lang/kizu), including its GPU kernels.

[日本語](README.ja.md)

kizukani runs Qwen3.8-27B from the compressed `.yskn` files that the YASAKANI authors publish. It decodes on the GPU through Metal and uses the published draft model for speculative decoding.

The model files and the `.yskn` format are the YASAKANI authors' work, and [Mackani](https://github.com/TKY-27/Mackani) showed how to run them on a Mac. Thank you to the YASAKANI authors, to TKY-27, and to the Qwen team. kizukani is not affiliated with or endorsed by any of them.

## Requirements

- An Apple Silicon Mac. kizukani has been tested on a single Mac so far.
- About 13 GB of disk space for the fastest model folder, or 15 GB for the quality model folder.
- The Kizu compiler at commit `7f79ac81e1d62534690339cb044291d97d3ba21b`.
- The [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli) (`hf`) to download the model.

## Build

Build the Kizu compiler. Its repository lists what that needs.

```sh
git clone https://github.com/kizu-lang/kizu
cd kizu
git checkout 7f79ac81e1d62534690339cb044291d97d3ba21b
just stage1
export KIZU_SRC="$PWD"
```

Then build kizukani from this repository's root.

```sh
scripts/build
```

This writes `target/kernels.metal` and `target/kizukani`.

## Get the model

```sh
hf download yasakani-dev/Qwen3.8-27B-YASAKANI-speed --local-dir models/qwen38-27b-speed
```

To use the quality model, which stays closer to the original model, download it as well.

```sh
hf download yasakani-dev/Qwen3.8-27B-YASAKANI-quality --local-dir models/qwen38-27b-quality
```

## Chat

Run kizukani from the repository root, because it finds the model and kernels by relative path.

```sh
target/kizukani chat
```

Type a message and press Enter. Type `/exit` or send end of input (Ctrl-D) to quit.

| Option | Meaning |
|---|---|
| `--no-think` | Answer without writing out reasoning first |
| `--model NAME` | Choose `speed` (default) or `quality` |
| `--system TEXT` | Set the system prompt |
| `--max-tokens N` | Limit each reply to N tokens (default 2048) |
| `--dump-tokens PATH` | Save the conversation's token ids to a file |

## Check

```sh
scripts/kizu test .
target/kizukani gpu-speculative-selfcheck both
```

The self-check reports how many of the 12 expected tokens matched.

## Benchmark

kizukani is not the fastest engine on this machine. oMLX with DFlash 2 was faster on all six tasks.

Tokens per second while generating, as the mean of two rounds of 256 tokens per task:

| Engine and model | Prose, short | Code, short | Thinking, short | Prose, long | Code, long | Thinking, long | Mean | Reading long input |
|---|---|---|---|---|---|---|---|---|
| oMLX 0.8.0, 4-bit + DFlash 2 | 24.6 | 40.6 | 39.6 | 31.7 | 30.6 | 28.4 | **32.6** | 159 |
| mlx-vlm 0.8.0, 4-bit + MTP | 24.8 | 30.1 | 28.7 | 28.4 | 23.6 | 22.9 | **26.4** | 164 |
| **kizukani, fastest model** | 18.4 | 35.5 | 34.5 | 21.6 | 20.3 | 14.6 | **24.1** | 59 |
| **kizukani, quality model** | 16.5 | 31.1 | 28.9 | 16.4 | 18.4 | 22.9 | **22.4** | 50 |
| mlx-lm 0.32.2, 4-bit | 18.6 | 18.8 | 19.3 | 18.0 | 18.8 | 18.8 | **18.7** | 159 |
| llama.cpp, Q4_K_M | 11.5 | 11.5 | 11.6 | 11.4 | 11.4 | 11.3 | **11.4** | 142 |

"Short" prompts have about 30 to 95 tokens and "long" prompts about 2,000. "Reading long input" is in tokens per second.

- **Machine:** MacBook Pro with an Apple M4 Max (40-core GPU) and 128 GB of memory, macOS 27.0, on AC power in High Power mode, measured on November 19, 2026.
- **Treat these as reference numbers.** The Mac was not fully idle during the run.
- **Speed only.** The engines use different quantizations and model sizes, so this table says nothing about answer quality.
- The difference between the two kizukani models is within the variation between rounds.

[bench/README.md](bench/README.md) explains how to reproduce the run, and [bench/results](bench/results) holds the raw data.

## Known limits

- Chat runs on Apple Silicon only. The Windows Vulkan path covers a decode self-check, without speculative decoding or chat.
- A conversation can hold up to 32,768 tokens.
- Each line of input is one message, so pasted text with line breaks becomes several messages.
- Replies always take the most likely next token. There is no sampling.
- Tool calls and image input are not supported.
- Reading long input is slow.

## License

Apache License 2.0. See [LICENSE](LICENSE), [NOTICE](NOTICE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Model files are distributed separately under their own terms and are not part of this repository.
