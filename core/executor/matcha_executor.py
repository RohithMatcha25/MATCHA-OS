"""
MATCHA Code Executor
Writes real files to disk, installs deps, runs them, returns a live URL.
"""

import os, sys, subprocess, socket, time, re, pathlib, threading

WORKSPACE = os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "apps")


class MatchaExecutor:
    def __init__(self):
        pathlib.Path(WORKSPACE).mkdir(parents=True, exist_ok=True)
        self.running = {}   # app_slug -> {process, port, url, dir}
        print("[MATCHA Executor] Code executor ready.")

    # ── Public ────────────────────────────────────────────────────────────────

    def build(self, request: str, brain) -> str:
        """
        Takes a natural-language build request + brain.
        Returns a status string (may include __BUILD_ASYNC__ token for async jobs).
        """
        slug = self._slug(request)
        app_dir = os.path.join(WORKSPACE, slug)
        pathlib.Path(app_dir).mkdir(parents=True, exist_ok=True)

        port = self._free_port()
        code = self._generate(request, port, brain)
        if not code:
            return "Could not generate code. Try again with more detail."

        app_file = os.path.join(app_dir, "app.py")
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(code)

        self._install("flask")

        result = self._start(slug, app_file, app_dir, port)
        if result == "ok":
            url = f"http://localhost:{port}"
            self.running[slug]["url"] = url
            return f"✅ **Built and running.**\n\nOpen: **{url}**\nFiles: `{app_dir}`"

        # Auto-fix on error
        err = result
        fixed = self._fix(code, err, port, brain)
        if fixed:
            with open(app_file, "w", encoding="utf-8") as f:
                f.write(fixed)
            result2 = self._start(slug, app_file, app_dir, port)
            if result2 == "ok":
                url = f"http://localhost:{port}"
                self.running[slug]["url"] = url
                return f"✅ **Built and running** (auto-fixed).\n\nOpen: **{url}**\nFiles: `{app_dir}`"
            return f"Build failed after auto-fix:\n```\n{result2[:300]}\n```"

        return f"Build failed:\n```\n{err[:300]}\n```"

    def run_code(self, code: str, lang: str = "python") -> str:
        """Execute arbitrary code and return output."""
        try:
            tmp = os.path.join(WORKSPACE, "_run_tmp.py")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(code)
            result = subprocess.run(
                [sys.executable, tmp],
                capture_output=True, text=True, timeout=15
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            if out:
                return f"```\n{out}\n```"
            if err:
                return f"Error:\n```\n{err}\n```"
            return "Code ran with no output."
        except subprocess.TimeoutExpired:
            return "Code timed out (15s limit)."
        except Exception as e:
            return f"Execution error: {e}"

    def list_apps(self) -> str:
        if not self.running:
            return "No apps running."
        lines = []
        for slug, info in self.running.items():
            alive = "🟢 running" if info["process"].poll() is None else "🔴 stopped"
            lines.append(f"• **{slug}** — {info.get('url','?')} ({alive})")
        return "\n".join(lines)

    def stop(self, slug: str) -> str:
        if slug in self.running:
            try:
                self.running[slug]["process"].terminate()
            except Exception:
                pass
            del self.running[slug]
            return f"Stopped {slug}."
        return f"No app '{slug}' found."

    # ── Private ───────────────────────────────────────────────────────────────

    def _generate(self, request: str, port: int, brain) -> str:
        prompt = (
            f"Build a complete, working Flask web app for this request: {request}\n\n"
            f"RULES:\n"
            f"- Return ONLY raw Python code. No markdown fences. No explanation.\n"
            f"- Use Flask + render_template_string only (no external template files)\n"
            f"- Include full inline CSS inside the HTML — make it look modern and clean\n"
            f"- All features must actually work (forms submit, data saves in-memory)\n"
            f"- Port: {port}\n"
            f"- Last line must be: app.run(host='0.0.0.0', port={port}, debug=False)\n"
            f"- Start with: from flask import Flask"
        )
        raw = brain.think(prompt)
        return self._extract(raw)

    def _fix(self, code: str, error: str, port: int, brain) -> str:
        prompt = (
            f"This Flask app crashed with this error:\n{error}\n\n"
            f"Fix the code. Return ONLY raw Python. No fences. Port={port}.\n\n"
            f"Code:\n{code}"
        )
        raw = brain.think(prompt)
        return self._extract(raw)

    def _extract(self, text: str) -> str:
        m = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        lines = text.strip().splitlines()
        code_lines = []
        started = False
        for line in lines:
            if not started and re.match(r"^(from |import |@app|app\s*=|#)", line):
                started = True
            if started:
                code_lines.append(line)
        return "\n".join(code_lines) if code_lines else text.strip()

    def _start(self, slug: str, app_file: str, app_dir: str, port: int) -> str:
        if slug in self.running:
            try:
                self.running[slug]["process"].terminate()
            except Exception:
                pass

        proc = subprocess.Popen(
            [sys.executable, app_file],
            cwd=app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2.5)
        if proc.poll() is not None:
            err = proc.stderr.read().decode(errors="ignore")
            return err or "Unknown error"

        self.running[slug] = {"process": proc, "port": port, "url": "", "dir": app_dir}
        return "ok"

    def _install(self, package: str):
        try:
            __import__(package)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", package, "-q"])

    def _free_port(self) -> int:
        used = {v["port"] for v in self.running.values()}
        for p in range(8100, 8300):
            if p in used:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", p))
                    return p
                except OSError:
                    continue
        return 8100

    def _slug(self, request: str) -> str:
        words = re.sub(r"[^a-z0-9 ]", "", request.lower()).split()
        useful = [w for w in words if w not in
                  ("build", "me", "a", "an", "the", "make", "create", "write", "please", "app", "i", "want")]
        return "-".join(useful[:4]) or "app"
