from flask import Flask, render_template, request, session, redirect
import random
import csv
import os
import time
import psycopg
from datetime import datetime

app = Flask(__name__)
app.secret_key = "word_test_secret"

WORD_FILE = "words.csv"

# -----------------------
# Supabase DB接続
# -----------------------
def get_conn():
    return psycopg.connect(os.environ["DATABASE_URL"])

# -----------------------
# 単語読み込み
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
# ホーム
# -----------------------
@app.route("/")
def start():
    return render_template("start.html")

# -----------------------
# 開始
# -----------------------
@app.route("/begin", methods=["POST"])
def begin():

    subject_id = request.form["subject_id"].strip()
    if subject_id == "":
        subject_id = "unknown"

    questions = random.sample(word_list, len(word_list))

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
        candidate = random.choice(word_list)["japanese"]
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
        progress=int((idx + 1) / len(questions) * 100)
    )

# -----------------------
# 回答保存
# -----------------------
def save_result(subject_id, question_no, word, correct, reaction_time, unknown_flag):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO results
        (subject_id, question_no, word, correct, reaction_time, unknown_flag)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        subject_id,
        question_no,
        word,
        correct,
        reaction_time,
        unknown_flag
    ))

    conn.commit()
    cur.close()
    conn.close()

# -----------------------
# 回答処理
# -----------------------
@app.route("/answer", methods=["POST"])
def answer():

    selected = request.form.get("answer", "分からない")

    idx = session["index"]
    q = session["questions"][idx]

    reaction_time = round(time.time() - session["start_time"], 3)

    correct_word = q["japanese"]

    if selected == "分からない":
        correct = 0
        unknown = 1
    else:
        correct = int(selected == correct_word)
        unknown = 0

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
# 終了＋CSV出力
# -----------------------
@app.route("/finish")
def finish():

    subject_id = session["subject_id"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            subject_id,
            question_no,
            word,
            correct,
            reaction_time,
            unknown_flag,
            created_at
        FROM results
        WHERE subject_id = %s
        ORDER BY question_no
    """, (subject_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    os.makedirs("results", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_file = f"results/{subject_id}_{timestamp}.csv"

    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow([
            "subject_id",
            "question_no",
            "word",
            "correct",
            "reaction_time",
            "unknown_flag",
            "created_at"
        ])

        writer.writerows(rows)

    return render_template(
        "finish.html",
        subject_id=subject_id,
        count=len(rows),
        csv_file=os.path.basename(csv_file)
    )

# -----------------------
# 起動
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)