from flask import Flask, render_template, session, request, redirect, url_for, jsonify
import json, os, requests, time, difflib

app = Flask(__name__)
app.secret_key = "secret-key"

with open(os.path.join("data", "lessons.json"), encoding="utf‑8") as fp:
    LESSONS = json.load(fp)

for lang in LESSONS:
    for p in lang["phrases"]:
        alts = p.get("alt", [])
        p["accept"] = [p["native"].lower(), p["roman"].lower(), *[a.lower() for a in alts]]

LANG_CODE = {"ru": "ru", "fr": "fr", "ja": "ja"}
NUM_LANGS = len(LESSONS)
PHRASES_PER = len(LESSONS[0]["phrases"])
# AKEY = os.getenv("ASSEMBLYAI_API_KEY", "")
AKEY = "3cbfea56f7024ebdbc033eb5a3d45f89"

def transcribe(blob: bytes, lang: str) -> str:
    h = {"authorization": AKEY}
    up = requests.post("https://api.assemblyai.com/v2/upload", headers=h, data=blob).json()
    job = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json={"audio_url": up["upload_url"], "language_code": lang},
        headers=h,
    ).json()
    tid = job["id"]
    while True:
        poll = requests.get(f"https://api.assemblyai.com/v2/transcript/{tid}", headers=h).json()
        if poll["status"] in ("completed", "error"):
            return poll.get("text", "")
        time.sleep(2)


def fuzzy_ok(ans: str, options: list[str]) -> bool:
    for opt in options:
        if difflib.SequenceMatcher(None, ans, opt).ratio() >= 0.75:
            return True
    return False


@app.route("/")
def home():
    session.clear()
    return render_template("home.html", languages=LESSONS)


@app.route("/learn/<int:idx>")
def learn(idx: int):
    if idx < 0 or idx >= NUM_LANGS * PHRASES_PER:
        return redirect(url_for("home"))
    lang_i, phrase_i = divmod(idx, PHRASES_PER)
    lesson = LESSONS[lang_i]
    phrase = lesson["phrases"][phrase_i]
    next_idx = idx + 1 if idx + 1 < NUM_LANGS * PHRASES_PER else None
    return render_template("learn.html", lesson=lesson, phrase=phrase, next_idx=next_idx)


@app.route("/quiz/<int:q>")
def quiz(q: int):
    if q == 0:
        session["answers"] = []
    if q >= NUM_LANGS * PHRASES_PER:
        return redirect(url_for("quiz_result"))
    lang_i, phrase_i = divmod(q, PHRASES_PER)
    question = LESSONS[lang_i]["phrases"][phrase_i]
    return render_template(
        "quiz.html",
        q=q,
        question=question,
        lang=LESSONS[lang_i],
        total=NUM_LANGS * PHRASES_PER,
        section_num=lang_i + 1,
        question_in_section=phrase_i + 1,
        section_start=phrase_i == 0,
    )


@app.route("/quiz_submit", methods=["POST"])
def quiz_submit():
    q = int(request.form["q"])
    lang_i, phrase_i = divmod(q, PHRASES_PER)
    phrase = LESSONS[lang_i]["phrases"][phrase_i]
    typed = request.form.get("typed", "").strip().lower()
    if typed:
        heard = typed
    else:
        heard = transcribe(request.files["audio"].read(), LANG_CODE[LESSONS[lang_i]["id"]]).lower()
    correct = fuzzy_ok(heard, phrase["accept"])
    session.setdefault("answers", []).append({"q": q, "user": heard, "correct": correct})
    session.modified = True
    return jsonify(correct=correct, heard=heard)


@app.route("/quiz_result")
def quiz_result():
    ans = session.get("answers", [])
    score = sum(a["correct"] for a in ans)
    total = NUM_LANGS * PHRASES_PER
    return render_template("result.html", score=score, total=total)


if __name__ == "__main__":
    app.run(debug=True)
