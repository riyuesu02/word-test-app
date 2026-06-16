from flask import Flask, render_template, request, session, redirect
import random
import csv
import os
import time
import psycopg
from dotenv import load_dotenv
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = "word_test_secret"

WORD_FILE = "words.csv"


# -----------------------
# DB接続
# -----------------------
def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise Exception("DATABASE_URL is not set")
    return psycopg.connect(url, sslmode="require")


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
# HOME
# -----------------------
@app.route("/")
def start():
    return render_template("start.html")


# -----------------------
# START
# -----------------------
@app.route("/begin", methods=["POST"])
def begin():

    subject_id = request.form["subject_id"].strip() or "unknown"

    session.clear()
    session["subject_id"] = subject_id
    session["session_id"] = str(uuid.uuid4())  # ★実験単位
    session["questions"] = random.sample(word_list, len(word_list))
    session["index"] = 0

    return redirect("/question")


# -----------------------
# QUESTION
# -----------------------
@app.route("/question")
def question():

    if "questions" not in session:
        return redirect("/")

    idx = session["index"]
    questions = session["questions"]

    if idx >= len(questions):
        return redirect("/finish")

    q = questions[idx]

    choices = [q["japanese"]]
    while len(choices) < 4:
        c = random.choice(word_list)["japanese"]
        if c not in choices:
            choices.append(c)

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
# DB保存のみ
# -----------------------
def save_result(subject_id, session_id, question_no, word, correct, reaction_time, unknown_flag):

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO results
                    (subject_id, session_id, question_no, word, correct, reaction_time, unknown_flag)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    subject_id,
                    session_id,
                    question_no,
                    word,
                    correct,
                    reaction_time,
                    unknown_flag
                ))
                conn.commit()
    except Exception as e:
        print("DB ERROR:", e)


# -----------------------
# ANSWER
# -----------------------
@app.route("/answer", methods=["POST"])
def answer():

    if "questions" not in session:
        return redirect("/")

    idx = session["index"]
    questions = session["questions"]

    if idx >= len(questions):
        return redirect("/finish")

    selected = request.form.get("answer", "分からない")
    q = questions[idx]

    reaction_time = round(time.time() - session["start_time"], 3)

    if selected == "分からない":
        correct = 0
        unknown = 1
    else:
        correct = int(selected == q["japanese"])
        unknown = 0

    save_result(
        session["subject_id"],
        session["session_id"],
        idx + 1,
        q["english"],
        correct,
        reaction_time,
        unknown
    )

    session["index"] += 1

    return redirect("/question")


# -----------------------
# FINISH（DBのみ）
# -----------------------
@app.route("/finish")
def finish():

    session.clear()

    return render_template("finish.html")