from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import traceback
import os

load_dotenv()

from backend.routers import users, courses, quizzes

app = FastAPI(
    title="Adaptive Learning Platform API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS must be added FIRST before anything else
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler — keeps CORS headers even on 500
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print("\n========== SERVER ERROR ==========")
    print(tb)
    print("==================================\n")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "trace": tb},
        headers={"Access-Control-Allow-Origin": "*"}
    )

app.include_router(users.router)
app.include_router(courses.router)
app.include_router(quizzes.quiz_router)
app.include_router(quizzes.progress_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/test-db")
def test_db():
    from backend.database import get_connection
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM users")
            result = cur.fetchone()
            cur.execute("SHOW TABLES")
            tables = [list(r.values())[0] for r in cur.fetchall()]
        conn.close()
        return {"status": "connected", "users": result["cnt"], "tables": tables}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}