from flask import Flask, render_template, request, session, redirect
import random
import csv
import sqlite3
import os
import time
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "word_test_secret"

WORD_FILE = "words.csv"
DB_FILE = "word_test.db"

# -----------------------
# DB初期化
# -----------------------
def init_db():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id TEXT,
        question_no INTEGER,
        word TEXT,
        correct INTEGER,
        reaction_time REAL,
        unknown_flag INTEGER,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# -----------------------
# 回答保存
# -----------------------
def save_result(
    subject_id,
    question_no,
    word,
    correct,
    reaction_time,
    unknown_flag
):

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    INSERT INTO results
    (
        subject_id,
        question_no,
        word,
        correct,
        reaction_time,
        unknown_flag,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        subject_id,
        question_no,
        word,
        correct,
        reaction_time,
        unknown_flag,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


# -----------------------
# 単語読込
# -----------------------
word_list = []

with open(WORD_FILE, encoding="cp932") as f:

    reader = csv.reader(f)

    for row in reader:

        if len(row) >= 2:

            word_list.append({
                "english": row[0].strip(),
                "japanese": row[1].strip()
            })


# -----------------------
# 開始画面
# -----------------------
@app.route("/")
def start():

    return render_template("start.html")


# -----------------------
# テスト開始
# -----------------------
@app.route("/begin", methods=["POST"])
def begin():

    subject_id = request.form["subject_id"].strip()

    if subject_id == "":
        subject_id = "unknown"

    questions = random.sample(
        word_list,
        len(word_list)
    )

    session.clear()

    session["subject_id"] = subject_id
    session["questions"] = questions
    session["index"] = 0

    return redirect("/question")


# -----------------------
# 問題表示
# -----------------------
@app.route("/question")
def question():

    idx = session["index"]
    questions = session["questions"]

    if idx >= len(questions):
        return redirect("/finish")

    q = questions[idx]

    choices = [q["japanese"]]

    while len(choices) < 4:

        candidate = random.choice(
            word_list
        )["japanese"]

        if candidate not in choices:
            choices.append(candidate)

    random.shuffle(choices)

    session["start_time"] = time.time()

    return render_template(
        "question.html",
        word=q["english"],
        number=idx + 1,
        total=len(questions),
        choices=choices,
        progress=int(
            (idx + 1) /
            len(questions) *
            100
        )
    )


# -----------------------
# 回答処理
# -----------------------
@app.route("/answer", methods=["POST"])
def answer():

    selected = request.form.get(
        "answer",
        "分からない"
    )

    idx = session["index"]

    q = session["questions"][idx]

    reaction_time = round(
        time.time() -
        session["start_time"],
        3
    )

    correct_word = q["japanese"]

    if selected == "分からない":

        correct = 0
        unknown = 1

    else:

        correct = int(
            selected == correct_word
        )

        unknown = 0

    # -----------------------
    # DB保存
    # -----------------------
    save_result(
        session["subject_id"],
        idx + 1,
        q["english"],
        correct,
        reaction_time,
        unknown
    )

    session["index"] += 1

    return redirect("/question")


# -----------------------
# 終了
# -----------------------
@app.route("/finish")
def finish():

    subject_id = session["subject_id"]

    # -----------------------
    # 被験者データ取得
    # -----------------------
    conn = sqlite3.connect(DB_FILE)

    query = """
    SELECT
        subject_id AS 被験者ID,
        question_no AS 問題番号,
        word AS 英単語,
        correct AS 正誤,
        reaction_time AS 回答時間,
        unknown_flag AS 分からない,
        created_at AS 記録時刻
    FROM results
    WHERE subject_id = ?
    ORDER BY question_no
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(subject_id,)
    )

    conn.close()

    # -----------------------
    # CSV出力
    # -----------------------
    os.makedirs("results", exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    csv_file = os.path.join(
        "results",
        f"{subject_id}_{timestamp}.csv"
    )

    df.to_csv(
        csv_file,
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------
    # 終了画面
    # -----------------------
    return render_template(
        "finish.html",
        subject_id=subject_id,
        count=len(df),
        csv_file=os.path.basename(csv_file)
    )


# -----------------------
# 起動
# -----------------------
if __name__ == "__main__":

    init_db()

    app.run(debug=True)