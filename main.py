"""
MATCHA OS — Main Server v2.0
Connects AI core + Online Mode + System Control + Shield + Devices to the interface.
"""

from flask import Flask, jsonify, request, send_from_directory
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.matcha_ai import MatchaAI

app = Flask(__name__, static_folder="interface")
matcha = MatchaAI()
matcha.user_name = "Rohith"


# ─── Core Interface ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("interface", "index.html")


@app.route("/api/boot")
def boot():
    """Called when MATCHA interface loads."""
    greeting = matcha.greet_on_boot()
    return jsonify({
        "greeting": greeting,
        "version": "0.2.0",
        "online": matcha.online
    })


@app.route("/api/think", methods=["POST"])
def think():
    """Main AI reasoning endpoint."""
    data = request.get_json()
    user_input = data.get("input", "")
    online = data.get("online", False)

    matcha.set_online(online)
    response = matcha.think(user_input)

    return jsonify({"response": response, "online": matcha.online})


@app.route("/api/mode", methods=["POST"])
def set_mode():
    """Switch online/offline mode."""
    data = request.get_json()
    online = data.get("online", False)
    matcha.set_online(online)
    return jsonify({"status": "ok", "online": online})


@app.route("/api/listen", methods=["POST"])
def listen():
    """Voice input endpoint."""
    try:
        from core.voice.matcha_voice import MatchaVoice
        voice = MatchaVoice(on_input_callback=lambda x: x)
        text = voice.listen_once()
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"text": "", "error": str(e)})


# ─── Online Mode — Web Agent ─────────────────────────────────────────────────

@app.route("/api/online/search", methods=["POST"])
def online_search():
    """Direct web search endpoint."""
    data = request.get_json()
    query = data.get("query", "")
    if not query:
        return jsonify({"success": False, "error": "No query provided."})

    agent = matcha._get_web_agent()
    if not agent:
        return jsonify({"success": False, "error": "Web agent unavailable."})

    result = agent.search(query)
    return jsonify(result)


@app.route("/api/online/weather", methods=["POST"])
def online_weather():
    """Weather endpoint."""
    data = request.get_json()
    location = data.get("location", "London")

    agent = matcha._get_web_agent()
    if not agent:
        return jsonify({"success": False, "error": "Web agent unavailable."})

    result = agent.get_weather(location)
    return jsonify(result)


@app.route("/api/online/news", methods=["POST"])
def online_news():
    """News endpoint."""
    data = request.get_json()
    source = data.get("source", "bbc")

    agent = matcha._get_web_agent()
    if not agent:
        return jsonify({"success": False, "error": "Web agent unavailable."})

    result = agent.get_news(source)
    return jsonify(result)


@app.route("/api/online/youtube", methods=["POST"])
def online_youtube():
    """YouTube search endpoint."""
    data = request.get_json()
    query = data.get("query", "")

    agent = matcha._get_web_agent()
    if not agent:
        return jsonify({"success": False, "error": "Web agent unavailable."})

    result = agent.search_youtube(query)
    return jsonify(result)


@app.route("/api/online/wikipedia", methods=["POST"])
def online_wikipedia():
    """Wikipedia lookup endpoint."""
    data = request.get_json()
    query = data.get("query", "")

    agent = matcha._get_web_agent()
    if not agent:
        return jsonify({"success": False, "error": "Web agent unavailable."})

    result = agent.wikipedia(query)
    return jsonify(result)


@app.route("/api/online/fetch", methods=["POST"])
def online_fetch():
    """Fetch any URL endpoint."""
    data = request.get_json()
    url = data.get("url", "")

    agent = matcha._get_web_agent()
    if not agent:
        return jsonify({"success": False, "error": "Web agent unavailable."})

    result = agent.fetch_url(url)
    return jsonify(result)


# ─── System Control ──────────────────────────────────────────────────────────

@app.route("/api/system/info")
def system_info():
    """Get system resource usage."""
    sc = matcha._get_system_control()
    if not sc:
        return jsonify({"success": False, "error": "System control unavailable."})
    return jsonify(sc.get_system_info())


@app.route("/api/system/volume", methods=["GET", "POST"])
def system_volume():
    """Get or set volume."""
    sc = matcha._get_system_control()
    if not sc:
        return jsonify({"success": False, "error": "System control unavailable."})

    if request.method == "GET":
        return jsonify(sc.get_volume())
    else:
        data = request.get_json()
        level = data.get("level")
        if level is not None:
            return jsonify(sc.set_volume(int(level)))
        action = data.get("action", "")
        if action == "mute":
            return jsonify(sc.mute())
        elif action == "unmute":
            return jsonify(sc.unmute())
        return jsonify({"success": False, "error": "Specify level or action."})


@app.route("/api/system/processes")
def system_processes():
    """List running processes."""
    sc = matcha._get_system_control()
    if not sc:
        return jsonify({"success": False, "error": "System control unavailable."})
    filter_name = request.args.get("filter")
    return jsonify(sc.list_processes(filter_name))


@app.route("/api/system/launch", methods=["POST"])
def system_launch():
    """Launch an application."""
    data = request.get_json()
    app_name = data.get("app", "")
    sc = matcha._get_system_control()
    if not sc:
        return jsonify({"success": False, "error": "System control unavailable."})
    return jsonify(sc.launch_app(app_name))


