# NEXORA Student Hub (starter project)

A beginner-friendly Flask + SQLite web app with a responsive HTML/CSS/JavaScript frontend, task API, learning resources API, and a public-page scraping demo.

## 1. Open in VS Code
1. Extract this ZIP.
2. In VS Code choose **File → Open Folder** and select `NEXORA-Student-Hub`.
3. Open **Terminal → New Terminal**.

## 2. Create a virtual environment (recommended)
Windows:
```powershell
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```
If `py` is not recognized, try `python -m venv .venv`.

## 3. Open the app
Visit http://127.0.0.1:5000 in your browser. Keep the terminal running while you use it. Press Ctrl+C in the terminal to stop the server.

## Included API endpoints
- `GET /api/health` — health check
- `GET /api/tasks` — list tasks
- `POST /api/tasks` — add task (`title`, `category`, `due_date`)
- `PATCH /api/tasks/<id>` — update completion (`done`)
- `DELETE /api/tasks/<id>` — delete task
- `GET /api/resources` — list learning resources
- `POST /api/resources` — add learning resource (`title`, `url`, `summary`)
- `GET /api/unstop` — live opportunities from Unstop (`category`: hackathons/competitions/internships/quizzes/scholarships, `search`)
- `POST /api/scrape` — extract public page details or structured Unstop opportunity data (`url`)

## Web scraping & Unstop integration notes
- **General Web Pages**: Extracts HTML title, headings, and preview text with SSRF guards.
- **Unstop Integration**: Automatically detects `unstop.com` links and retrieves structured metadata including host institution, registration deadlines, eligibility, required skills, and prizes.
- **One-Click Actions**: Opportunities can be added directly to the personal task planner or saved as a bookmarked learning resource.
- Use only public pages you are permitted to access. Respect the website's terms, robots.txt, rate limits, and copyright. This is an educational prototype.

## Next steps
For a real student portal, add authentication, user-specific task ownership, input validation, CSRF protection, deployment configuration, and tests before publishing.
