# Kamir

Momir Basicをテーブルトップで遊ぶための印刷用プロキシカードを生成するツールです。  
MTGJSONのデータベースからクリーチャーカードを抽出し、Scryfallから画像を取得して印刷用PDFを生成します。

## 動作環境

- Raspberry Pi OS Bookworm (64-bit) ヘッドレス、または macOS / Linux
- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) (パッケージ管理)

## セットアップ

```bash
# 依存パッケージをインストール
uv sync

# AllPrintings.sqlite を mtgjson.com からダウンロードして配置
# https://mtgjson.com/downloads/all-files/#allprintings
mkdir -p data/db
mv AllPrintings.sqlite data/db/
```

## 使い方

```bash
# 全ステージを順番に実行（推奨）
uv run kamir run

# 個別に実行する場合
uv run kamir build-db       # Stage 1: カードDBを構築
uv run kamir fetch-images   # Stage 2: Scryfallから画像を取得
uv run kamir make-pdfs      # Stage 3: 印刷用PDFを生成

# デバッグログを有効にする
uv run kamir --debug run
```

各ステージは中断・再開に対応しています。処理済みの画像・PDFはスキップされます。

## 出力

| パス | 内容 |
|---|---|
| `data/db/kamir_cardpool.sqlite` | フィルタ済みカードDB |
| `data/img/{mana_value}/{card_name}.jpg` | グレースケール処理済み画像 |
| `data/pdf/{mana_value}/{card_name}.pdf` | 印刷用プロキシPDF (48mm × 67mm) |
| `logs/kamir.log` | 実行ログ |

## テスト

```bash
uv run pytest
```

## 設定

`config.toml` で動作をカスタマイズできます。

```toml
[sets]
allowed = ["LEA", "2ED", ...]   # 使用するエキスパンション

[scryfall]
request_delay = 1.0             # APIリクエスト間隔（秒）

[image]
crop = [26, 47, 197, 147]       # トリミング範囲 (left, upper, right, lower)
```

## プロジェクト構成

```
kamir/
├── cli.py          # エントリーポイント
├── config.py       # 設定読み込み
├── db/             # MTGJSONロードおよびDB書き込み
├── filter/         # カードフィルタリング（純粋関数）
├── images/         # Scryfall取得・画像処理・キャッシュ
├── render/         # PDF生成
└── utils/          # ログ・進捗バー
```

詳細は [docs/architecture.md](docs/architecture.md) を参照してください。
