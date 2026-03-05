"""
MATCHA Universal Browser Agent
Works for ANY website - login, navigate, act.
Supports: LinkedIn, Instagram, Gmail, GitHub, Amazon, Deliveroo, Uber Eats, Just Eat,
          Twitter/X, Facebook, Netflix, Spotify, YouTube, Reddit, and any URL.
"""

import os, sqlite3, pathlib, threading, time, re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BROWSER_DB = os.path.join(BASE, "core", "memory", "browser_tasks.db")

# ── Site configs ──────────────────────────────────────────────────────────────
SITES = {
    "linkedin": {
        "url": "https://www.linkedin.com/login",
        "user_sel": "#username",
        "pass_sel": "#password",
        "submit_sel": 'button[type="submit"]',
        "home_url": "https://www.linkedin.com/feed/",
        "logged_in_check": lambda u: "feed" in u or "/in/" in u,
    },
    "instagram": {
        "url": "https://www.instagram.com/accounts/login/",
        "user_sel": 'input[name="username"]',
        "pass_sel": 'input[name="password"]',
        "submit_sel": 'button[type="submit"]',
        "home_url": "https://www.instagram.com/",
        "logged_in_check": lambda u: "instagram.com" in u and "login" not in u,
    },
    "gmail": {
        "url": "https://accounts.google.com/signin",
        "user_sel": 'input[type="email"]',
        "pass_sel": 'input[type="password"]',
        "submit_sel": '#identifierNext, #passwordNext',
        "home_url": "https://mail.google.com/",
        "logged_in_check": lambda u: "mail.google.com" in u,
    },
    "github": {
        "url": "https://github.com/login",
        "user_sel": "#login_field",
        "pass_sel": "#password",
        "submit_sel": '[name="commit"]',
        "home_url": "https://github.com/",
        "logged_in_check": lambda u: "github.com" in u and "login" not in u,
    },
    "amazon": {
        "url": "https://www.amazon.co.uk/ap/signin",
        "user_sel": "#ap_email",
        "pass_sel": "#ap_password",
        "submit_sel": "#signInSubmit",
        "home_url": "https://www.amazon.co.uk/",
        "logged_in_check": lambda u: "amazon.co.uk" in u and "signin" not in u,
    },
    "twitter": {
        "url": "https://x.com/login",
        "user_sel": 'input[autocomplete="username"]',
        "pass_sel": 'input[name="password"]',
        "submit_sel": '[data-testid="LoginButton"]',
        "home_url": "https://x.com/home",
        "logged_in_check": lambda u: "x.com/home" in u or "twitter.com/home" in u,
    },
    "facebook": {
        "url": "https://www.facebook.com/login",
        "user_sel": "#email",
        "pass_sel": "#pass",
        "submit_sel": '[name="login"]',
        "home_url": "https://www.facebook.com/",
        "logged_in_check": lambda u: "facebook.com" in u and "login" not in u,
    },
    "netflix": {
        "url": "https://www.netflix.com/login",
        "user_sel": 'input[name="userLoginId"]',
        "pass_sel": 'input[name="password"]',
        "submit_sel": 'button[data-uia="login-submit-button"]',
        "home_url": "https://www.netflix.com/browse",
        "logged_in_check": lambda u: "netflix.com/browse" in u,
    },
    "spotify": {
        "url": "https://accounts.spotify.com/login",
        "user_sel": "#login-username",
        "pass_sel": "#login-password",
        "submit_sel": "#login-button",
        "home_url": "https://open.spotify.com/",
        "logged_in_check": lambda u: "open.spotify.com" in u,
    },
    "deliveroo": {
        "url": "https://deliveroo.co.uk/login",
        "user_sel": 'input[name="email"]',
        "pass_sel": 'input[name="password"]',
        "submit_sel": 'button[type="submit"]',
        "home_url": "https://deliveroo.co.uk/",
        "logged_in_check": lambda u: "deliveroo.co.uk" in u and "login" not in u,
    },
    "ubereats": {
        "url": "https://auth.uber.com/v2/",
        "user_sel": 'input[name="email"]',
        "pass_sel": 'input[name="password"]',
        "submit_sel": '[data-testid="submit-button"]',
        "home_url": "https://www.ubereats.com/",
        "logged_in_check": lambda u: "ubereats.com" in u and "auth" not in u,
    },
    "just eat": {
        "url": "https://www.just-eat.co.uk/account/login",
        "user_sel": '#email',
        "pass_sel": '#password',
        "submit_sel": 'button[type="submit"]',
        "home_url": "https://www.just-eat.co.uk/",
        "logged_in_check": lambda u: "just-eat.co.uk" in u and "login" not in u,
    },
}

