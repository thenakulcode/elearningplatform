from fastapi import APIRouter, Depends, HTTPException
from backend.database import db_dependency
from backend import schemas, adaptive
from backend.auth import get_current_user, require_role
from datetime import datetime
import json

quiz_router     = APIRouter(prefix="/api/quiz",     tags=["quiz"])
progress_router = APIRouter(prefix="/api/progress", tags=["progress"])


# ─── Quiz ─────────────────────────────────────────────────────────────────────

@quiz_router.get("/lesson/{lesson_id}")
def get_quiz(lesson_id: int, conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT skill_level FROM learner_profiles WHERE user_id=%s",
            (user_id,)
        )
        profile = cur.fetchone()
        skill = float(profile["skill_level"]) if profile else 0.5
        diff  = adaptive.select_question_difficulty(skill)

        # Try preferred difficulty first, fall back to all
        cur.execute(
            "SELECT * FROM questions WHERE lesson_id=%s AND difficulty=%s",
            (lesson_id, diff)
        )
        questions = cur.fetchall()
        if not questions:
            cur.execute("SELECT * FROM questions WHERE lesson_id=%s", (lesson_id,))
            questions = cur.fetchall()

    if not questions:
        raise HTTPException(404, "No questions found for this lesson")

    return [
        {
            "id": q["id"], "question": q["question"],
            "type": q["type"],
            "options": json.loads(q["options"]) if isinstance(q["options"], str) else (q["options"] or []),
            "difficulty": q["difficulty"],
        }
        for q in questions
    ]


@quiz_router.post("/submit")
def submit_quiz(data: schemas.QuizSubmit, conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id   = current_user["id"]
    lesson_id = data.lesson_id
    answers   = data.answers

    if not answers:
        raise HTTPException(400, "No answers provided")

    feedback  = []
    correct_c = 0

    with conn.cursor() as cur:
        for ans in answers:
            qid   = ans.get("question_id")
            given = ans.get("answer", "")
            cur.execute("SELECT * FROM questions WHERE id=%s", (qid,))
            q = cur.fetchone()
            if not q:
                continue
            is_correct = given.strip().lower() == q["correct"].strip().lower()
            if is_correct:
                correct_c += 1
            feedback.append({
                "question_id": qid,
                "question":    q["question"],
                "your_answer": given,
                "correct":     q["correct"],
                "is_correct":  is_correct,
                "explanation": q["explanation"],
            })  

        total = len(feedback)
        score = correct_c / total if total else 0

        cur.execute("""
            INSERT INTO quiz_attempts
                (user_id, lesson_id, score, total_q, correct_q, answers, attempted_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (user_id, lesson_id, score, total, correct_c, json.dumps(answers)))
        conn.commit()

    # Adaptive profile update
    result = adaptive.process_quiz_result(user_id, lesson_id, score, conn)
    badges = adaptive.check_and_award_badges(user_id, conn)

    # Find course_id for recommendation
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.course_id FROM lessons l
            JOIN modules m ON l.module_id = m.id
            WHERE l.id = %s
        """, (lesson_id,))
        row = cur.fetchone()
    course_id = row["course_id"] if row else None

    next_lesson = None
    if course_id:
        next_lesson = adaptive.recommend_next_lesson(user_id, course_id, conn)

    return {
        "score":              round(score * 100, 1),
        "total_q":            total,
        "correct_q":          correct_c,
        "xp_earned":          result["xp_earned"],
        "feedback":           feedback,
        "new_skill_level":    result["new_skill"],
        "badges_earned":      badges,
        "next_recommendation": next_lesson,
    }


@quiz_router.post("/questions")
def add_question(
    lesson_id: int,
    data: schemas.QuestionCreate,
    conn=Depends(db_dependency),
    current_user=Depends(require_role("instructor", "admin"))
):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO questions
                (lesson_id, question, type, options, correct, explanation, difficulty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            lesson_id, data.question, data.type or "mcq",
            json.dumps(data.options) if data.options else None,
            data.correct, data.explanation, data.difficulty or 1
        ))
        qid = cur.lastrowid
        conn.commit()
    return {"id": qid}


# ─── Progress ─────────────────────────────────────────────────────────────────

