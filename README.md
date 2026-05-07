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
# 依存パッケージをインストール
uv sync

# AllPrintings.sqlite を mtgjson.com からダウンロードして配置
# https://mtgjson.com/downloads/all-files/#allprintings
mkdir -p data/db
mv AllPrintings.sqlite data/db/

# カードプールDBを構築（初回のみ）
uv run kamir build-db
```

## 使い方

```bash
# カードプールDBを構築（AllPrintings.sqlite から）
uv run kamir build-db

# ゲームセッション開始（Phase 2 で実装予定）
uv run kamir play

# デバッグログを有効にする
uv run kamir --debug build-db
```

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

`config.toml` で動作をカスタマイズできます。

```toml
[play]
auto_print = false   # trueにすると確認なしで即印刷

[printer]
device      = "/dev/usb/lp0"  # プリンターのUSBデバイスパス
usb_vendor  = 0x0000          # lsusb で確認したVendor ID
usb_product = 0x0000          # lsusb で確認したProduct ID

[sets]
allowed = ["LEA", "2ED", ...]  # 使用するエキスパンション
```

## プロジェクト構成

```
kamir/
├── domain.py       # Card データクラス（全サブシステム共通）
├── cli.py          # エントリーポイント
├── config.py       # 設定読み込み
├── db/             # MTGJSONロードおよびDB書き込み
├── filter/         # カードフィルタリング（純粋関数）+ to_card()
├── play/           # ゲームセッション (Phase 2)
└── printer/        # ESC/POS描画 + MJ-5890K送信 (Phase 3)
```

詳細は [docs/architecture.md](docs/architecture.md) を参照してください。

## 実装フェーズ

| フェーズ | 内容 | 状態 |
|---|---|---|
| Phase 1 | Card ドメインモデル、DBビルダー、モジュール整理 | ✅ 完了 |
| Phase 2 | プレイアプリ（対話型クリーチャー選択・ターミナル表示） | 実装中 |
| Phase 3 | 印刷（ESC/POSテキスト描画・MJ-5890K送信） | 未着手 |
| Phase 4 | Raspberry Pi実機テスト・設定調整 | 未着手 |