# ── Action maps ───────────────────────────────────────────────────────────────
# After login: keywords → URL to navigate to
POST_LOGIN_ACTIONS = {
    "linkedin": {
        "profile":    "https://www.linkedin.com/in/me/",
        "jobs":       "https://www.linkedin.com/jobs/search/?keywords=software+engineer&location=United+Kingdom&f_AL=true",
        "messages":   "https://www.linkedin.com/messaging/",
        "connections":"https://www.linkedin.com/mynetwork/",
        "notifications": "https://www.linkedin.com/notifications/",
    },
    "instagram": {
        "profile":    "https://www.instagram.com/{username}/",
        "explore":    "https://www.instagram.com/explore/",
        "messages":   "https://www.instagram.com/direct/inbox/",
        "reels":      "https://www.instagram.com/reels/",
    },
    "gmail": {
        "inbox":      "https://mail.google.com/mail/u/0/#inbox",
        "sent":       "https://mail.google.com/mail/u/0/#sent",
        "compose":    "https://mail.google.com/mail/u/0/#compose",
    },
    "github": {
        "profile":    "https://github.com/",
        "repos":      "https://github.com/RohithMatcha25?tab=repositories",
        "notifications": "https://github.com/notifications",
    },
    "amazon": {
        "orders":     "https://www.amazon.co.uk/gp/css/order-history",
        "cart":       "https://www.amazon.co.uk/gp/cart/view.html",
        "wishlist":   "https://www.amazon.co.uk/wishlist",
    },
}


