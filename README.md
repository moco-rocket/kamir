# Kamir

Momir BasicをRaspberry Pi + サーマルプリンターで紙卓プレイするためのツールです。

マナ総量Xを宣言して土地を1枚捨てると、Kamirがカードプールからクリーチャーをランダムに抽選し、
MJ-5890Kサーマルプリンターにカード情報を印刷します。印刷されたスリップをトークンとして場に置きます。

## 動作環境

- Raspberry Pi OS Bookworm (64-bit) ヘッドレス、または macOS / Linux
- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) (パッケージ管理)
- MJ-5890K サーマルプリンター (USB接続)

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
kamir build-db
```

`uv sync` を実行すると `.venv/bin/kamir` にエントリーポイントが生成されます。
仮想環境をアクティベートすることで、以降 `kamir` を直接呼び出せます。

```bash
source .venv/bin/activate
```

Raspberry Pi で常用する場合は `~/.bashrc` に以下を追記するか、
`uv tool install --editable .` でシステム全体にインストールすることもできます。

```bash
# ~/.bashrc に追記する場合（KAMIR_DIR はリポジトリのパスに合わせて変更）
export PATH="$HOME/kamir/.venv/bin:$PATH"
```

## 使い方

```bash
# カードプールDBを構築（AllPrintings.sqlite から）
kamir build-db

# DBを完全に作り直す（スキーマ変更後やリセット時）
kamir build-db --force

# アートのダウンロード状況を確認する
kamir art-status

# ゲームセッション開始
kamir play

# ハードウェアテスト（マナ総量4のクリーチャーを1枚印刷）
kamir print-test --mv 4

# デバッグログを有効にする
kamir --debug build-db
```

## 出力

| パス | 内容 |
|---|---|
| `data/db/kamir_cardpool.sqlite` | フィルタ済みカードプールDB |
| `logs/kamir.log` | 実行ログ |

印刷出力はMJ-5890Kサーマルプリンターに直接送られます。ファイルとしては保存されません。

## テスト

```bash
pytest
```

## 設定

プロジェクトルートに `config.toml` を作成します。

```toml
[paths]
mtgjson_db = "data/db/AllPrintings.sqlite"
kamir_db   = "data/db/kamir_cardpool.sqlite"
log_file   = "logs/kamir.log"

[play]
auto_print = true   # false にすると印刷前に確認プロンプトを表示

[printer]
device      = "/dev/usb/lp0"   # Raspberry Pi でのUSBデバイスパス
usb_vendor  = 0x0000            # lsusb で確認
usb_product = 0x0000

[sets]
# allowed = "all" で AllPrintings.sqlite 内の全物理プレイ対象セットを自動収録
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
