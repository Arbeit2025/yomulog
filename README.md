# よむログ（yomulog）

読書版ミニ Studylog。本のタイトルと「今日読んだページ数」を軽く残していくための、小さな読書記録ツールです。単一ファイル Flask + SQLite で動きます。

## 由来

cocoletter の軽さ × Studylog の読書版、という発想で作りました。Studylog 本体には手を入れず、読書だけに絞った軽量版です。

## できること

- 読書記録の登録
  - 本のタイトル（必須）
  - 著者（任意）
  - 今日読んだページ数（必須・0以上の整数）
  - ひとことメモ（任意）
  - 日付（既定は今日・JST）
- 記録の一覧（新しい順）
- 本ごとの合計ページ数
- 今月の合計ページ数と、読んだ日数の集計
- 記録の削除

## ローカル起動

```bash
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000 を開く
```

データベースは既定で `app.py` と同じフォルダの `yomulog.db` に作られます。場所を変えたい場合は環境変数 `YOMULOG_DB` にパスを指定してください。

## テスト

```bash
python -m unittest discover -s tests
```

テストは一時データベースを使い、実際の `yomulog.db` には触れません。

## Render へのデプロイ

`render.yaml` を使って Web Service（Free）としてデプロイできます。起動コマンドは `gunicorn app:app`、ヘルスチェックは `/healthz` です。

## 注意（データの保持について）

Render の Free プランではディスクが永続化されないため、再デプロイや再起動のタイミングで SQLite のデータ（読書記録）が消えることがあります。大事な記録の保管場所としては使わず、軽く試すためのものとして扱ってください。

## 構成

- `app.py` … 本体（単一ファイル）
- `tests/test_app.py` … unittest（一時DB使用）
- `requirements.txt` … Flask と gunicorn のみ
- `render.yaml` … Render 用設定
