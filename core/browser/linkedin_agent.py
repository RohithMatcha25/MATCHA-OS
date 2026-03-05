"""
MATCHA LinkedIn Agent
Full LinkedIn automation - login, profile update, job search, job application.
Runs in a visible browser so user can see and intervene if needed.
"""

import os, json, time, sqlite3, pathlib, threading
from datetime import datetime
from typing import Optional, List

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
JOBS_DB = os.path.join(BASE, "core", "memory", "jobs.db")


class LinkedInAgent:
    def __init__(self):
        pathlib.Path(os.path.dirname(JOBS_DB)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._status = "idle"
        self._last_result = ""
        print("[MATCHA LinkedIn] LinkedIn agent ready.")

    def _init_db(self):
        with sqlite3.connect(JOBS_DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                title TEXT, company TEXT, location TEXT,
                url TEXT, status TEXT, ts TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY,
                job_id INTEGER, status TEXT, ts TEXT
            )""")

    def _get_page(self, headless=False):
        """Launch Playwright browser and return page."""
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--start-maximized"]
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = ctx.new_page()
            return pw, browser, page
        except Exception as e:
            print(f"[LinkedIn] Browser error: {e}")
            return None, None, None

    def _login(self, page, username: str, password: str) -> bool:
        """Login to LinkedIn. Returns True if successful."""
        try:
            page.goto("https://www.linkedin.com/login", timeout=20000)
            page.wait_for_selector("#username", timeout=10000)
            page.fill("#username", username)
            page.fill("#password", password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=20000)

            # Check if login worked
            if "feed" in page.url or "in/me" in page.url or "/home" in page.url:
                return True
            # Check for verification
            if "checkpoint" in page.url or "verification" in page.url:
                self._status = "needs_verification"
                self._last_result = "LinkedIn needs identity verification. Please open LinkedIn in your browser and verify, then try again."
                return False
            return True
        except Exception as e:
            print(f"[LinkedIn] Login error: {e}")
            return False

    # ── Profile ───────────────────────────────────────────────────────────────

    def view_profile(self, username: str, password: str) -> str:
        """Open and return profile info."""
        self._status = "running"
        pw, browser, page = self._get_page(headless=False)
        if not page:
            return "Could not launch browser. Make sure Playwright is installed."
        try:
            if not self._login(page, username, password):
                return self._last_result or "Login failed."

            page.goto("https://www.linkedin.com/in/me/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)

            # Extract profile info
            name = self._safe_text(page, "h1")
            headline = self._safe_text(page, ".text-body-medium")
            location = self._safe_text(page, ".pb2 span")

            self._status = "done"
            self._last_result = f"Profile loaded. Name: {name}, Headline: {headline}, Location: {location}"
            return self._last_result
        except Exception as e:
            self._status = "error"
            return f"Profile error: {e}"
        finally:
            try:
                browser.close()
                pw.stop()
            except Exception:
                pass

    def search_jobs(self, username: str, password: str, query: str, location: str = "United Kingdom") -> str:
        """Search LinkedIn jobs and return results."""
        self._status = "running"
        pw, browser, page = self._get_page(headless=False)
        if not page:
            return "Could not launch browser."
        try:
            if not self._login(page, username, password):
                return self._last_result or "Login failed."

            # Go to jobs
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
            page.goto(search_url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(3)

            # Scrape job listings
            jobs = []
            cards = page.query_selector_all(".job-card-container, .jobs-search__results-list li")
            for card in cards[:15]:
                try:
                    title_el = card.query_selector(".job-card-list__title, h3")
                    company_el = card.query_selector(".job-card-container__company-name, h4")
                    location_el = card.query_selector(".job-card-container__metadata-item")
                    link_el = card.query_selector("a")

                    title = title_el.inner_text().strip() if title_el else "Unknown"
                    company = company_el.inner_text().strip() if company_el else "Unknown"
                    loc = location_el.inner_text().strip() if location_el else ""
                    url = link_el.get_attribute("href") if link_el else ""
                    if url and not url.startswith("http"):
                        url = "https://www.linkedin.com" + url

                    if title != "Unknown":
                        jobs.append({"title": title, "company": company, "location": loc, "url": url})
                        # Save to DB
                        with sqlite3.connect(JOBS_DB) as c:
                            c.execute(
                                "INSERT OR IGNORE INTO jobs (title, company, location, url, status, ts) VALUES (?,?,?,?,'found',?)",
                                (title, company, loc, url, datetime.now().isoformat())
                            )
                except Exception:
                    continue

            self._status = "done"
            if not jobs:
                self._last_result = f"No jobs found for '{query}'. Try different keywords."
                return self._last_result

            lines = [f"Found {len(jobs)} jobs for **{query}**:\n"]
            for i, j in enumerate(jobs[:10], 1):
                lines.append(f"{i}. **{j['title']}** at {j['company']} — {j['location']}")

            lines.append(f"\nSay 'apply to job 1' or 'apply to all jobs' to apply.")
            self._last_result = "\n".join(lines)
            return self._last_result

        except Exception as e:
            self._status = "error"
            return f"Job search error: {e}"
        finally:
            try:
                browser.close()
                pw.stop()
            except Exception:
                pass

    def apply_jobs(self, username: str, password: str, query: str = "software engineer") -> str:
        """Search and apply to Easy Apply jobs."""
        self._status = "running"
        pw, browser, page = self._get_page(headless=False)
        if not page:
            return "Could not launch browser."
        try:
            if not self._login(page, username, password):
                return self._last_result or "Login failed."

            # Search with Easy Apply filter
            url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ','%20')}&f_AL=true&location=United%20Kingdom"
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(3)

            applied = 0
            skipped = 0
            cards = page.query_selector_all(".job-card-container")

            for card in cards[:5]:  # Apply to first 5 matching jobs
                try:
                    card.click()
                    time.sleep(2)

                    # Check for Easy Apply button
                    easy_apply = page.query_selector(".jobs-apply-button")
                    if not easy_apply:
                        skipped += 1
                        continue

                    easy_apply.click()
                    time.sleep(2)

                    # Click through application steps
                    for step in range(5):
                        next_btn = page.query_selector('button[aria-label="Continue to next step"]')
                        review_btn = page.query_selector('button[aria-label="Review your application"]')
                        submit_btn = page.query_selector('button[aria-label="Submit application"]')

                        if submit_btn:
                            submit_btn.click()
                            time.sleep(2)
                            applied += 1
                            # Log application
                            with sqlite3.connect(JOBS_DB) as c:
                                c.execute(
                                    "INSERT INTO applications (status, ts) VALUES ('applied', ?)",
                                    (datetime.now().isoformat(),)
                                )
                            break
                        elif review_btn:
                            review_btn.click()
                            time.sleep(1)
                        elif next_btn:
                            next_btn.click()
                            time.sleep(1)
                        else:
                            skipped += 1
                            # Close modal if open
                            dismiss = page.query_selector('button[aria-label="Dismiss"]')
                            if dismiss:
                                dismiss.click()
                            break

                except Exception as e:
                    print(f"[LinkedIn] Apply error on card: {e}")
                    skipped += 1
                    continue

            self._status = "done"
            self._last_result = f"Applied to {applied} jobs. Skipped {skipped} (not Easy Apply or required manual input)."
            return self._last_result

        except Exception as e:
            self._status = "error"
            return f"Apply error: {e}"
        finally:
            try:
                browser.close()
                pw.stop()
            except Exception:
                pass

    def get_status(self) -> str:
        return f"Status: {self._status}. Last result: {self._last_result or 'none'}"

    def get_applied_jobs(self) -> str:
        with sqlite3.connect(JOBS_DB) as c:
            rows = c.execute("SELECT title, company, status FROM jobs ORDER BY id DESC LIMIT 20").fetchall()
            apps = c.execute("SELECT COUNT(*) FROM applications WHERE status='applied'").fetchone()[0]
        if not rows:
            return "No jobs tracked yet."
        lines = [f"Applied: {apps} total\n"]
        for r in rows[:10]:
            lines.append(f"• {r[0]} at {r[1]} ({r[2]})")
        return "\n".join(lines)

    def _safe_text(self, page, selector: str) -> str:
        try:
            el = page.query_selector(selector)
            return el.inner_text().strip() if el else ""
        except Exception:
            return ""
