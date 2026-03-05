"""
MATCHA LinkedIn Agent v2
- Persistent browser session (stays open after login)
- Real job search + Easy Apply
- Profile viewing
- Status tracking
"""

import os, sqlite3, pathlib, threading, time, re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
JOBS_DB = os.path.join(BASE, "core", "memory", "jobs.db")

_agent_lock = threading.Lock()


class LinkedInAgent:
    def __init__(self):
        pathlib.Path(os.path.dirname(JOBS_DB)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._status = "idle"
        self._last_result = ""
        self._jobs_found = []
        print("[MATCHA LinkedIn] Agent ready.")

    def _init_db(self):
        with sqlite3.connect(JOBS_DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                title TEXT, company TEXT, location TEXT,
                url TEXT, status TEXT DEFAULT 'found', ts TEXT,
                UNIQUE(title, company)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY,
                title TEXT, company TEXT, status TEXT, ts TEXT
            )""")
        print("[LinkedIn DB] Initialised.")

    # ── Core browser helper ───────────────────────────────────────────────────

    def _launch(self, headless=False):
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=headless,
            slow_mo=50,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()
        return pw, browser, page

    def _login(self, page, username, password):
        """Returns True on success."""
        try:
            page.goto("https://www.linkedin.com/login", timeout=30000, wait_until="domcontentloaded")
            page.fill("#username", username, timeout=10000)
            page.fill("#password", password)
            page.click('button[type="submit"]')
            # Wait for redirect away from login
            page.wait_for_url(lambda u: "login" not in u and "signup" not in u, timeout=25000)

            if "checkpoint" in page.url or "challenge" in page.url:
                self._last_result = "⚠️ LinkedIn needs verification. Open LinkedIn in your browser, verify, then try again."
                self._status = "needs_verification"
                return False

            print(f"[LinkedIn] Logged in. URL: {page.url}")
            return True
        except Exception as e:
            self._last_result = f"Login failed: {e}"
            self._status = "login_failed"
            return False

    # ── Profile ───────────────────────────────────────────────────────────────

    def view_profile_task(self, username, password):
        """Run in background thread. Opens browser, logs in, stays on profile."""
        self._status = "running"
        pw = browser = None
        try:
            pw, browser, page = self._launch(headless=False)
            if not self._login(page, username, password):
                return

            page.goto("https://www.linkedin.com/in/me/", timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            name = self._text(page, "h1") or "your name"
            headline = self._text(page, ".text-body-medium.break-words") or "your headline"
            location = self._text(page, ".pb2 .text-body-small") or "your location"

            self._last_result = (
                f"✅ Profile loaded:\n"
                f"**Name:** {name}\n"
                f"**Headline:** {headline}\n"
                f"**Location:** {location}\n\n"
                f"Browser is still open. To update your profile, say what you want changed."
            )
            self._status = "done"

            # Keep browser open for 2 minutes so user can see/interact
            page.wait_for_timeout(120000)

        except Exception as e:
            self._last_result = f"Profile error: {e}"
            self._status = "error"
        finally:
            try:
                if browser: browser.close()
                if pw: pw.stop()
            except Exception:
                pass

    # ── Job Search ────────────────────────────────────────────────────────────

    def search_jobs_task(self, username, password, query="software engineer",
                         locations=None, stay_open=True):
        """Search jobs. Stays open after search so user can see results."""
        if locations is None:
            locations = ["United Kingdom"]
        self._status = "searching"
        self._jobs_found = []
        pw = browser = None
        try:
            pw, browser, page = self._launch(headless=False)
            if not self._login(page, username, password):
                return

            all_jobs = []
            for loc in locations[:3]:
                q = query.replace(" ", "%20")
                l = loc.replace(" ", "%20")
                url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location={l}&f_TPR=r604800"
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Scroll to load more
                for _ in range(3):
                    page.keyboard.press("End")
                    page.wait_for_timeout(1000)

                cards = page.query_selector_all(".job-card-container--clickable")
                for card in cards[:20]:
                    try:
                        title = self._text(card, ".job-card-list__title") or self._text(card, "h3")
                        company = self._text(card, ".job-card-container__primary-description") or self._text(card, "h4")
                        location_text = self._text(card, ".job-card-container__metadata-item")
                        link = card.query_selector("a")
                        href = link.get_attribute("href") if link else ""
                        if href and not href.startswith("http"):
                            href = "https://www.linkedin.com" + href

                        if title and title not in [j["title"] for j in all_jobs]:
                            all_jobs.append({
                                "title": title, "company": company or "Unknown",
                                "location": location_text or loc, "url": href
                            })
                    except Exception:
                        continue

            self._jobs_found = all_jobs

            # Save to DB
            with sqlite3.connect(JOBS_DB) as c:
                for j in all_jobs:
                    try:
                        c.execute(
                            "INSERT OR IGNORE INTO jobs (title, company, location, url, ts) VALUES (?,?,?,?,?)",
                            (j["title"], j["company"], j["location"], j["url"], datetime.now().isoformat())
                        )
                    except Exception:
                        pass

            if not all_jobs:
                self._last_result = f"No jobs found for '{query}'. Try different keywords."
                self._status = "done"
                return

            lines = [f"Found **{len(all_jobs)} jobs** for '{query}':\n"]
            for i, j in enumerate(all_jobs[:15], 1):
                lines.append(f"{i}. **{j['title']}** — {j['company']} ({j['location']})")
            lines.append(f"\nSay **'apply to all linkedin jobs'** to start applying via Easy Apply.")

            self._last_result = "\n".join(lines)
            self._status = "done"

            # Keep browser open
            if stay_open:
                page.wait_for_timeout(180000)

        except Exception as e:
            self._last_result = f"Job search error: {e}"
            self._status = "error"
        finally:
            try:
                if browser: browser.close()
                if pw: pw.stop()
            except Exception:
                pass

    # ── Easy Apply ────────────────────────────────────────────────────────────

    def apply_jobs_task(self, username, password, query="software engineer",
                        locations=None):
        """Easy Apply to jobs. Runs visible so user can see."""
        if locations is None:
            locations = ["United Kingdom", "Scotland", "India"]
        self._status = "applying"
        pw = browser = None
        applied = 0
        skipped = 0
        try:
            pw, browser, page = self._launch(headless=False)
            if not self._login(page, username, password):
                return

            q = query.replace(" ", "%20")
            url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location=United%20Kingdom&f_AL=true"
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            cards = page.query_selector_all(".job-card-container--clickable")
            print(f"[LinkedIn] Found {len(cards)} Easy Apply cards")

            for i, card in enumerate(cards[:10]):
                try:
                    title = self._text(card, ".job-card-list__title") or f"Job {i+1}"
                    company = self._text(card, ".job-card-container__primary-description") or "Unknown"

                    card.click()
                    page.wait_for_timeout(2000)

                    # Look for Easy Apply button
                    apply_btn = page.query_selector('.jobs-apply-button--top-card')
                    if not apply_btn:
                        apply_btn = page.query_selector('[data-job-id] .jobs-apply-button')
                    if not apply_btn:
                        skipped += 1
                        continue

                    apply_btn.click()
                    page.wait_for_timeout(2000)

                    # Navigate application steps
                    for step in range(8):
                        # Check for submit button
                        submit = page.query_selector('button[aria-label="Submit application"]')
                        if submit:
                            submit.click()
                            page.wait_for_timeout(2000)
                            applied += 1
                            print(f"[LinkedIn] Applied: {title} @ {company}")
                            with sqlite3.connect(JOBS_DB) as c:
                                c.execute(
                                    "INSERT INTO applications (title, company, status, ts) VALUES (?,?,'applied',?)",
                                    (title, company, datetime.now().isoformat())
                                )
                            break

                        # Check for next/review
                        next_btn = page.query_selector('button[aria-label="Continue to next step"]')
                        review_btn = page.query_selector('button[aria-label="Review your application"]')

                        if review_btn:
                            review_btn.click()
                            page.wait_for_timeout(1000)
                        elif next_btn:
                            next_btn.click()
                            page.wait_for_timeout(1000)
                        else:
                            # Complex form — skip, close modal
                            skipped += 1
                            dismiss = page.query_selector('button[aria-label="Dismiss"]')
                            if dismiss:
                                dismiss.click()
                                page.wait_for_timeout(500)
                                # Confirm dismiss
                                confirm = page.query_selector('button[data-control-name="discard_application_confirm_btn"]')
                                if confirm:
                                    confirm.click()
                            break

                except Exception as e:
                    print(f"[LinkedIn] Apply error on card {i}: {e}")
                    skipped += 1
                    # Try to close any open modal
                    try:
                        dismiss = page.query_selector('button[aria-label="Dismiss"]')
                        if dismiss:
                            dismiss.click()
                            page.wait_for_timeout(500)
                    except Exception:
                        pass
                    continue

            self._last_result = (
                f"✅ **Job applications done:**\n"
                f"Applied: {applied}\n"
                f"Skipped (complex forms): {skipped}\n\n"
                f"Say **'show my applications'** to see what was applied."
            )
            self._status = "done"
            page.wait_for_timeout(30000)

        except Exception as e:
            self._last_result = f"Apply error: {e}"
            self._status = "error"
        finally:
            try:
                if browser: browser.close()
                if pw: pw.stop()
            except Exception:
                pass

    # ── Status / History ─────────────────────────────────────────────────────

    def get_status(self):
        if self._last_result:
            return self._last_result
        return f"Status: {self._status}"

    def get_applied_jobs(self):
        try:
            with sqlite3.connect(JOBS_DB) as c:
                apps = c.execute(
                    "SELECT title, company, ts FROM applications ORDER BY id DESC LIMIT 20"
                ).fetchall()
                total = c.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            if not apps:
                return "No applications recorded yet."
            lines = [f"**Total applied: {total}**\n"]
            for a in apps:
                lines.append(f"• {a[0]} at {a[1]}")
            return "\n".join(lines)
        except Exception as e:
            return f"DB error: {e}"

    # ── Helper ────────────────────────────────────────────────────────────────

    def _text(self, el, selector):
        try:
            found = el.query_selector(selector)
            return found.inner_text().strip() if found else ""
        except Exception:
            return ""