class UniversalBrowserAgent:
    def __init__(self):
        pathlib.Path(os.path.dirname(BROWSER_DB)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._status = {}   # service → last status
        self._result = {}   # service → last result
        print("[MATCHA Browser] Universal agent ready.")

    def _init_db(self):
        with sqlite3.connect(BROWSER_DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                service TEXT, action TEXT, status TEXT, result TEXT, ts TEXT
            )""")

    # ── Launch ────────────────────────────────────────────────────────────────

    def _launch(self):
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=80,
            args=["--no-sandbox", "--start-maximized",
                  "--disable-blink-features=AutomationControlled"]
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

    # ── Login ─────────────────────────────────────────────────────────────────

    def _login(self, page, service_key, username, password):
        cfg = SITES.get(service_key)
        if not cfg:
            # Generic: just open the URL
            page.goto(f"https://www.{service_key}.com", timeout=20000, wait_until="domcontentloaded")
            return True

        try:
            page.goto(cfg["url"], timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            # Gmail needs two steps (email → next → password → next)
            if service_key == "gmail":
                page.fill(cfg["user_sel"], username, timeout=8000)
                page.click("#identifierNext")
                page.wait_for_timeout(2000)
                page.fill(cfg["pass_sel"], password, timeout=8000)
                page.click("#passwordNext")
            else:
                page.fill(cfg["user_sel"], username, timeout=8000)
                page.wait_for_timeout(500)
                page.fill(cfg["pass_sel"], password)
                page.wait_for_timeout(500)
                # Handle multiple submit selectors
                for sel in cfg["submit_sel"].split(","):
                    sel = sel.strip()
                    try:
                        btn = page.query_selector(sel)
                        if btn:
                            btn.click()
                            break
                    except Exception:
                        continue

            page.wait_for_timeout(3000)
            page.wait_for_load_state("domcontentloaded", timeout=20000)

            # Check result
            url = page.url
            if "checkpoint" in url or "challenge" in url or "verify" in url:
                return "verification_needed"
            if cfg["logged_in_check"](url):
                return True
            # Might still be loading
            page.wait_for_timeout(3000)
            if cfg["logged_in_check"](page.url):
                return True
            return True  # Try anyway

        except Exception as e:
            print(f"[Browser] Login error for {service_key}: {e}")
            return True  # Browser is open, let user see it

    # ── Main task runner ──────────────────────────────────────────────────────

    def run_task(self, service_key, username, password, task_text, stay_open_secs=180):
        """
        Core method — runs in a background thread.
        Logs in, navigates to the right page, performs action if possible.
        Browser stays visible for stay_open_secs.
        """
        self._status[service_key] = "running"
        pw = browser = None
        t_lower = task_text.lower()

        try:
            pw, browser, page = self._launch()
            result = self._login(page, service_key, username, password)

            if result == "verification_needed":
                msg = (f"⚠️ {service_key.title()} needs verification. "
                       f"Please verify in the browser that just opened, then try again.")
                self._result[service_key] = msg
                self._status[service_key] = "needs_verification"
                page.wait_for_timeout(120000)
                return

            # Post-login navigation
            actions = POST_LOGIN_ACTIONS.get(service_key, {})
            navigated = False

            for keyword, nav_url in actions.items():
                if keyword in t_lower:
                    # Replace {username} placeholder if needed
                    nav_url = nav_url.replace("{username}", username.split("@")[0])
                    page.goto(nav_url, timeout=20000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                    navigated = True
                    break

            # Service-specific actions
            action_result = self._do_action(page, service_key, task_text, username, password)

            msg = f"✅ {service_key.title()}: {action_result}\nBrowser is open — you can see and interact with it."
            self._result[service_key] = msg
            self._status[service_key] = "done"

            self._log_task(service_key, task_text, "done", action_result)

            # Keep browser open
            page.wait_for_timeout(stay_open_secs * 1000)

        except Exception as e:
            msg = f"❌ {service_key.title()} error: {e}"
            self._result[service_key] = msg
            self._status[service_key] = "error"
        finally:
            try:
                if browser: browser.close()
                if pw: pw.stop()
            except Exception:
                pass

    # ── Service-specific actions ──────────────────────────────────────────────

    def _do_action(self, page, service, task, username, password):
        t = task.lower()

        if service == "linkedin":
            return self._linkedin_action(page, t)
        elif service == "instagram":
            return self._instagram_action(page, t, username)
        elif service == "gmail":
            return self._gmail_action(page, t)
        elif service == "amazon":
            return self._amazon_action(page, t)
        elif service == "deliveroo" or service == "ubereats" or service == "just eat":
            return self._food_action(page, t, service)
        else:
            return f"Logged in to {service.title()}. Browser is open."

    def _linkedin_action(self, page, t):
        if any(w in t for w in ["profile", "update profile", "my profile"]):
            page.goto("https://www.linkedin.com/in/me/", timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            name = self._text(page, "h1")
            return f"Opened your LinkedIn profile. Name: {name}"

        elif any(w in t for w in ["jobs", "search job", "find job", "apply"]):
            # Extract query
            query = "software engineer"
            for jt in ["software engineer", "automation engineer", "backend", "frontend",
                       "full stack", "python developer", "devops"]:
                if jt in t:
                    query = jt
                    break
            loc = "United Kingdom"
            for l in ["uk", "scotland", "india", "london"]:
                if l in t:
                    loc = l.title()
                    break
            url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&location={loc.replace(' ', '%20')}&f_AL=true"
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            count = len(page.query_selector_all(".job-card-container--clickable"))
            return f"Found {count} Easy Apply jobs for '{query}' in {loc}. Browser is open — you can apply from here, or say 'apply to all linkedin jobs'."

        elif "messages" in t or "inbox" in t:
            page.goto("https://www.linkedin.com/messaging/", timeout=15000)
            return "Opened LinkedIn messages."

        return "Logged into LinkedIn. Browser is open."

    def _instagram_action(self, page, t, username):
        if "profile" in t:
            handle = username.split("@")[0]
            page.goto(f"https://www.instagram.com/{handle}/", timeout=15000)
            return "Opened your Instagram profile."
        elif "message" in t or "dm" in t:
            page.goto("https://www.instagram.com/direct/inbox/", timeout=15000)
            return "Opened Instagram DMs."
        elif "explore" in t:
            page.goto("https://www.instagram.com/explore/", timeout=15000)
            return "Opened Instagram Explore."
        elif "reel" in t:
            page.goto("https://www.instagram.com/reels/", timeout=15000)
            return "Opened Instagram Reels."
        return "Logged into Instagram. Browser is open."

    def _gmail_action(self, page, t):
        page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        if "compose" in t or "send" in t or "write" in t:
            compose = page.query_selector('[gh="cm"]')
            if compose:
                compose.click()
                page.wait_for_timeout(1000)
            return "Opened Gmail compose."
        return "Opened Gmail inbox."

    def _amazon_action(self, page, t):
        if "order" in t:
            page.goto("https://www.amazon.co.uk/gp/css/order-history", timeout=20000)
            return "Opened Amazon order history."
        elif "search" in t or "buy" in t or "find" in t:
            # Extract search query
            m = re.search(r'(?:search|buy|find|order)\s+(.+?)(?:\s+on amazon|$)', t)
            if m:
                q = m.group(1).strip().replace(" ", "+")
                page.goto(f"https://www.amazon.co.uk/s?k={q}", timeout=20000)
                return f"Searched Amazon for '{m.group(1)}'."
        return "Opened Amazon. Browser is open."

    def _food_action(self, page, t, service):
        if "order" in t or "food" in t:
            # Extract food item
            m = re.search(r'order\s+(.+?)(?:\s+from|\s+on|$)', t)
            item = m.group(1) if m else "food"
            return f"Opened {service.title()}. Search for '{item}' in the browser."
        return f"Logged into {service.title()}. Browser is open."

    # ── LinkedIn Easy Apply (dedicated) ──────────────────────────────────────

    def linkedin_apply_all(self, username, password, query="software engineer",
                           locations=None):
        """Apply to Easy Apply jobs on LinkedIn."""
        if locations is None:
            locations = ["United Kingdom"]
        self._status["linkedin_apply"] = "applying"
        pw = browser = None
        applied = 0
        skipped = 0

        try:
            pw, browser, page = self._launch()
            login_ok = self._login(page, "linkedin", username, password)
            if login_ok == "verification_needed":
                self._result["linkedin_apply"] = "Verification needed on LinkedIn."
                return

            for loc in locations[:3]:
                q = query.replace(" ", "%20")
                l = loc.replace(" ", "%20")
                url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location={l}&f_AL=true"
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                cards = page.query_selector_all(".job-card-container--clickable")
                print(f"[LinkedIn Apply] {len(cards)} cards for {query} in {loc}")

                for i, card in enumerate(cards[:8]):
                    try:
                        title = self._text(card, ".job-card-list__title") or f"Job {i+1}"
                        company = self._text(card, ".job-card-container__primary-description") or ""
                        card.click()
                        page.wait_for_timeout(2000)

                        apply_btn = (
                            page.query_selector('.jobs-apply-button--top-card') or
                            page.query_selector('button.jobs-apply-button')
                        )
                        if not apply_btn:
                            skipped += 1
                            continue

                        apply_btn.click()
                        page.wait_for_timeout(2000)

                        for step in range(10):
                            submit = page.query_selector('button[aria-label="Submit application"]')
                            nxt = page.query_selector('button[aria-label="Continue to next step"]')
                            rev = page.query_selector('button[aria-label="Review your application"]')

                            if submit:
                                submit.click()
                                page.wait_for_timeout(2000)
                                applied += 1
                                self._log_task("linkedin", f"applied:{title}@{company}", "applied", "")
                                print(f"[LinkedIn Apply] ✅ Applied: {title} @ {company}")
                                break
                            elif rev:
                                rev.click()
                                page.wait_for_timeout(1000)
                            elif nxt:
                                nxt.click()
                                page.wait_for_timeout(1000)
                            else:
                                skipped += 1
                                for dismiss_sel in [
                                    'button[aria-label="Dismiss"]',
                                    'button[data-control-name="discard_application_confirm_btn"]'
                                ]:
                                    try:
                                        d = page.query_selector(dismiss_sel)
                                        if d:
                                            d.click()
                                            page.wait_for_timeout(500)
                                    except Exception:
                                        pass
                                break
                    except Exception as e:
                        print(f"[LinkedIn Apply] Error card {i}: {e}")
                        skipped += 1
                        try:
                            d = page.query_selector('button[aria-label="Dismiss"]')
                            if d:
                                d.click()
                        except Exception:
                            pass

            result = (
                f"✅ LinkedIn Apply done.\n"
                f"Applied: {applied} jobs\n"
                f"Skipped: {skipped} (complex forms)\n\n"
                f"Say 'show my applications' to see the list."
            )
            self._result["linkedin_apply"] = result
            self._status["linkedin_apply"] = "done"
            page.wait_for_timeout(60000)

        except Exception as e:
            self._result["linkedin_apply"] = f"Apply error: {e}"
            self._status["linkedin_apply"] = "error"
        finally:
            try:
                if browser: browser.close()
                if pw: pw.stop()
            except Exception:
                pass

    # ── Status / History ─────────────────────────────────────────────────────

    def get_status(self, service=None):
        if service and service in self._result:
            return self._result[service]
        if "linkedin_apply" in self._result:
            return self._result["linkedin_apply"]
        all_results = list(self._result.values())
        if all_results:
            return all_results[-1]
        return f"No tasks run yet."

    def get_task_history(self, limit=10):
        try:
            with sqlite3.connect(BROWSER_DB) as c:
                rows = c.execute(
                    "SELECT service, action, status, ts FROM tasks ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            if not rows:
                return "No task history."
            lines = ["**Recent browser tasks:**\n"]
            for r in rows:
                lines.append(f"• {r[0].title()} — {r[1][:60]} ({r[2]}) [{r[3][:10]}]")
            return "\n".join(lines)
        except Exception:
            return "No history."

    def _log_task(self, service, action, status, result):
        try:
            with sqlite3.connect(BROWSER_DB) as c:
                c.execute(
                    "INSERT INTO tasks (service, action, status, result, ts) VALUES (?,?,?,?,?)",
                    (service, action[:200], status, result[:500], datetime.now().isoformat())
                )
        except Exception:
            pass

    def _text(self, el, selector):
        try:
            found = el.query_selector(selector)
            return found.inner_text().strip() if found else ""
        except Exception:
            return ""
