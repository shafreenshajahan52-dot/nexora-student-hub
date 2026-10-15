from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse
import ipaddress
import socket
import re
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///nexora.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(40), default="Study")
    due_date = db.Column(db.String(30), default="")
    done = db.Column(db.Boolean, default=False)

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    summary = db.Column(db.String(500), default="")

with app.app_context():
    db.create_all()
    if Task.query.count() == 0:
        db.session.add_all([
            Task(title="Revise Data Science notes", category="Study", due_date="Today"),
            Task(title="Finish ML assignment", category="Assignment", due_date="Tomorrow"),
            Task(title="Prepare seminar slides", category="Project", due_date="This week"),
        ])
        db.session.commit()
    if Resource.query.count() == 0:
        db.session.add_all([
            Resource(title="Python documentation", url="https://docs.python.org/3/", summary="Official Python learning and reference material."),
            Resource(title="MDN Web Docs", url="https://developer.mozilla.org/", summary="HTML, CSS and JavaScript guides."),
            Resource(title="Flask documentation", url="https://flask.palletsprojects.com/", summary="Build web apps and APIs with Flask."),
        ])
        db.session.commit()

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "app": "NEXORA Student Hub"})

@app.get("/api/tasks")
def get_tasks():
    tasks = Task.query.order_by(Task.id.desc()).all()
    return jsonify([{
        "id": t.id, "title": t.title, "category": t.category,
        "due_date": t.due_date, "done": t.done
    } for t in tasks])

@app.post("/api/tasks")
def add_task():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "Study")).strip()[:40]
    due_date = str(data.get("due_date", "")).strip()[:30]
    if not title:
        return jsonify({"error": "Task title is required."}), 400
    task = Task(title=title[:160], category=category or "Study", due_date=due_date)
    db.session.add(task)
    db.session.commit()
    return jsonify({"id": task.id, "title": task.title, "category": task.category,
                    "due_date": task.due_date, "done": task.done}), 201

@app.patch("/api/tasks/<int:task_id>")
def toggle_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({"error": "Task not found."}), 404
    data = request.get_json(silent=True) or {}
    task.done = bool(data.get("done", not task.done))
    db.session.commit()
    return jsonify({"id": task.id, "done": task.done})

