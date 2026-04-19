from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    name: str
    email: str        # plain str, avoid email validation issues
    password: str
    role: Optional[str] = "student"

class LoginIn(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


# ── Course ────────────────────────────────────────────────────────────────────
class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    difficulty: Optional[str] = "beginner"

class ModuleCreate(BaseModel):
    title: str
    order_num: Optional[int] = 0

class LessonCreate(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order_num: Optional[int] = 0
    xp_reward: Optional[int] = 10


# ── Question ──────────────────────────────────────────────────────────────────
class QuestionCreate(BaseModel):
    question: str
    type: Optional[str] = "mcq"
    options: Optional[List[str]] = None
    correct: str
    explanation: Optional[str] = None
    difficulty: Optional[int] = 1


# ── Quiz ──────────────────────────────────────────────────────────────────────
class QuizSubmit(BaseModel):
    lesson_id: int
    answers: List[dict]


# ── Progress ──────────────────────────────────────────────────────────────────
class ProgressUpdate(BaseModel):
    lesson_id: int
    time_spent_s: Optional[int] = 0
    completed: Optional[bool] = False


# ── Profile ───────────────────────────────────────────────────────────────────
class ProfileOut(BaseModel):
    skill_level: float
    learning_speed: float
    weak_topics: Optional[List[str]] = []
    strong_topics: Optional[List[str]] = []
    preferred_type: str
    total_xp: int
    streak_days: int