@progress_router.post("/lesson")
def update_progress(data: schemas.ProgressUpdate, conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, completed FROM lesson_progress WHERE user_id=%s AND lesson_id=%s",
            (user_id, data.lesson_id)
        )
        lp = cur.fetchone()

        if lp:
            if data.completed and not lp["completed"]:
                cur.execute("""
                    UPDATE lesson_progress
                    SET completed=1, completed_at=NOW(), time_spent_s=time_spent_s+%s
                    WHERE id=%s
                """, (data.time_spent_s or 0, lp["id"]))
            else:
                cur.execute(
                    "UPDATE lesson_progress SET time_spent_s=time_spent_s+%s WHERE id=%s",
                    (data.time_spent_s or 0, lp["id"])
                )
        else:
            cur.execute("""
                INSERT INTO lesson_progress
                    (user_id, lesson_id, completed, time_spent_s, completed_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user_id, data.lesson_id,
                1 if data.completed else 0,
                data.time_spent_s or 0,
                datetime.utcnow() if data.completed else None
            ))

        # Award lesson XP on first completion
        if data.completed:
            cur.execute("SELECT xp_reward FROM lessons WHERE id=%s", (data.lesson_id,))
            lesson = cur.fetchone()
            if lesson:
                cur.execute("""
                    UPDATE learner_profiles
                    SET total_xp = total_xp + %s
                    WHERE user_id = %s
                """, (lesson["xp_reward"], user_id))

        conn.commit()

    if data.completed:
        adaptive.check_and_award_badges(user_id, conn)

    return {"message": "Progress updated"}


@progress_router.get("/course/{course_id}")
def course_progress(course_id: int, conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM courses WHERE id=%s", (course_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Course not found")

        cur.execute("""
            SELECT l.id FROM lessons l
            JOIN modules m ON l.module_id = m.id
            WHERE m.course_id = %s
        """, (course_id,))
        lesson_ids = [r["id"] for r in cur.fetchall()]
        total = len(lesson_ids)

        lessons_status = []
        completed = 0
        for lid in lesson_ids:
            cur.execute(
                "SELECT completed FROM lesson_progress WHERE user_id=%s AND lesson_id=%s",
                (user_id, lid)
            )
            lp = cur.fetchone()
            done = bool(lp["completed"]) if lp else False
            if done:
                completed += 1
            lessons_status.append({"lesson_id": lid, "completed": done})

    return {
        "course_id":         course_id,
        "total_lessons":     total,
        "completed_lessons": completed,
        "percentage":        round(completed / total * 100, 1) if total else 0,
        "lessons":           lessons_status,
    }


@progress_router.get("/dashboard")
def dashboard_summary(conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM learner_profiles WHERE user_id=%s", (user_id,))
        profile = cur.fetchone()

        cur.execute("SELECT COUNT(*) AS cnt FROM enrollments WHERE user_id=%s", (user_id,))
        enrolled_count = cur.fetchone()["cnt"]

        cur.execute("""
            SELECT lesson_id, score, attempted_at FROM quiz_attempts
            WHERE user_id=%s ORDER BY attempted_at DESC LIMIT 5
        """, (user_id,))
        recent_quizzes = cur.fetchall()

        cur.execute("""
            SELECT ub.earned_at, b.name, b.icon
            FROM user_badges ub JOIN badges b ON ub.badge_id = b.id
            WHERE ub.user_id=%s
        """, (user_id,))
        badges = cur.fetchall()

    def parse_list(val):
        if not val:
            return []
        return json.loads(val) if isinstance(val, str) else (val or [])

    return {
        "profile": {
            "skill_level":   round(float(profile["skill_level"]) * 100, 1) if profile else 50,
            "total_xp":      profile["total_xp"] if profile else 0,
            "streak_days":   profile["streak_days"] if profile else 0,
            "weak_topics":   parse_list(profile["weak_topics"]) if profile else [],
            "strong_topics": parse_list(profile["strong_topics"]) if profile else [],
        },
        "enrolled_courses": enrolled_count,
        "recent_quiz_scores": [
            {
                "lesson_id": q["lesson_id"],
                "score":     round(float(q["score"]) * 100, 1),
                "date":      q["attempted_at"],
            }
            for q in recent_quizzes
        ],
        "badges": [
            {"name": b["name"], "icon": b["icon"], "earned_at": b["earned_at"]}
            for b in badges
        ],
    }
