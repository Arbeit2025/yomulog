# ============================================================
# yomulog（よむログ）- 読書版ミニ Studylog
#
# 目次
#   1. 設定・DB初期化
#   2. 集計ヘルパー
#   3. 画面テンプレート
#   4. ルート（一覧・登録・削除・healthz）
#   5. アプリ生成・起動
#
# 単一ファイル Flask + SQLite。DB は既定で app.py と同じ場所の
# yomulog.db（環境変数 YOMULOG_DB で変更可）。
# ============================================================

import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, g, jsonify, redirect, render_template_string, request, url_for

# ============================
# 1. 設定・DB初期化
# ============================

JST = ZoneInfo("Asia/Tokyo")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.environ.get("YOMULOG_DB", os.path.join(BASE_DIR, "yomulog.db"))


def today_jst():
    """今日の日付（JST）を YYYY-MM-DD で返す。"""
    return datetime.now(JST).strftime("%Y-%m-%d")


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL DEFAULT '',
                pages INTEGER NOT NULL,
                memo TEXT NOT NULL DEFAULT '',
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# ============================
# 2. 集計ヘルパー
# ============================


def fetch_records(db):
    """記録を新しい順（日付→登録順）に返す。"""
    return db.execute(
        "SELECT id, title, author, pages, memo, date FROM records "
        "ORDER BY date DESC, id DESC"
    ).fetchall()


def fetch_book_totals(db):
    """本ごとの合計ページ数（タイトル＋著者でまとめる）。"""
    return db.execute(
        "SELECT title, author, SUM(pages) AS total, COUNT(*) AS cnt "
        "FROM records GROUP BY title, author ORDER BY total DESC, title ASC"
    ).fetchall()


def fetch_month_summary(db, month_prefix):
    """指定月（YYYY-MM）の合計ページ数と読んだ日数を返す。"""
    row = db.execute(
        "SELECT COALESCE(SUM(pages), 0) AS total, COUNT(DISTINCT date) AS days "
        "FROM records WHERE date LIKE ?",
        (month_prefix + "%",),
    ).fetchone()
    return {"total_pages": row["total"], "days": row["days"]}


# ============================
# 3. 画面テンプレート
# ============================

