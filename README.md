# Adaptive Learning Platform

## Tech Stack
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Backend**: Python FastAPI
- **Database**: MySQL

## Project Structure
```
adaptive-learning-platform/
├── frontend/
│   ├── index.html          # Landing / Login page
│   ├── dashboard.html      # Student dashboard
│   ├── course.html         # Course / lesson view
│   ├── quiz.html           # Adaptive quiz
│   ├── progress.html       # Progress & analytics
│   ├── admin.html          # Admin/instructor panel
│   ├── css/
│   │   ├── main.css
│   │   ├── dashboard.css
│   │   ├── course.css
│   │   ├── quiz.css
│   │   └── admin.css
│   └── js/
│       ├── api.js           # API client
│       ├── auth.js          # Auth helpers
│       ├── dashboard.js
│       ├── course.js
│       ├── quiz.js
│       ├── progress.js
│       └── admin.js
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── database.py          # MySQL connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # JWT auth
│   ├── adaptive.py          # Adaptive engine logic
│   └── routers/
│       ├── users.py
│       ├── courses.py
│       ├── lessons.py
│       ├── quizzes.py
│       └── progress.py
├── schema.sql               # MySQL schema
├── requirements.txt
└── .env.example
```

## Setup
1. Create MySQL database and run `schema.sql`
2. Copy `.env.example` to `.env` and fill in credentials
3. `pip install -r requirements.txt`
4. `uvicorn backend.main:app --reload`
5. Open `frontend/index.html` in browser

## Deploy On Vercel

This repository is configured to deploy both frontend and backend on Vercel:
- Static frontend from `frontend/`
- FastAPI backend as a Python serverless function from `api/index.py`

### Files Required
- `vercel.json` (routing and build config)
- `api/index.py` (exports FastAPI app)

### Database Requirement
Do not use local MySQL for production. Use a hosted MySQL database and run `schema.sql` on it before deploying.

### Vercel Environment Variables
Set these in Vercel Project Settings -> Environment Variables:
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

### Deploy Steps
1. Push this project to GitHub.
2. In Vercel, click **Add New -> Project** and import the GitHub repository.
3. Keep the root directory as repository root.
4. Add all environment variables listed above.
5. Deploy.

### Verify Deployment
- Open `/api/health` and confirm response is `{ "status": "ok" }`.
- Open `/` and test register/login flow.