@app.route("/api/system/files", methods=["POST"])
def system_files():
    """Search for files."""
    data = request.get_json()
    query = data.get("query", "")
    search_dir = data.get("dir")
    sc = matcha._get_system_control()
    if not sc:
        return jsonify({"success": False, "error": "System control unavailable."})
    return jsonify(sc.find_files(query, search_dir))


# ─── Security / MATCHA Shield ─────────────────────────────────────────────────

@app.route("/api/shield/status")
def shield_status():
    """Shield status."""
    shield = matcha._get_shield()
    if not shield:
        return jsonify({"success": False, "error": "Shield unavailable."})
    return jsonify(shield.get_status())


@app.route("/api/shield/scan", methods=["POST"])
def shield_scan():
    """Scan a path."""
    data = request.get_json()
    path = data.get("path", os.path.expanduser("~/Downloads"))
    shield = matcha._get_shield()
    if not shield:
        return jsonify({"success": False, "error": "Shield unavailable."})
    # Run scan in thread to not block Flask
    import threading
    result_holder = {}
    def run_scan():
        result_holder["result"] = shield.scan_directory(path)
    t = threading.Thread(target=run_scan)
    t.start()
    t.join(timeout=30)
    return jsonify(result_holder.get("result", {"success": False, "error": "Scan timed out."}))


@app.route("/api/shield/quarantine")
def shield_quarantine():
    """List quarantine."""
    shield = matcha._get_shield()
    if not shield:
        return jsonify({"success": False, "error": "Shield unavailable."})
    return jsonify(shield.list_quarantine())


@app.route("/api/shield/threats")
def shield_threats():
    """Get threat log."""
    shield = matcha._get_shield()
    if not shield:
        return jsonify({"success": False, "error": "Shield unavailable."})
    limit = int(request.args.get("limit", 20))
    return jsonify(shield.get_threat_log(limit))


# ─── Devices ─────────────────────────────────────────────────────────────────

@app.route("/api/devices")
def devices():
    """All connected devices."""
    dm = matcha._get_device_manager()
    if not dm:
        return jsonify({"success": False, "error": "Device manager unavailable."})
    return jsonify(dm.get_all_devices())


@app.route("/api/devices/usb")
def devices_usb():
    """USB drives."""
    dm = matcha._get_device_manager()
    if not dm:
        return jsonify({"success": False, "error": "Device manager unavailable."})
    return jsonify(dm.list_usb_drives())


@app.route("/api/devices/bluetooth")
def devices_bluetooth():
    """Bluetooth devices."""
    dm = matcha._get_device_manager()
    if not dm:
        return jsonify({"success": False, "error": "Device manager unavailable."})
    return jsonify(dm.list_bluetooth_devices())


# ─── Memory / Patterns ───────────────────────────────────────────────────────

@app.route("/api/memory/patterns")
def memory_patterns():
    """Get usage patterns."""
    patterns = matcha.memory.get_patterns()
    return jsonify({"success": True, "patterns": patterns})


@app.route("/api/memory/context")
def memory_context():
    """Get recent conversation context."""
    context = matcha.memory.get_recent_context(10)
    return jsonify({"success": True, "context": [
        {"input": row[0], "intent": row[1], "response": row[2]}
        for row in context
    ]})


# ─── Download ────────────────────────────────────────────────────────────────

@app.route("/source")
def source_file():
    """Serve source files for remote update."""
    from flask import request as _req, send_file as _sf, abort
    import os
    file_path = _req.args.get("file", "")
    # Security: only allow specific extensions, no path traversal
    if not file_path or ".." in file_path or file_path.startswith("/"):
        abort(400)
    allowed = (".py", ".html", ".js", ".css", ".json", ".txt", ".bat", ".sh")
    if not any(file_path.endswith(ext) for ext in allowed):
        abort(403)
    full_path = os.path.join(os.path.dirname(__file__), file_path.replace("/", os.sep))
    if not os.path.exists(full_path):
        abort(404)
    return _sf(full_path, as_attachment=False)

@app.route("/download")
def download():
    """Serve the Windows installer ZIP."""
    from flask import send_file as _send_file
    import os
    zip_path = os.path.join(os.path.dirname(__file__), "dist", "matcha-os-windows.zip")
    if os.path.exists(zip_path):
        return _send_file(zip_path, as_attachment=True, download_name="matcha-os-windows.zip")
    return {"error": "File not found"}, 404


# ─── Learning & Permissions ───────────────────────────────────────────────────

@app.route("/api/learning/stats")
def learning_stats():
    return jsonify({"success": True, "stats": matcha.get_learning_stats()})


@app.route("/api/permissions")
def permissions():
    return jsonify({"success": True, "permissions": matcha.get_permissions()})


@app.route("/api/permissions/revoke", methods=["POST"])
def revoke_permission():
    data = request.get_json()
    action_type = data.get("action_type", "")
    return jsonify({"success": True, "message": matcha.revoke_permission(action_type)})


# ─── Start ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════╗
║         MATCHA OS v0.2.0             ║
║    Online Mode · System Control      ║
║    Shield · Devices · Memory         ║
╚══════════════════════════════════════╝
    """)
    print("[MATCHA] Starting on http://localhost:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
