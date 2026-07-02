from flask import Flask, render_template, request, session, send_from_directory
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

from modules.file_reader import extract_text
from modules.text_processing import clean_text
from modules.mcq_generator import generate_questions
from modules.grading import grade_quiz
from modules.pdf_report import generate_pdf


app = Flask(__name__)
app.secret_key = "ai-question-generator-secret"


# مهم جدًا لـ Render
UPLOAD_FOLDER = "/tmp/uploads"
DATABASE_PATH = "/tmp/uploads/database/database.db"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)


@app.route("/")
def home():
    return render_template("home.html")


def save_result(score, total, percentage):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score INTEGER,
            total INTEGER,
            percentage REAL,
            created_at TEXT
        )
    """)

    cursor.execute("""
        INSERT INTO results (score, total, percentage, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        score,
        total,
        percentage,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "لم يتم إرسال ملف"

    file = request.files["file"]

    if file.filename == "":
        return "لم يتم اختيار ملف"

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    file.save(file_path)

    if not os.path.exists(file_path):
        return "حدث خطأ أثناء حفظ الملف على السيرفر"

    extracted_text = extract_text(file_path)
    cleaned_text = clean_text(extracted_text)

    if not cleaned_text or len(cleaned_text.strip()) < 50:
        return "لم يتم استخراج نص واضح من الملف. جرّب ملفًا آخر."

    questions = generate_questions(cleaned_text)

    if not questions:
        return "لم يتم توليد أسئلة من الملف."

    session["questions"] = questions

    return render_template("quiz.html", questions=questions)


@app.route("/submit", methods=["POST"])
def submit():
    questions = session.get("questions")

    if not questions:
        return "لم يتم العثور على بيانات الاختبار."

    result = grade_quiz(questions, request.form)

    save_result(
        result["score"],
        result["total"],
        result["percentage"]
    )

    pdf_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        "Quiz_Report.pdf"
    )

    generate_pdf(result, pdf_path)

    return render_template(
        "results.html",
        result=result
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


if __name__ == "__main__":
    app.run(debug=True)