INDEX_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>よむログ</title>
<style>
  body { font-family: sans-serif; margin: 2em auto; max-width: 720px; padding: 0 1em;
         background: #fdfaf5; color: #333; }
  h1 { font-size: 1.5em; }
  .summary { background: #fff; border: 1px solid #e5dccb; border-radius: 8px;
             padding: 0.8em 1em; margin: 1em 0; }
  form.add { background: #fff; border: 1px solid #e5dccb; border-radius: 8px;
             padding: 1em; margin: 1em 0; }
  label { display: block; margin: 0.6em 0 0.2em; font-size: 0.9em; }
  input, textarea { width: 100%; box-sizing: border-box; padding: 0.5em;
                    border: 1px solid #ccc; border-radius: 4px; }
  button { margin-top: 0.8em; padding: 0.5em 1.2em; border: 0; border-radius: 4px;
           background: #8a6d3b; color: #fff; cursor: pointer; }
  .error { background: #fdecea; border: 1px solid #e0a49e; color: #8b2e24;
           border-radius: 8px; padding: 0.6em 1em; }
  table { width: 100%; border-collapse: collapse; background: #fff; }
  th, td { border-bottom: 1px solid #eee; padding: 0.5em; text-align: left;
           font-size: 0.92em; vertical-align: top; }
  .del { background: #b0a696; padding: 0.25em 0.7em; margin: 0; }
  .memo { color: #666; }
</style>
</head>
<body>
<h1>📚 よむログ</h1>
<p>読書版ミニ Studylog。今日読んだ分を、軽く残すための記録帳です。</p>

<div class="summary">
  <strong>今月（{{ month_label }}）</strong>：
  合計 {{ month_summary.total_pages }} ページ ／ 読んだ日数 {{ month_summary.days }} 日
</div>

{% if error %}<p class="error">{{ error }}</p>{% endif %}

<form class="add" method="post" action="{{ url_for('add') }}">
  <label for="title">本のタイトル（必須）</label>
  <input id="title" name="title" type="text" value="{{ form.title }}" required>
  <label for="author">著者（任意）</label>
  <input id="author" name="author" type="text" value="{{ form.author }}">
  <label for="pages">今日読んだページ数（必須・0以上）</label>
  <input id="pages" name="pages" type="number" min="0" step="1" value="{{ form.pages }}" required>
  <label for="date">日付</label>
  <input id="date" name="date" type="date" value="{{ form.date }}">
  <label for="memo">ひとことメモ（任意）</label>
  <textarea id="memo" name="memo" rows="2">{{ form.memo }}</textarea>
  <button type="submit">記録する</button>
</form>

<h2>本ごとの合計</h2>
{% if book_totals %}
<table>
  <tr><th>タイトル</th><th>著者</th><th>合計ページ</th><th>記録数</th></tr>
  {% for b in book_totals %}
  <tr>
    <td>{{ b.title }}</td><td>{{ b.author }}</td>
    <td>{{ b.total }}</td><td>{{ b.cnt }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p>まだ記録がありません。</p>
{% endif %}

<h2>記録の一覧</h2>
{% if records %}
<table>
  <tr><th>日付</th><th>タイトル</th><th>ページ</th><th>メモ</th><th></th></tr>
  {% for r in records %}
  <tr>
    <td>{{ r.date }}</td>
    <td>{{ r.title }}{% if r.author %}（{{ r.author }}）{% endif %}</td>
    <td>{{ r.pages }}</td>
    <td class="memo">{{ r.memo }}</td>
    <td>
      <form method="post" action="{{ url_for('delete', record_id=r.id) }}"
            onsubmit="return confirm('この記録を削除しますか？');">
        <button class="del" type="submit">削除</button>
      </form>
    </td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p>まだ記録がありません。最初の1冊をどうぞ。</p>
{% endif %}
</body>
</html>
"""

# ============================
# 4. ルート
# ============================


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH
    init_db(app.config["DB_PATH"])

    def get_db():
        if "db" not in g:
            conn = sqlite3.connect(app.config["DB_PATH"])
            conn.row_factory = sqlite3.Row
            g.db = conn
        return g.db

    @app.teardown_appcontext
    def close_db(exc=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    def render_index(error=None, form=None):
        db = get_db()
        today = today_jst()
        month_prefix = today[:7]
        return render_template_string(
            INDEX_HTML,
            records=fetch_records(db),
            book_totals=fetch_book_totals(db),
            month_summary=fetch_month_summary(db, month_prefix),
            month_label=month_prefix.replace("-", "年") + "月",
            error=error,
            form=form or {"title": "", "author": "", "pages": "", "memo": "", "date": today},
        )

    @app.route("/", methods=["GET"])
    def index():
        return render_index()

    @app.route("/add", methods=["POST"])
    def add():
        title = (request.form.get("title") or "").strip()
        author = (request.form.get("author") or "").strip()
        pages_raw = (request.form.get("pages") or "").strip()
        memo = (request.form.get("memo") or "").strip()
        date = (request.form.get("date") or "").strip() or today_jst()

        form = {"title": title, "author": author, "pages": pages_raw, "memo": memo, "date": date}

        if not title:
            return render_index(error="タイトルは必須です。", form=form), 400
        try:
            pages = int(pages_raw)
        except ValueError:
            return render_index(error="ページ数は整数で入力してください。", form=form), 400
        if pages < 0:
            return render_index(error="ページ数は0以上で入力してください。", form=form), 400
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return render_index(error="日付の形式が正しくありません。", form=form), 400

        db = get_db()
        db.execute(
            "INSERT INTO records (title, author, pages, memo, date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, author, pages, memo, date, datetime.now(JST).isoformat(timespec="seconds")),
        )
        db.commit()
        return redirect(url_for("index"))

    @app.route("/delete/<int:record_id>", methods=["POST"])
    def delete(record_id):
        db = get_db()
        db.execute("DELETE FROM records WHERE id = ?", (record_id,))
        db.commit()
        return redirect(url_for("index"))

    @app.route("/healthz", methods=["GET"])
    def healthz():
        return jsonify({"status": "ok"})

    return app


# ============================
# 5. アプリ生成・起動
# ============================

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
