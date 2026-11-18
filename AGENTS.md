# kizukani

An Apple Silicon engine for YASAKANI model files, written in Kizu, including its GPU kernels.

## Commands

Run everything from the repository root. Build the Kizu compiler at commit `7f79ac81e1d62534690339cb044291d97d3ba21b` with `just stage1`, and point `KIZU_SRC` at that checkout.

| Task | Command |
|---|---|
| Build the kernels and the binary | `scripts/build` |
| Run the tests | `scripts/kizu test .` |
| Check decoding against the expected tokens | `target/kizukani gpu-speculative-selfcheck both` |
| Check the comment rule | `python3 scripts/comment-lint/check.py` |
| Test the comment lint | `python3 scripts/comment-lint/test.py` |

The tests and the self-check need `target/kernels.metal` and the model folder under `models/`.

## Comments

Names say what code does, and tests say what it promises. Reasons and background belong in commit messages.

Kizu sources carry only two kinds of comment:

- `// SAFETY:` justifies unsafe code. Keep it short and state the assumptions.
- `///` documents a declaration where the language asks for it, such as an unsafe declaration.

`scripts/comment-lint/check.py` enforces this in pre-commit and CI.

## Changes

- Before finishing a change, build, run the tests and the comment lint, and confirm that the self-check matches 12 of 12 tokens.
- A change to the kernels or the decoder must not change the generated tokens.
- Do not commit `models/` or `target/`. Model files are distributed separately by the YASAKANI authors.
- Keep absolute paths and machine-specific details out of the repository.
- Publish speed claims only with the conditions they were measured under.
