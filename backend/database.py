import pymysql
import pymysql.cursors
from dotenv import load_dotenv
import os
from urllib.parse import urlparse

load_dotenv()


def _db_config_from_url(db_url: str):
    parsed = urlparse(db_url)
    if parsed.scheme not in ("mysql", "mysql+pymysql"):
        raise ValueError("DATABASE_URL must use mysql:// or mysql+pymysql://")

    db_name = (parsed.path or "").lstrip("/")
    if not db_name:
        raise ValueError("DATABASE_URL must include a database name in the path")

    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": db_name,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
        "connect_timeout": 10,
    }

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    DB_CONFIG = _db_config_from_url(DATABASE_URL)
else:
    DB_CONFIG = {
        "host":        os.getenv("DB_HOST", "localhost"),
        "port":        int(os.getenv("DB_PORT", 3306)),
        "user":        os.getenv("DB_USER", "root"),
        "password":    os.getenv("DB_PASSWORD", ""),
        "database":    os.getenv("DB_NAME", "adaptive_learning"),
        "charset":     "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit":  False,
        "connect_timeout": 10,
    }


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def db_dependency():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()