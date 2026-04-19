"""
Adaptive Learning Engine — Pure SQL (pymysql)
"""
from datetime import datetime, timedelta
from typing import Optional
import json


def update_skill_level(current: float, score: float, difficulty: int) -> float:
    diff_weight = {1: 0.5, 2: 1.0, 3: 1.5}.get(difficulty, 1.0)
    delta   = (score - 0.5) * 0.15 * diff_weight
    updated = max(0.0, min(1.0, current + delta))
    return round(updated, 4)


def select_question_difficulty(skill: float) -> int:
    if skill < 0.35:
        return 1
    if skill < 0.70:
        return 2
    return 3


def recommend_next_lesson(user_id: int, course_id: int, conn) -> Optional[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT weak_topics FROM learner_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()
        weak = []
        if profile and profile["weak_topics"]:
            try:
                raw = profile["weak_topics"]
                weak = json.loads(raw) if isinstance(raw, str) else (raw or [])
            except Exception:
                weak = []

        cur.execute("""
            SELECT l.id, l.title
            FROM lessons l
            JOIN modules m ON l.module_id = m.id
            WHERE m.course_id = %s
            ORDER BY m.order_num, l.order_num
        """, (course_id,))
        lessons = cur.fetchall()

        cur.execute("""
            SELECT lesson_id FROM lesson_progress
            WHERE user_id = %s AND completed = 1
        """, (user_id,))
        completed_ids = {row["lesson_id"] for row in cur.fetchall()}

    for lesson in lessons:
        if lesson["id"] not in completed_ids:
            if any(w.lower() in lesson["title"].lower() for w in weak):
                return {"id": lesson["id"], "title": lesson["title"], "reason": "Strengthen weak area"}

    for lesson in lessons:
        if lesson["id"] not in completed_ids:
            return {"id": lesson["id"], "title": lesson["title"], "reason": "Continue progress"}

    return None


def process_quiz_result(user_id: int, lesson_id: int, score: float, conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT title, xp_reward FROM lessons WHERE id = %s", (lesson_id,))
        lesson = cur.fetchone()
        lesson_title = lesson["title"] if lesson else "unknown"
        xp_reward    = lesson["xp_reward"] if lesson else 20

        cur.execute("SELECT * FROM learner_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()

        if not profile:
            cur.execute("""
                INSERT INTO learner_profiles
                    (user_id, skill_level, learning_speed, weak_topics, strong_topics,
                     preferred_type, total_xp, streak_days, last_active)
                VALUES (%s, 0.5, 1.0, '[]', '[]', 'reading', 0, 0, NOW())
            """, (user_id,))
            conn.commit()
            cur.execute("SELECT * FROM learner_profiles WHERE user_id = %s", (user_id,))
            profile = cur.fetchone()

        def parse_list(val):
            if not val:
                return []
            return json.loads(val) if isinstance(val, str) else (val or [])

        new_skill = update_skill_level(float(profile["skill_level"]), score, 2)
        weak      = parse_list(profile["weak_topics"])
        strong    = parse_list(profile["strong_topics"])

        if score < 0.6:
            if lesson_title not in weak:
                weak.append(lesson_title)
            weak = weak[:10]
        else:
            if lesson_title not in strong:
                strong.append(lesson_title)
            strong = strong[:20]

        xp_earned = int(score * xp_reward)
        new_xp    = (profile["total_xp"] or 0) + xp_earned

        streak = profile["streak_days"] or 0
        last   = profile["last_active"]
        today  = datetime.utcnow().date()
        if last:
            last_date = last.date() if hasattr(last, "date") else last
            if last_date == today - timedelta(days=1):
                streak += 1
            elif last_date != today:
                streak = 1
        else:
            streak = 1

        cur.execute("""
            UPDATE learner_profiles
            SET skill_level=%s, weak_topics=%s, strong_topics=%s,
                total_xp=%s, streak_days=%s, last_active=NOW()
            WHERE user_id=%s
        """, (new_skill, json.dumps(weak), json.dumps(strong), new_xp, streak, user_id))
        conn.commit()

    return {"xp_earned": xp_earned, "new_skill": new_skill}


def check_and_award_badges(user_id: int, conn) -> list:
    awarded = []
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM learner_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()
        if not profile:
            return []

        cur.execute("SELECT badge_id FROM user_badges WHERE user_id = %s", (user_id,))
        existing_ids = {row["badge_id"] for row in cur.fetchall()}

        cur.execute("SELECT * FROM badges")
        badges = cur.fetchall()

        cur.execute("""
            SELECT COUNT(*) AS cnt FROM lesson_progress
            WHERE user_id = %s AND completed = 1
        """, (user_id,))
        lessons_done = cur.fetchone()["cnt"]

        cur.execute("SELECT MAX(score) AS best FROM quiz_attempts WHERE user_id = %s", (user_id,))
        best_row   = cur.fetchone()
        best_score = float(best_row["best"]) if best_row and best_row["best"] is not None else 0

        for badge in badges:
            if badge["id"] in existing_ids:
                continue
            cond   = badge["condition_text"] or ""
            earned = False
            if "lessons_completed=1" in cond and lessons_done >= 1:             earned = True
            if "perfect_quiz=1"      in cond and best_score >= 1.0:             earned = True
            if "daily_lessons=5"     in cond and lessons_done >= 5:             earned = True
            if "streak=7"            in cond and (profile["streak_days"] or 0) >= 7: earned = True
            if "xp=500"              in cond and (profile["total_xp"] or 0) >= 500:  earned = True

            if earned:
                cur.execute(
                    "INSERT IGNORE INTO user_badges (user_id, badge_id) VALUES (%s, %s)",
                    (user_id, badge["id"])
                )
                awarded.append({"name": badge["name"], "icon": badge["icon"]})

        conn.commit()
    return awarded
