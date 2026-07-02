import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def normalize_answer(answer):
    if answer is None:
        return ""

    answer = str(answer).strip()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي",
        "ـ": "",
    }

    for old, new in replacements.items():
        answer = answer.replace(old, new)

    answer = answer.replace(".", "")
    answer = answer.replace("،", "")
    answer = answer.replace(",", "")
    answer = answer.replace("  ", " ")

    return answer.strip().lower()


def check_answer(user_answer, correct_answer):
    user = normalize_answer(user_answer)
    correct = normalize_answer(correct_answer)

    return user == correct


def grade_short_answer_ai(user_answer, model_answer, question_text):
    if not user_answer or len(user_answer.strip()) < 2:
        return False

    prompt = f"""
أنت مصحح أكاديمي دقيق.

السؤال:
{question_text}

الإجابة النموذجية:
{model_answer}

إجابة الطالب:
{user_answer}

قيّم إجابة الطالب حسب المعنى وليس حسب التطابق الحرفي.

القواعد:
- إذا كانت إجابة الطالب تحمل نفس المعنى الأساسي للإجابة النموذجية، اعتبرها صحيحة.
- إذا كانت الإجابة ناقصة جدًا أو عشوائية أو لا علاقة لها بالسؤال، اعتبرها خطأ.
- لا تكن متساهلًا مع الحروف العشوائية مثل a أو s أو d.
- أجب بكلمة واحدة فقط: صحيح أو خطأ
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=data,
            timeout=30
        )

        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"].strip()

        return content.startswith("صحيح")

    except Exception as error:
        print("Short Answer Grading Error:", error)
        return False


def analyze_performance(results):
    tf_correct = 0
    tf_total = 0

    mcq_correct = 0
    mcq_total = 0

    short_correct = 0
    short_total = 0

    for r in results:
        if r["type"] == "صح أو خطأ":
            tf_total += 1
            if r["is_correct"]:
                tf_correct += 1

        elif r["type"] == "اختيار من متعدد":
            mcq_total += 1
            if r["is_correct"]:
                mcq_correct += 1

        elif r["type"] == "سؤال قصير":
            short_total += 1
            if r["is_correct"]:
                short_correct += 1

    strengths = []
    weaknesses = []

    if tf_total:
        if tf_correct / tf_total >= 0.7:
            strengths.append("أداء جيد في أسئلة الصح والخطأ.")
        else:
            weaknesses.append("يحتاج إلى مراجعة أسئلة الصح والخطأ.")

    if mcq_total:
        if mcq_correct / mcq_total >= 0.7:
            strengths.append("أداء جيد في أسئلة الاختيار من متعدد.")
        else:
            weaknesses.append("يحتاج إلى مراجعة أسئلة الاختيار من متعدد.")

    if short_total:
        if short_correct / short_total >= 0.7:
            strengths.append("أداء جيد في الأسئلة القصيرة.")
        else:
            weaknesses.append("يحتاج إلى تحسين الإجابة على الأسئلة القصيرة.")

    if not strengths:
        strengths.append("لا توجد نقاط قوة واضحة حتى الآن.")

    if not weaknesses:
        weaknesses.append("لا توجد نقاط ضعف ملحوظة.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses
    }


def make_feedback(is_correct):
    if is_correct:
        return "إجابة صحيحة، أحسنت."
    else:
        return "الإجابة غير صحيحة، راجع هذا المفهوم في الدرس."


def generate_recommendations(percentage):
    recommendations = []

    if percentage >= 90:
        recommendations = [
            "أداء ممتاز، استمر بنفس المستوى.",
            "يمكنك الانتقال إلى الدرس التالي.",
            "حافظ على هذا الأداء."
        ]

    elif percentage >= 75:
        recommendations = [
            "أداؤك جيد جدًا.",
            "راجع الأسئلة التي أخطأت فيها.",
            "أعد الاختبار للحصول على درجة أعلى."
        ]

    elif percentage >= 60:
        recommendations = [
            "مستواك جيد.",
            "راجع المفاهيم التي أخطأت فيها.",
            "حاول إعادة الاختبار بعد المراجعة."
        ]

    else:
        recommendations = [
            "ينصح بإعادة دراسة الدرس.",
            "ركز على نقاط الضعف.",
            "أعد الاختبار بعد المراجعة."
        ]

    return recommendations


def calculate_statistics(results):
    stats = {
        "صح أو خطأ": {"correct": 0, "total": 0},
        "اختيار من متعدد": {"correct": 0, "total": 0},
        "سؤال قصير": {"correct": 0, "total": 0},
    }

    for r in results:
        qtype = r["type"]

        if qtype in stats:
            stats[qtype]["total"] += 1

            if r["is_correct"]:
                stats[qtype]["correct"] += 1

    return stats


def grade_quiz(questions, user_answers):
    results = []
    score = 0
    total = 0

    # أولاً: تصحيح أسئلة صح أو خطأ
    for index, q in enumerate(questions.get("true_false", [])):
        question_text = q.get("question", "")
        correct_answer = q.get("answer", "")
        user_answer = user_answers.get(f"tf_{index}")

        is_correct = check_answer(user_answer, correct_answer)

        if is_correct:
            score += 1

        total += 1

        results.append({
            "type": "صح أو خطأ",
            "question": question_text,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "feedback": make_feedback(is_correct)
        })

    # ثانياً: تصحيح أسئلة الاختيار من متعدد
    for index, q in enumerate(questions.get("mcq", [])):
        question_text = q.get("question", "")
        correct_answer = q.get("answer", "")
        user_answer = user_answers.get(f"mcq_{index}")

        is_correct = check_answer(user_answer, correct_answer)

        if is_correct:
            score += 1

        total += 1

        results.append({
            "type": "اختيار من متعدد",
            "question": question_text,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "feedback": make_feedback(is_correct)
        })

    # ثالثاً: تصحيح الأسئلة القصيرة بالذكاء الاصطناعي
    for index, q in enumerate(questions.get("short_answer", [])):
        question_text = q.get("question", "")
        correct_answer = q.get("answer", "")
        user_answer = user_answers.get(f"short_{index}")

        is_correct = grade_short_answer_ai(
            user_answer,
            correct_answer,
            question_text
        )

        if is_correct:
            score += 1

        total += 1

        results.append({
            "type": "سؤال قصير",
            "question": question_text,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "feedback": make_feedback(is_correct)
        })

    percentage = round((score / total) * 100, 2) if total > 0 else 0

    analysis = analyze_performance(results)
    recommendations = generate_recommendations(percentage)
    statistics = calculate_statistics(results)
    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results,
        "analysis": analysis,
        "recommendations": recommendations,
        "statistics": statistics
    }