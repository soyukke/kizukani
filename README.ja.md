# kizukani

[YASAKANI](https://github.com/yasakani-dev/yasakani) のモデルファイルを Apple Silicon で動かす非公式のエンジンです。GPU カーネルまで含めて [Kizu](https://github.com/kizu-lang/kizu) で書いています。

[English](README.md)

kizukani は、YASAKANI の開発者が公開している圧縮済みの `.yskn` ファイルから Qwen3.8-27B を実行します。Metal を使って GPU でデコードし、公開されている下書きモデルで投機デコードを行います。

モデルファイルと `.yskn` 形式は YASAKANI の開発者の成果です。Mac で動かす方法は [Mackani](https://github.com/TKY-27/Mackani) から学びました。YASAKANI の開発者、TKY-27 さん、Qwen チームに感謝します。kizukani はこれらのいずれとも関係がなく、公認も受けていません。

## 必要なもの

- Apple Silicon の Mac。動作確認はまだ 1 台のみです。
- モデルフォルダ用の空き容量。最速版は約 13 GB、品質版は約 15 GB です。
- コミット `7f79ac81e1d62534690339cb044291d97d3ba21b` の Kizu コンパイラ。
- モデルのダウンロードに使う [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli)（`hf`）。

## ビルド

Kizu コンパイラをビルドします。必要なものは Kizu のリポジトリを参照してください。

```sh
git clone https://github.com/kizu-lang/kizu
cd kizu
git checkout 7f79ac81e1d62534690339cb044291d97d3ba21b
just stage1
export KIZU_SRC="$PWD"
```

次に、このリポジトリのルートで kizukani をビルドします。

```sh
scripts/build
```

`target/kernels.metal` と `target/kizukani` が作られます。

## モデルの入手

```sh
hf download yasakani-dev/Qwen3.8-27B-YASAKANI-speed --local-dir models/qwen38-27b-speed
```

元のモデルにより近い品質版を使う場合は、こちらもダウンロードします。

```sh
hf download yasakani-dev/Qwen3.8-27B-YASAKANI-quality --local-dir models/qwen38-27b-quality
```

## チャット

モデルとカーネルを相対パスで探すので、リポジトリのルートで実行してください。

```sh
target/kizukani chat
```

メッセージを入力して Enter を押します。`/exit` か入力の終了（Ctrl-D）で終わります。

| オプション | 内容 |
|---|---|
| `--no-think` | 思考を書き出さずに回答する |
| `--model NAME` | `speed`（既定）か `quality` を選ぶ |
| `--system TEXT` | システムプロンプトを指定する |
| `--max-tokens N` | 1 回の回答を N token までにする（既定 2048） |
| `--dump-tokens PATH` | 会話の token ID をファイルに保存する |

## 動作確認

```sh
scripts/kizu test .
target/kizukani gpu-speculative-selfcheck both
```

selfcheck は、期待する 12 token のうち一致した数を表示します。

## ベンチマーク

このマシンで最速のエンジンは kizukani ではありません。全 6 タスクで oMLX + DFlash 2 のほうが速い結果でした。

生成中の 1 秒あたりの token 数です。タスクごとに 256 token を 2 周生成した平均です。

| エンジンとモデル | 文章 短 | コード 短 | 思考 短 | 文章 長 | コード 長 | 思考 長 | 平均 | 長い入力の読み込み |
|---|---|---|---|---|---|---|---|---|
| oMLX 0.8.0、4bit + DFlash 2 | 24.6 | 40.6 | 39.6 | 31.7 | 30.6 | 28.4 | **32.6** | 159 |
| mlx-vlm 0.8.0、4bit + MTP | 24.8 | 30.1 | 28.7 | 28.4 | 23.6 | 22.9 | **26.4** | 164 |
| **kizukani、最速版** | 18.4 | 35.5 | 34.5 | 21.6 | 20.3 | 14.6 | **24.1** | 59 |
| **kizukani、品質版** | 16.5 | 31.1 | 28.9 | 16.4 | 18.4 | 22.9 | **22.4** | 50 |
| mlx-lm 0.32.2、4bit | 18.6 | 18.8 | 19.3 | 18.0 | 18.8 | 18.8 | **18.7** | 159 |
| llama.cpp、Q4_K_M | 11.5 | 11.5 | 11.6 | 11.4 | 11.4 | 11.3 | **11.4** | 142 |

「短」は約 30〜95 token、「長」は約 2,000 token の入力です。「長い入力の読み込み」の単位は token/秒です。

- **マシン:** MacBook Pro（Apple M4 Max、40 コア GPU、メモリ 128 GB）、macOS 27.0。電源接続、高出力モードで、2026 年 11 月 19 日に計測しました。
- **参考値として見てください。** 計測中の Mac は完全な待機状態ではありませんでした。
- **比較しているのは速度だけです。** エンジンごとに量子化とモデルサイズが違うので、回答の品質はこの表からはわかりません。
- kizukani の 2 つのモデルの差は、周回ごとのばらつきの範囲内です。

再現手順は [bench/README.md](bench/README.md)、生データは [bench/results](bench/results) にあります。

## 既知の制限

- チャットは Apple Silicon 専用です。Windows の Vulkan 版はデコードの selfcheck のみで、投機デコードとチャットには対応していません。
- 1 つの会話で扱えるのは 32,768 token までです。
- 入力は 1 行で 1 メッセージです。改行を含む文章を貼り付けると、複数のメッセージになります。
- 回答は常に最も確率の高い token を選びます。サンプリングには対応していません。
- ツール呼び出しと画像入力には対応していません。
- 長い入力の読み込みには時間がかかります。

## ライセンス

Apache License 2.0 です。[LICENSE](LICENSE)、[NOTICE](NOTICE)、[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) を参照してください。モデルファイルはそれぞれの条件で別途配布されていて、このリポジトリには含まれません。