@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({"error": "Task not found."}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({"deleted": True})

@app.get("/api/resources")
def get_resources():
    resources = Resource.query.order_by(Resource.id.desc()).all()
    return jsonify([{"id": r.id, "title": r.title, "url": r.url, "summary": r.summary}
                    for r in resources])

@app.post("/api/resources")
def add_resource():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()[:200]
    url = str(data.get("url", "")).strip()[:1000]
    summary = str(data.get("summary", "")).strip()[:500]
    if not title or not url:
        return jsonify({"error": "Resource title and URL are required."}), 400
    resource = Resource(title=title, url=url, summary=summary)
    db.session.add(resource)
    db.session.commit()
    return jsonify({"id": resource.id, "title": resource.title, "url": resource.url, "summary": resource.summary}), 201

def format_unstop_opportunity(item):
    """Normalize Unstop opportunity JSON into clean student-friendly format."""
    if not isinstance(item, dict):
        return None
    org_data = item.get("organisation") or {}
    org_name = org_data.get("name", "Organization") if isinstance(org_data, dict) else str(org_data)
    org_logo = org_data.get("logoUrl2") or org_data.get("logoUrl") if isinstance(org_data, dict) else ""

    reg_req = item.get("regnRequirements") or {}
    remain_days = reg_req.get("remain_days") or reg_req.get("remainingDaysArray", {}).get("text") or "N/A"
    deadline = reg_req.get("end_regn_dt") or item.get("end_date") or ""
    status = reg_req.get("reg_status") or item.get("status") or "ACTIVE"

    pub_url = item.get("public_url") or item.get("seo_url") or ""
    if pub_url and not pub_url.startswith("http"):
        full_url = f"https://unstop.com/{pub_url.lstrip('/')}"
    else:
        full_url = pub_url or item.get("short_url") or "https://unstop.com"

    filters = [f.get("name") for f in (item.get("filters") or []) if isinstance(f, dict) and f.get("name")]
    skills = [s.get("skill") for s in (item.get("required_skills") or []) if isinstance(s, dict) and s.get("skill")]

    prize_descriptions = []
    for p in (item.get("prizes") or []):
        if isinstance(p, dict):
            rank = p.get("rank") or "Award"
            cash = p.get("cash")
            curr = p.get("currencyCode") or "INR"
            cert = " + Certificate" if p.get("certificate") else ""
            if cash:
                prize_descriptions.append(f"{rank}: {curr} {cash:,}{cert}")
            elif cert:
                prize_descriptions.append(f"{rank}: Certificate")

    return {
        "id": item.get("id"),
        "title": item.get("title", "Untitled Opportunity"),
        "organisation": org_name,
        "org_logo": org_logo,
        "url": full_url,
        "category": item.get("type") or item.get("subtype") or "Competition",
        "deadline": deadline,
        "remain_days": remain_days,
        "status": status,
        "filters": filters[:5],
        "skills": skills[:5],
        "prizes": prize_descriptions[:3],
        "views": item.get("viewsCount", 0),
        "registrations": item.get("registerCount", 0)
    }

def fetch_unstop_opportunities(opportunity_type="hackathons", search="", sort="latest", per_page=12):
    """Fetch opportunities directly from Unstop's public API."""
    params = {
        "opportunity": opportunity_type or "hackathons",
        "sort": sort or "latest",
        "per_page": min(per_page, 24)
    }
    if search:
        params["searchTerm"] = search
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        resp = requests.get(
            "https://unstop.com/api/public/opportunity/search-result",
            params=params,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            raw_items = data.get("data", [])
            formatted = [format_unstop_opportunity(i) for i in raw_items]
            return [f for f in formatted if f]
        return []
    except Exception as e:
        print("Unstop API query failed:", e)
        return []

def scrape_unstop_url(url):
    """Specialized scraper for Unstop URLs extracting structured opportunity data."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Extract ID from end of URL slug (e.g. build-with-bharat-50-codeverse-1770159)
    id_match = re.search(r"-(\d+)$", path)
    search_term = id_match.group(1) if id_match else path.split("/")[-1]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    api_url = "https://unstop.com/api/public/opportunity/search-result"
    try:
        resp = requests.get(api_url, params={"searchTerm": search_term, "per_page": 5}, headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("data", {}).get("data", [])
            if items:
                opp = format_unstop_opportunity(items[0])
                deadline_str = opp["deadline"][:10] if opp.get("deadline") else "Not specified"
                headings = [
                    f"Organization: {opp['organisation']}",
                    f"Status: {opp['remain_days']} ({opp['status']})",
                    f"Deadline: {deadline_str}"
                ]
                if opp["filters"]:
                    headings.append(f"Eligibility: {', '.join(opp['filters'])}")
                if opp["skills"]:
                    headings.append(f"Required Skills: {', '.join(opp['skills'])}")
                if opp["prizes"]:
                    headings.append(f"Prizes: {', '.join(opp['prizes'])}")

                summary_parts = [
                    f"{opp['title']} hosted by {opp['organisation']}.",
                    f"Registration status: {opp['remain_days']}.",
                    f"Eligibility: {', '.join(opp['filters']) if opp['filters'] else 'Open to all students'}."
                ]
                if opp["skills"]:
                    summary_parts.append(f"Key skills: {', '.join(opp['skills'])}.")
                if opp["prizes"]:
                    summary_parts.append(f"Awards: {', '.join(opp['prizes'])}.")

                return {
                    "url": opp["url"],
                    "title": f"Unstop: {opp['title']}",
                    "headings": headings,
                    "summary": " ".join(summary_parts)[:900],
                    "is_unstop": True,
                    "unstop_data": opp
                }
    except Exception as e:
        print("Unstop opportunity scrape error:", e)

    # Category fallback (e.g. /hackathons, /competitions, /internships)
    for cat in ["hackathons", "competitions", "internships", "jobs", "quizzes", "scholarships", "workshops"]:
        if cat in path.lower():
            items = fetch_unstop_opportunities(cat, per_page=6)
            if items:
                headings = [f"Top Live {cat.capitalize()} on Unstop:"] + [
                    f"{i['title']} · {i['organisation']} ({i['remain_days']})" for i in items[:4]
                ]
                return {
                    "url": url,
                    "title": f"Unstop - Live {cat.capitalize()}",
                    "headings": headings,
                    "summary": f"Browse top live {cat} from universities and companies on Unstop. Explore prizes, registration deadlines, and student eligibility criteria.",
                    "is_unstop": True,
                    "unstop_items": items
                }
    return None

@app.get("/api/unstop")
def get_unstop():
    """Endpoint for querying live Unstop opportunities by category and search keyword."""
    category = request.args.get("category", "hackathons").strip()
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "latest").strip()
    valid_categories = {"hackathons", "competitions", "internships", "jobs", "quizzes", "workshops", "scholarships"}
    if category not in valid_categories:
        category = "hackathons"
    opportunities = fetch_unstop_opportunities(category, search=search, sort=sort, per_page=12)
    return jsonify({
        "category": category,
        "search": search,
        "count": len(opportunities),
        "results": opportunities
    })

def is_public_http_url(url):
    """Basic guard: only HTTP(S) public hostnames; rejects localhost/private IPs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if host in ("localhost", "localhost.localdomain"):
            return False
        try:
            addresses = socket.getaddrinfo(host, None)
            for item in addresses:
                ip = ipaddress.ip_address(item[4][0])
                if not ip.is_global:
                    return False
        except (socket.gaierror, ValueError):
            return False
        return True
    except Exception:
        return False

@app.post("/api/scrape")
def scrape_public_page():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not is_public_http_url(url):
        return jsonify({"error": "Enter a valid public http/https URL. Local/private addresses are not allowed."}), 400

    parsed = urlparse(url)
    # Smart scraper for Unstop URLs
    if parsed.hostname and ("unstop.com" in parsed.hostname.lower()):
        unstop_result = scrape_unstop_url(url)
        if unstop_result:
            return jsonify(unstop_result)

    try:
        response = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "NEXORAStudentHub/1.0 (educational demo; contact site owner before frequent requests)"},
            allow_redirects=False
        )
        if response.is_redirect:
            return jsonify({"error": "This demo does not follow redirects. Open the page URL directly and try again."}), 400
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return jsonify({"error": "That URL did not return an HTML page."}), 415
        if len(response.content) > 2_000_000:
            return jsonify({"error": "Page is too large for this demo (limit 2 MB)."}), 413
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:8]]
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(" ", strip=True)]
        summary = " ".join(paragraphs[:3])[:900]
        result = {"url": url, "title": title[:200], "headings": headings, "summary": summary}
        return jsonify(result)
    except requests.Timeout:
        return jsonify({"error": "The website took too long to respond. Try again later."}), 504
    except requests.RequestException:
        return jsonify({"error": "Could not read this page. It may block automated requests or be unavailable."}), 502

if __name__ == "__main__":
    app.run(debug=True)
