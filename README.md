# Kamir

Momir BasicをRaspberry Pi + サーマルプリンターで紙卓プレイするためのツールです。

マナ総量Xを宣言して土地を1枚捨てると、Kamirがカードプールからクリーチャーをランダムに抽選し、
MJ-5890Kサーマルプリンターにカード情報を印刷します。印刷されたスリップをトークンとして場に置きます。

## 動作環境

- Raspberry Pi OS Bookworm (64-bit) ヘッドレス
- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) (パッケージ管理)
- MJ-5890K サーマルプリンター (USB接続)

> **Note**: `kamir build-db` / `kamir play` はデータ確認や開発目的で macOS / Linux でも動作しますが、
> プリンターへの出力は Linux (`/dev/usb/lp*`) 専用です。

## セットアップ

```bash
# uv をインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# リポジトリをクローン
git clone https://github.com/moco-rocket/kamir.git
cd kamir

# 依存パッケージをインストール（kamir コマンドも .venv/bin/ に生成される）
uv sync

# AllPrintings.sqlite を mtgjson.com からダウンロードして配置
# https://mtgjson.com/downloads/all-files/#allprintings
mkdir -p data/db
mv AllPrintings.sqlite data/db/

# config.toml を作成（下記「設定」セクション参照）

# カードプールDBを構築（初回のみ）
uv run kamir build-db
```

`uv sync` を実行すると `.venv/bin/kamir` にエントリーポイントが生成されます。
仮想環境をアクティベートすることで、以降 `kamir` を直接呼び出せます。

```bash
source .venv/bin/activate
```

Raspberry Pi で常用する場合は `~/.bashrc` に以下を追記するか、
`uv tool install` でシステム全体にインストールすることもできます。

```bash
# ~/.bashrc に追記する場合（KAMIR_DIR はリポジトリのパスに合わせて変更）
export PATH="$HOME/kamir/.venv/bin:$PATH"
```

`uv tool install` でインストールした場合は、`config.toml` の場所を明示する必要があります
（インストール先ディレクトリとは無関係になるため）。

```bash
uv tool install git+https://github.com/moco-rocket/kamir.git

# 方法 A: 環境変数で固定（systemd や .bashrc に設定）
export KAMIR_CONFIG=/home/pi/kamir-data/config.toml
kamir play

# 方法 B: 実行のたびに指定
kamir --config /home/pi/kamir-data/config.toml play

# 方法 C: config.toml のあるディレクトリに cd してから実行
cd /home/pi/kamir-data && kamir play
```

## Raspberry Pi ハードウェア準備

プリンターを使う前に、以下をRaspberry Pi上で一度だけ実行してください。

**1. プリンターをUSBで接続し、デバイスを確認する**

```bash
ls /dev/usb/lp*
# → /dev/usb/lp0 などが表示されれば認識されている
```

**2. ユーザーに印刷デバイスへのアクセス権を付与する**

```bash
sudo usermod -aG lp $USER
```

設定を反映するため、一度ログアウトして再ログインしてください。

**3. `config.toml` のデバイスパスを確認する**

`config.toml` の `[printer] device` が上記で確認したパスと一致していることを確かめてください。

**4. 動作確認**

```bash
uv run kamir print-test --mv 4
```

詳細は [docs/printing.md](docs/printing.md) を参照してください。

---

## 使い方

> **Note**: `kamir` コマンドは仮想環境内にインストールされます。
> `source .venv/bin/activate` で有効化するか、常に `uv run kamir` 経由で実行してください。

```bash
# カードプールDBを構築（AllPrintings.sqlite から）
uv run kamir build-db

# DBを完全に作り直す（スキーマ変更後やリセット時）
uv run kamir build-db --force

# アートのダウンロード状況を確認する
uv run kamir art-status

# ターミナル対話セッション
uv run kamir play

# GPIOボタン操作セッション（Raspberry Pi）
uv run kamir --config config.toml gpio-play

# ハードウェアテスト（マナ総量4のクリーチャーを1枚印刷）
uv run kamir print-test --mv 4

# デバッグログを有効にする
uv run kamir --debug build-db
```

## GPIO ボタン操作モード（Raspberry Pi）

4つのボタン・TM1637 7セグメント・エラーLEDを使った物理操作モードです。
`uv sync` で `gpiozero` / `raspberrypi-tm1637` / `lgpio` が自動インストールされます。

```bash
uv run kamir --config config.toml gpio-play
```

POWERボタン長押し（1秒以上）でプロセスを終了します。

配線・単体テスト・systemd設定の詳細は [docs/gpio-play.md](docs/gpio-play.md) を参照してください。

## 出力

| パス | 内容 |
|---|---|
| `data/db/kamir_cardpool.sqlite` | フィルタ済みカードプールDB |
| `logs/kamir.log` | 実行ログ |

印刷出力はMJ-5890Kサーマルプリンターに直接送られます。ファイルとしては保存されません。

## テスト

```bash
uv run pytest
```

## 設定

`config.toml` の探索順序は以下の通りです:

1. `--config <path>` 引数で明示した場合
2. 環境変数 `KAMIR_CONFIG` が設定されている場合
3. カレントディレクトリの `config.toml`

`uv sync` を使った開発環境ではリポジトリルートから実行するため 3 が自然に機能します。
`uv tool install` でインストールした場合は 1 か 2 を利用してください。

`config.toml` の内容:

```toml
[paths]
mtgjson_db = "data/db/AllPrintings.sqlite"
kamir_db   = "data/db/kamir_cardpool.sqlite"
log_file   = "logs/kamir.log"

[play]
auto_print = true   # false にすると印刷前に確認プロンプトを表示

[printer]
device = "/dev/usb/lp0"  # Raspberry Pi でのUSBデバイスパス（ls /dev/usb/lp* で確認）

[sets]
# allowed = "*" で AllPrintings.sqlite 内の全物理プレイ対象セットを自動収録
# （Un-シリーズ・アルケミー・デジタル専用セットを除く）
allowed = ["LEA", "2ED", "3ED", "4ED", "5ED", "6ED", "7ED", "8ED", "9ED", "10E"]
```

## プロジェクト構成

```
kamir/
├── domain.py       # Card データクラス（全サブシステム共通）
├── cli.py          # エントリーポイント
├── config.py       # 設定読み込み
├── db/             # MTGJSONロードおよびDB書き込み
├── filter/         # カードフィルタリング（純粋関数）+ to_card()
├── play/           # ゲームセッション
└── printer/        # ESC/POS描画 + MJ-5890K送信
```

詳細は [docs/architecture.md](docs/architecture.md) を参照してください。

## Legal

Kamir is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

Card images are provided by [Scryfall](https://scryfall.com) and are used in accordance with their [terms of service](https://scryfall.com/docs/terms).
