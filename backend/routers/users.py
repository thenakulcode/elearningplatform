from fastapi import APIRouter, Depends, HTTPException
from backend.database import db_dependency
from backend import schemas
from backend.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(data: schemas.RegisterIn, conn=Depends(db_dependency)):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        role = data.role if data.role in ("student", "instructor") else "student"
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (data.name, data.email, hash_password(data.password), role)
        )
        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO learner_profiles
                (user_id, skill_level, learning_speed, weak_topics, strong_topics,
                 preferred_type, total_xp, streak_days)
            VALUES (%s, 0.5, 1.0, '[]', '[]', 'reading', 0, 0)
        """, (user_id,))
        conn.commit()

    token = create_access_token({"sub": str(user_id)})
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user_id, "name": data.name, "email": data.email, "role": role}
    }


@router.post("/login")
def login(data: schemas.LoginIn, conn=Depends(db_dependency)):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (data.email,))
        user = cur.fetchone()

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user["id"])})
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user["id"], "name": user["name"],
                 "email": user["email"], "role": user["role"]}
    }


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"], "name": current_user["name"],
        "email": current_user["email"], "role": current_user["role"],
        "avatar_url": current_user.get("avatar_url"),
    }
