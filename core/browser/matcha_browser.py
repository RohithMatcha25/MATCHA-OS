"""
MATCHA Browser Agent
Controls real browsers — logs in, fills forms, clicks buttons, does anything.
Uses Playwright (headless or visible). All data stored locally. Nothing sent outside.
"""

import os, json, time, pathlib, sqlite3, threading
from datetime import datetime
from typing import Optional

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CREDS_DB = os.path.join(BASE, "core", "memory", "credentials.db")
SESSIONS_DIR = os.path.join(BASE, "core", "memory", "browser_sessions")


class MatchaBrowserAgent:
    def __init__(self):
        pathlib.Path(os.path.dirname(CREDS_DB)).mkdir(parents=True, exist_ok=True)
        pathlib.Path(SESSIONS_DIR).mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._playwright = None
        self._browser = None
        self._page = None
        self._active_task = None
        print("[MATCHA Browser] Browser agent ready.")

    def _init_db(self):
        with sqlite3.connect(CREDS_DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS credentials (
                service TEXT PRIMARY KEY,
                username TEXT,
                password TEXT,
                extra TEXT,
                ts TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                service TEXT,
                task TEXT,
                status TEXT,
                result TEXT,
                ts TEXT
            )""")

    # ── Credential Management ─────────────────────────────────────────────────

    def store_credentials(self, service: str, username: str, password: str) -> str:
        """Store credentials locally — never sent outside machine."""
        with sqlite3.connect(CREDS_DB) as c:
            c.execute("""INSERT OR REPLACE INTO credentials (service, username, password, ts)
                         VALUES (?, ?, ?, ?)""",
                      (service.lower(), username, password, datetime.now().isoformat()))
        return f"Credentials for {service} saved locally on your machine."

    def get_credentials(self, service: str) -> Optional[dict]:
        with sqlite3.connect(CREDS_DB) as c:
            row = c.execute(
                "SELECT username, password, extra FROM credentials WHERE service=?",
                (service.lower(),)
            ).fetchone()
        if row:
            return {"username": row[0], "password": row[1], "extra": row[2]}
        return None

    def list_saved_services(self) -> list:
        with sqlite3.connect(CREDS_DB) as c:
            rows = c.execute("SELECT service FROM credentials").fetchall()
        return [r[0] for r in rows]

    # ── Browser Control ───────────────────────────────────────────────────────

    def _get_playwright(self):
        if self._playwright is None:
            try:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
                self._playwright = self._pw
            except ImportError:
                return None
        return self._playwright

    def _launch_browser(self, headless=False):
        pw = self._get_playwright()
        if not pw:
            return None
        try:
            self._browser = pw.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            ctx = self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self._page = ctx.new_page()
            return self._page
        except Exception as e:
            print(f"[MATCHA Browser] Launch error: {e}")
            return None

    def _close_browser(self):
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
                self._page = None
        except Exception:
            pass

    # ── High-Level Tasks ──────────────────────────────────────────────────────

    def open_website(self, url: str, service_name: str = "") -> str:
        """Open a website in a visible browser window."""
        try:
            import subprocess, sys
            # Use the system browser — just open the URL
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/c", "start", url])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            return f"__OPEN_URL__{url}__LABEL__{service_name or url}"
        except Exception as e:
            return f"Could not open browser: {e}"

    def login_and_act(self, service: str, task: str, brain=None) -> str:
        """
        Login to a service and perform a task.
        Asks for credentials if not stored.
        """
        creds = self.get_credentials(service)
        if not creds:
            return (
                f"__NEED_CREDS__{service}__TASK__{task}\n"
                f"I need your {service} credentials to do this. "
                f"Say: 'my {service} username is X and password is Y' and I'll save them locally and proceed."
            )

        # Log the task
        with sqlite3.connect(CREDS_DB) as c:
            c.execute(
                "INSERT INTO tasks (service, task, status, ts) VALUES (?, ?, 'running', ?)",
                (service, task, datetime.now().isoformat())
            )

        # Run in background thread
        thread = threading.Thread(
            target=self._run_task,
            args=(service, task, creds, brain),
            daemon=True
        )
        thread.start()

        return f"Starting task on {service}: {task}\n\nI'll update you when it's done. This runs in the background."

    def _run_task(self, service: str, task: str, creds: dict, brain):
        """Background execution of browser task."""
        try:
            page = self._launch_browser(headless=False)  # Visible so user can see
            if not page:
                self._update_task(service, task, "failed", "Could not launch browser")
                return

            # Route to service handler
            result = "Task completed."
            sl = service.lower()

            if "linkedin" in sl:
                result = self._linkedin_task(page, task, creds, brain)
            elif "instagram" in sl or "insta" in sl:
                result = self._instagram_task(page, task, creds, brain)
            elif "gmail" in sl or "email" in sl:
                result = self._gmail_task(page, task, creds, brain)
            elif "amazon" in sl:
                result = self._amazon_task(page, task, creds, brain)
            elif "ubereats" in sl or "deliveroo" in sl or "just eat" in sl or "food" in sl:
                result = self._food_task(page, task, creds, brain)
            elif "github" in sl:
                result = self._github_task(page, task, creds, brain)
            else:
                result = self._generic_task(page, service, task, creds, brain)

            self._update_task(service, task, "done", result)
        except Exception as e:
            self._update_task(service, task, "failed", str(e))
        finally:
            self._close_browser()

    def _update_task(self, service: str, task: str, status: str, result: str):
        with sqlite3.connect(CREDS_DB) as c:
            c.execute(
                "UPDATE tasks SET status=?, result=? WHERE service=? AND task=? AND status='running'",
                (status, result, service, task)
            )

    # ── Service-specific handlers ─────────────────────────────────────────────

    def _linkedin_task(self, page, task: str, creds: dict, brain) -> str:
        try:
            page.goto("https://www.linkedin.com/login", timeout=15000)
            page.wait_for_selector("#username", timeout=8000)
            page.fill("#username", creds["username"])
            page.fill("#password", creds["password"])
            page.click('[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=15000)

            if "jobs" in task.lower() or "apply" in task.lower():
                return self._linkedin_jobs(page, task, brain)
            elif "profile" in task.lower() or "update" in task.lower():
                return self._linkedin_profile(page, task, brain)
            elif "message" in task.lower():
                return self._linkedin_messages(page, task, brain)
            return "Logged into LinkedIn. What would you like me to do next?"
        except Exception as e:
            return f"LinkedIn task failed: {e}"

    def _linkedin_jobs(self, page, task: str, brain) -> str:
        try:
            page.goto("https://www.linkedin.com/jobs/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)

            # Extract job query from task
            query = "software engineer"
            if brain:
                q = brain.think(f"Extract the job title/role from this task: '{task}'. Return only the job title, nothing else.")
                if q and len(q) < 50:
                    query = q.strip()

            # Search for jobs
            search = page.query_selector(".jobs-search-box__text-input")
            if search:
                search.fill(query)
                search.press("Enter")
                page.wait_for_load_state("networkidle", timeout=10000)

                # Get job listings
                jobs = page.query_selector_all(".job-card-container")
                job_list = []
                for j in jobs[:10]:
                    try:
                        title = j.query_selector(".job-card-list__title")
                        company = j.query_selector(".job-card-container__company-name")
                        if title:
                            job_list.append(f"• {title.inner_text().strip()} at {company.inner_text().strip() if company else 'Unknown'}")
                    except Exception:
                        pass

                return f"Found {len(jobs)} jobs for '{query}':\n" + "\n".join(job_list[:10])
            return "Opened LinkedIn Jobs."
        except Exception as e:
            return f"LinkedIn jobs error: {e}"

    def _linkedin_profile(self, page, task: str, brain) -> str:
        try:
            page.goto("https://www.linkedin.com/in/me/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            return "Opened your LinkedIn profile. Viewing now."
        except Exception as e:
            return f"Profile error: {e}"

    def _linkedin_messages(self, page, task: str, brain) -> str:
        try:
            page.goto("https://www.linkedin.com/messaging/", timeout=15000)
            return "Opened LinkedIn messages."
        except Exception as e:
            return f"Messages error: {e}"

    def _instagram_task(self, page, task: str, creds: dict, brain) -> str:
        try:
            page.goto("https://www.instagram.com/accounts/login/", timeout=15000)
            page.wait_for_selector('input[name="username"]', timeout=8000)
            page.fill('input[name="username"]', creds["username"])
            page.fill('input[name="password"]', creds["password"])
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=15000)
            return "Logged into Instagram. What would you like me to do?"
        except Exception as e:
            return f"Instagram task failed: {e}"

    def _gmail_task(self, page, task: str, creds: dict, brain) -> str:
        try:
            page.goto("https://mail.google.com", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            return "Opened Gmail."
        except Exception as e:
            return f"Gmail error: {e}"

    def _amazon_task(self, page, task: str, creds: dict, brain) -> str:
        try:
            page.goto("https://www.amazon.co.uk", timeout=15000)
            return "Opened Amazon."
        except Exception as e:
            return f"Amazon error: {e}"

    def _food_task(self, page, task: str, creds: dict, brain) -> str:
        try:
            page.goto("https://www.deliveroo.co.uk", timeout=15000)
            return "Opened Deliveroo."
        except Exception as e:
            return f"Food delivery error: {e}"

    def _github_task(self, page, task: str, creds: dict, brain) -> str:
        try:
            page.goto("https://github.com/login", timeout=15000)
            page.wait_for_selector("#login_field", timeout=8000)
            page.fill("#login_field", creds["username"])
            page.fill("#password", creds["password"])
            page.click('[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=15000)
            return "Logged into GitHub."
        except Exception as e:
            return f"GitHub error: {e}"

    def _generic_task(self, page, service: str, task: str, creds: dict, brain) -> str:
        """Generic login for any service."""
        try:
            # Ask brain for the login URL
            if brain:
                url = brain.think(
                    f"What is the login URL for {service}? Return only the URL, nothing else."
                )
                url = url.strip()
                if url.startswith("http"):
                    page.goto(url, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    return f"Opened {service} login page."
            return f"Could not find login page for {service}."
        except Exception as e:
            return f"Task error: {e}"

    # ── Task Status ───────────────────────────────────────────────────────────

    def get_task_status(self) -> str:
        with sqlite3.connect(CREDS_DB) as c:
            rows = c.execute(
                "SELECT service, task, status, result FROM tasks ORDER BY id DESC LIMIT 5"
            ).fetchall()
        if not rows:
            return "No tasks run yet."
        lines = []
        for r in rows:
            status_icon = "✅" if r[2] == "done" else "⏳" if r[2] == "running" else "❌"
            lines.append(f"{status_icon} **{r[0]}**: {r[1]}\n   → {r[3] or r[2]}")
        return "\n\n".join(lines)
