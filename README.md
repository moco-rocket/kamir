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

### Raspberry Pi（本番）

```bash
# uv をインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# kamir をインストール
uv tool install git+https://github.com/moco-rocket/kamir.git

# AllPrintings.sqlite を mtgjson.com からダウンロードして配置
# https://mtgjson.com/downloads/all-files/#allprintings
mkdir -p ~/kamir-data/data/db
mv AllPrintings.sqlite ~/kamir-data/data/db/

# config.toml を作成（下記「設定」セクション参照）
# cd ~/kamir-data && cp /path/to/config.toml .

# カードプールDBを構築（初回のみ）
cd ~/kamir-data && kamir build-db
```

`config.toml` の探索順序については下記「設定」セクションを参照してください。
`uv tool upgrade kamir` で最新バージョンに更新できます。

### 開発環境（macOS / Linux）

```bash
git clone https://github.com/moco-rocket/kamir.git
cd kamir
uv sync
source .venv/bin/activate
kamir build-db
```

または venv をアクティベートせずに `uv run kamir build-db` でも実行できます。

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
kamir print-test --mv 4
```

詳細は [docs/printing.md](docs/printing.md) を参照してください。

---

## 使い方

```bash
# カードプールDBを構築（AllPrintings.sqlite から）
kamir build-db

# DBを完全に作り直す（スキーマ変更後やリセット時）
kamir build-db --force

# アートのダウンロード状況を確認する
kamir art-status

# ターミナル対話セッション
kamir play

# GPIOボタン操作セッション（Raspberry Pi）
kamir --config config.toml gpio-play

# ハードウェアテスト（マナ総量4のクリーチャーを1枚印刷）
kamir print-test --mv 4

# デバッグログを有効にする
kamir --debug build-db
```

## GPIO ボタン操作モード（Raspberry Pi）

4つのボタン・TM1637 7セグメント・エラーLEDを使った物理操作モードです。
`uv tool install` で `gpiozero` / `raspberrypi-tm1637` / `lgpio` が自動インストールされます。

```bash
kamir --config config.toml gpio-play
```

- POWERボタン長押し（1秒以上）でプロセスを停止します
- `config.toml` で `os_shutdown = true` を設定すると、OS シャットダウン（`systemctl poweroff`）まで行います

配線・単体テスト・systemd設定の詳細は [docs/gpio-play.md](docs/gpio-play.md) を参照してください。

## 出力

| パス | 内容 |
|---|---|
| `data/db/kamir_cardpool.sqlite` | フィルタ済みカードプールDB |
| `logs/kamir.log` | 実行ログ |

印刷出力はMJ-5890Kサーマルプリンターに直接送られます。ファイルとしては保存されません。

## テスト

開発用チェックアウトから実行します（`uv tool install` 環境では不要）。

```bash
uv run pytest
```

## 設定

`config.toml` の探索順序は以下の通りです:

1. `--config <path>` 引数で明示した場合
2. 環境変数 `KAMIR_CONFIG` が設定されている場合
3. カレントディレクトリの `config.toml`

Raspberry Pi での運用では、`config.toml` のあるディレクトリに `cd` してから実行するか（方法3）、
`--config` で絶対パスを指定してください（方法1）。

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
├── hardware/       # ManaDisplay / ErrorLed プロトコルと実装（TM1637、GPIO LED）
├── play/           # ゲームセッション（ターミナル・GPIO）
└── printer/        # ESC/POS描画 + MJ-5890K送信
```

詳細は [docs/architecture.md](docs/architecture.md) を参照してください。

## Legal

Kamir is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

Card images are provided by [Scryfall](https://scryfall.com) and are used in accordance with their [terms of service](https://scryfall.com/docs/terms).
