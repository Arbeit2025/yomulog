import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app, today_jst  # noqa: E402


class YomulogTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app(self.db_path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def add_record(self, title="テストの本", author="著者A", pages="30",
                   memo="おもしろい", date=""):
        return self.client.post(
            "/add",
            data={"title": title, "author": author, "pages": pages,
                  "memo": memo, "date": date},
        )

    # --- healthz ---
    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), {"status": "ok"})

    # --- 登録と一覧 ---
    def test_add_and_list(self):
        res = self.add_record()
        self.assertEqual(res.status_code, 302)
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("テストの本", body)
        self.assertIn("著者A", body)
        self.assertIn("おもしろい", body)

    def test_list_newest_first(self):
        self.add_record(title="古い本", date="2026-10-01")
        self.add_record(title="新しい本", date="2026-10-30")
        body = self.client.get("/").get_data(as_text=True)
        records_section = body.split("記録の一覧", 1)[1]
        self.assertLess(records_section.index("新しい本"), records_section.index("古い本"))

    def test_default_date_is_today_jst(self):
        self.add_record()
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn(today_jst(), body)

    def test_author_and_memo_optional(self):
        res = self.client.post("/add", data={"title": "タイトルのみ", "pages": "5"})
        self.assertEqual(res.status_code, 302)
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("タイトルのみ", body)

    # --- 集計 ---
    def test_book_totals(self):
        self.add_record(title="本X", pages="10", date="2026-10-01")
        self.add_record(title="本X", pages="15", date="2026-10-02")
        self.add_record(title="本Y", pages="7", date="2026-10-02")
        body = self.client.get("/").get_data(as_text=True)
        # 本ごとの合計：本X=25 が表示される
        self.assertIn("25", body)
        self.assertIn("本X", body)
        self.assertIn("本Y", body)

    def test_month_summary(self):
        today = today_jst()
        other_month = "2020-01-15"
        self.add_record(title="今月の本", pages="12", date=today)
        self.add_record(title="今月の本", pages="8", date=today)
        self.add_record(title="昔の本", pages="100", date=other_month)
        body = self.client.get("/").get_data(as_text=True)
        # 今月の合計は 20 ページ・読んだ日数 1 日（昔の100ページは含まない）
        self.assertIn("合計 20 ページ", body)
        self.assertIn("読んだ日数 1 日", body)

    # --- 削除 ---
    def test_delete(self):
        self.add_record(title="消える本")
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("消える本", body)
        # 一覧に含まれる削除フォームの対象IDは 1 件目 = 1
        res = self.client.post("/delete/1")
        self.assertEqual(res.status_code, 302)
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("消える本", body)

    # --- バリデーション ---
    def test_title_required(self):
        res = self.add_record(title="")
        self.assertEqual(res.status_code, 400)
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("合計 30 ページ", body)

    def test_pages_must_be_nonnegative_int(self):
        for bad in ("-1", "abc", "1.5", ""):
            res = self.add_record(pages=bad)
            self.assertEqual(res.status_code, 400, f"pages={bad!r} は 400 のはず")

    def test_pages_zero_ok(self):
        res = self.add_record(pages="0")
        self.assertEqual(res.status_code, 302)

    def test_bad_date_rejected(self):
        res = self.add_record(date="2026/10/31")
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
