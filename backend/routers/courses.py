from fastapi import APIRouter, Depends, HTTPException
from backend.database import db_dependency
from backend import schemas
from backend.auth import get_current_user, require_role

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("")
def list_courses(conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.*, u.name AS instructor_name
            FROM courses c
            JOIN users u ON c.instructor_id = u.id
            WHERE c.is_published = 1
        """)
        courses = cur.fetchall()

        result = []
        for c in courses:
            # Enrolled?
            cur.execute(
                "SELECT id FROM enrollments WHERE user_id=%s AND course_id=%s",
                (user_id, c["id"])
            )
            enrolled = cur.fetchone() is not None

            # Lesson count & completed count
            cur.execute("""
                SELECT l.id FROM lessons l
                JOIN modules m ON l.module_id = m.id
                WHERE m.course_id = %s
            """, (c["id"],))
            lesson_ids = [r["id"] for r in cur.fetchall()]
            total = len(lesson_ids)

            completed = 0
            if lesson_ids:
                fmt = ",".join(["%s"] * len(lesson_ids))
                cur.execute(f"""
                    SELECT COUNT(*) AS cnt FROM lesson_progress
                    WHERE user_id=%s AND completed=1 AND lesson_id IN ({fmt})
                """, (user_id, *lesson_ids))
                completed = cur.fetchone()["cnt"]

            progress = round(completed / total * 100, 1) if total else 0

            result.append({
                **{k: v for k, v in c.items() if k != "password_hash"},
                "enrolled": enrolled,
                "progress": progress,
                "lesson_count": total,
            })
    return result


@router.get("/{course_id}")
def get_course(course_id: int, conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.*, u.name AS instructor_name
            FROM courses c JOIN users u ON c.instructor_id = u.id
            WHERE c.id = %s
        """, (course_id,))
        course = cur.fetchone()
        if not course:
            raise HTTPException(404, "Course not found")

        cur.execute(
            "SELECT id FROM enrollments WHERE user_id=%s AND course_id=%s",
            (user_id, course_id)
        )
        enrolled = cur.fetchone() is not None

        cur.execute(
            "SELECT * FROM modules WHERE course_id=%s ORDER BY order_num",
            (course_id,)
        )
        modules = cur.fetchall()

        modules_data = []
        for mod in modules:
            cur.execute(
                "SELECT * FROM lessons WHERE module_id=%s ORDER BY order_num",
                (mod["id"],)
            )
            lessons = cur.fetchall()
            lessons_data = []
            for lesson in lessons:
                cur.execute(
                    "SELECT completed FROM lesson_progress WHERE user_id=%s AND lesson_id=%s",
                    (user_id, lesson["id"])
                )
                lp = cur.fetchone()
                lessons_data.append({
                    "id": lesson["id"], "title": lesson["title"],
                    "video_url": lesson["video_url"], "order_num": lesson["order_num"],
                    "xp_reward": lesson["xp_reward"],
                    "completed": bool(lp["completed"]) if lp else False,
                })
            modules_data.append({
                "id": mod["id"], "title": mod["title"],
                "order_num": mod["order_num"], "lessons": lessons_data
            })

    return {
        "id": course["id"], "title": course["title"],
        "description": course["description"], "thumbnail_url": course["thumbnail_url"],
        "difficulty": course["difficulty"], "instructor_name": course["instructor_name"],
        "modules": modules_data, "enrolled": enrolled,
    }


@router.post("/enroll/{course_id}")
def enroll(course_id: int, conn=Depends(db_dependency), current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    with conn.cursor() as cur:
        cur.execute("SELECT id, is_published FROM courses WHERE id=%s", (course_id,))
        course = cur.fetchone()
        if not course or not course["is_published"]:
            raise HTTPException(404, "Course not found")

        cur.execute(
            "SELECT id FROM enrollments WHERE user_id=%s AND course_id=%s",
            (user_id, course_id)
        )
        if cur.fetchone():
            raise HTTPException(400, "Already enrolled")

        cur.execute(
            "INSERT INTO enrollments (user_id, course_id) VALUES (%s, %s)",
            (user_id, course_id)
        )
        conn.commit()
    return {"message": "Enrolled successfully"}


@router.post("")
def create_course(
    data: schemas.CourseCreate,
    conn=Depends(db_dependency),
    current_user=Depends(require_role("instructor", "admin"))
):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO courses (title, description, thumbnail_url, difficulty, instructor_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.title, data.description, data.thumbnail_url,
              data.difficulty or "beginner", current_user["id"]))
        course_id = cur.lastrowid
        conn.commit()
    return {"id": course_id, "title": data.title}


@router.patch("/{course_id}/publish")
def publish_course(
    course_id: int,
    conn=Depends(db_dependency),
    current_user=Depends(require_role("instructor", "admin"))
):
    with conn.cursor() as cur:
        cur.execute("SELECT id, is_published FROM courses WHERE id=%s", (course_id,))
        course = cur.fetchone()
        if not course:
            raise HTTPException(404, "Not found")
        new_state = not bool(course["is_published"])
        cur.execute(
            "UPDATE courses SET is_published=%s WHERE id=%s",
            (new_state, course_id)
        )
        conn.commit()
    return {"is_published": new_state}


@router.post("/{course_id}/modules")
def add_module(
    course_id: int, data: schemas.ModuleCreate,
    conn=Depends(db_dependency),
    current_user=Depends(require_role("instructor", "admin"))
):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO modules (course_id, title, order_num) VALUES (%s, %s, %s)",
            (course_id, data.title, data.order_num or 0)
        )
        mod_id = cur.lastrowid
        conn.commit()
    return {"id": mod_id, "title": data.title}


@router.post("/modules/{module_id}/lessons")
def add_lesson(
    module_id: int, data: schemas.LessonCreate,
    conn=Depends(db_dependency),
    current_user=Depends(require_role("instructor", "admin"))
):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO lessons (module_id, title, content, video_url, order_num, xp_reward)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (module_id, data.title, data.content, data.video_url,
              data.order_num or 0, data.xp_reward or 10))
        lesson_id = cur.lastrowid
        conn.commit()
    return {"id": lesson_id, "title": data.title}
@router.get("/admin/all")
def admin_list_courses(
    conn=Depends(db_dependency),
    current_user=Depends(require_role("instructor", "admin"))
):
    """Return ALL courses (published + draft) for admin panel."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.*, u.name AS instructor_name
            FROM courses c
            JOIN users u ON c.instructor_id = u.id
            WHERE c.instructor_id = %s OR %s = 'admin'
            ORDER BY c.created_at DESC
        """, (current_user["id"], current_user["role"]))
        courses = cur.fetchall()

        result = []
        for c in courses:
            cur.execute("""
                SELECT COUNT(*) as cnt FROM lessons l
                JOIN modules m ON l.module_id = m.id
                WHERE m.course_id = %s
            """, (c["id"],))
            lesson_count = cur.fetchone()["cnt"]

            result.append({
                "id":              c["id"],
                "title":           c["title"],
                "description":     c["description"],
                "difficulty":      c["difficulty"],
                "is_published":    bool(c["is_published"]),
                "instructor_name": c["instructor_name"],
                "lesson_count":    lesson_count,
                "created_at":      str(c["created_at"]),
            })
    return result