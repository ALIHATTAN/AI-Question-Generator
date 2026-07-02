import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def empty_questions():
    return {
        "true_false": [],
        "mcq": [],
        "short_answer": []
    }


def clean_json_response(text):
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    return text


def remove_table_of_contents(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\.{3,}", " ", text)

    bad_words = [
        "الفهرس",
        "المحتويات",
        "جدول المحتويات",
        "اسم الملف",
        "رقم الصفحة",
        "صفحة"
    ]

    for word in bad_words:
        text = text.replace(word, " ")

    text = re.sub(r"\s+", " ", text).strip()
    return text


def call_ai(prompt, temperature=0.1):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }

    response = requests.post(API_URL, headers=headers, json=data, timeout=90)
    response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    json_text = clean_json_response(content)
    return json.loads(json_text)


def generate_initial_questions(lesson_text):
    prompt = f"""
أنت معلم جامعي دقيق ومختص في إعداد الاختبارات.

اقرأ النص التعليمي التالي، ثم أنشئ اختبارًا من محتوى الدرس فقط.

المطلوب:
- 5 أسئلة صح أو خطأ
- 5 أسئلة اختيار من متعدد
- 3 أسئلة قصيرة

الشروط:
- لا تستخدم الفهرس.
- لا تستخدم أرقام الصفحات.
- لا تستخدم اسم الأستاذ أو عناوين الملف.
- جميع الأسئلة والإجابات باللغة العربية فقط.
- الأسئلة يجب أن تقيس الفهم وليس النسخ الحرفي.
- لا تجعل كل أسئلة الصح والخطأ إجابتها صح.
- أسئلة الاختيار من متعدد يجب أن تحتوي على 4 خيارات.
- يجب أن يكون هناك خيار صحيح واحد فقط.
- الإجابة الصحيحة يجب أن تكون موجودة حرفيًا ضمن الخيارات.
- الأسئلة القصيرة تكون واضحة وإجابتها النموذجية مختصرة.

أخرج JSON فقط بهذا الشكل:

{{
  "true_false": [
    {{
      "question": "عبارة صح أو خطأ",
      "answer": "صح"
    }}
  ],
  "mcq": [
    {{
      "question": "نص السؤال",
      "options": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"],
      "answer": "خيار 1"
    }}
  ],
  "short_answer": [
    {{
      "question": "نص السؤال",
      "answer": "الإجابة النموذجية"
    }}
  ]
}}

النص:
{lesson_text[:12000]}
"""

    return call_ai(prompt, temperature=0.1)


def review_questions(lesson_text, questions):
    prompt = f"""
أنت مراجع اختبارات أكاديمي دقيق.

سأعطيك نصًا تعليميًا وأسئلة تم توليدها منه.
راجع الأسئلة وصحح أي خطأ فيها.

المطلوب منك:
- تحقق أن كل سؤال مبني على النص.
- احذف أو عدّل أي سؤال مأخوذ من الفهرس.
- صحح إجابات صح أو خطأ إذا كانت خاطئة.
- تأكد أن أسئلة صح أو خطأ فيها تنوع بين "صح" و"خطأ".
- تأكد أن كل سؤال اختيار من متعدد له 4 خيارات.
- تأكد أن الإجابة الصحيحة موجودة حرفيًا ضمن الخيارات.
- تأكد أنه لا يوجد أكثر من خيار صحيح في MCQ.
- عدّل الخيارات الضعيفة أو الواضحة جدًا.
- اجعل الأسئلة عربية واضحة ودقيقة.
- لا تضف شرحًا خارج JSON.

أعد إخراج JSON النهائي فقط بنفس الصيغة:

{{
  "true_false": [
    {{
      "question": "عبارة صح أو خطأ",
      "answer": "صح"
    }}
  ],
  "mcq": [
    {{
      "question": "نص السؤال",
      "options": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"],
      "answer": "خيار 1"
    }}
  ],
  "short_answer": [
    {{
      "question": "نص السؤال",
      "answer": "الإجابة النموذجية"
    }}
  ]
}}

النص التعليمي:
{lesson_text[:12000]}

الأسئلة المراد مراجعتها:
{json.dumps(questions, ensure_ascii=False)}
"""

    return call_ai(prompt, temperature=0)


def validate_questions(questions):
    questions.setdefault("true_false", [])
    questions.setdefault("mcq", [])
    questions.setdefault("short_answer", [])

    clean_tf = []
    for q in questions["true_false"]:
        question = q.get("question", "").strip()
        answer = q.get("answer", "").strip()

        if question and answer in ["صح", "خطأ"]:
            clean_tf.append({
                "question": question,
                "answer": answer
            })

    clean_mcq = []
    for q in questions["mcq"]:
        question = q.get("question", "").strip()
        options = q.get("options", [])
        answer = q.get("answer", "").strip()

        if not isinstance(options, list):
            continue

        options = [str(opt).strip() for opt in options if str(opt).strip()]

        if len(options) == 4 and answer in options and question:
            clean_mcq.append({
                "question": question,
                "options": options,
                "answer": answer
            })

    clean_short = []
    for q in questions["short_answer"]:
        question = q.get("question", "").strip()
        answer = q.get("answer", "").strip()

        if question and answer:
            clean_short.append({
                "question": question,
                "answer": answer
            })

    return {
        "true_false": clean_tf[:5],
        "mcq": clean_mcq[:5],
        "short_answer": clean_short[:3]
    }


def generate_questions(text):
    lesson_text = remove_table_of_contents(text)

    if not lesson_text or len(lesson_text) < 150:
        return empty_questions()

    try:
        initial_questions = generate_initial_questions(lesson_text)

        reviewed_questions = review_questions(
            lesson_text,
            initial_questions
        )

        final_questions = validate_questions(reviewed_questions)

        return final_questions

    except Exception as error:
        print("OpenRouter Question Generation Error:", error)
        return empty_questions()