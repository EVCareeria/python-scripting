import json
import os
from collections import defaultdict

LOG_FILE_PATH = os.getenv("COWRIE_LOG_PATH", "/var/cowrie/logs/cowrie.json")

def get_cowrie_digested_logs(limit=50, log_path=None):
    """
    Reads Cowrie JSON logs and groups them by session ID so that 
    each entry represents a complete attacker session.
    """
    if log_path is None:
        log_path = LOG_FILE_PATH
    if not os.path.exists(log_path):
        return []

    sessions = defaultdict(lambda: {
        "session": "unknown",
        "timestamp": "",
        "end_timestamp": "",
        "src_ip": "unknown",
        "logins": [],
        "commands": [],
        "events": [],
        "duration_ms": 0,
        "closed": False
    })

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    session_id = data.get("session")
                    if not session_id:
                        continue
                    
                    s = sessions[session_id]
                    if s["session"] == "unknown":
                        s["session"] = session_id
                        s["timestamp"] = data.get("timestamp", "")
                        s["src_ip"] = data.get("src_ip", "unknown")

                    s["end_timestamp"] = data.get("timestamp", s["end_timestamp"])
                    s["events"].append(data)

                    eventid = data.get("eventid")
                    if eventid == "cowrie.login.success":
                        creds = f"{data.get('username')}/{data.get('password')}"
                        if creds not in s["logins"]:
                            s["logins"].append(creds)
                    elif eventid == "cowrie.command.input" or "input" in data:
                        cmd = data.get("input") or data.get("message")
                        if cmd and cmd not in s["commands"]:
                            s["commands"].append(cmd)
                    elif eventid == "cowrie.session.closed":
                        s["closed"] = True
                        s["duration_ms"] = data.get("duration_ms", 0)

                except json.JSONDecodeError:
                    continue

        session_list = list(sessions.values())
        session_list.sort(key=lambda x: x["timestamp"], reverse=True)
        return session_list[:limit]

    except Exception as e:
        print(f"Error reading Cowrie logs: {e}")
        return []

def is_cowrie_archive_name(filename):
    """True for rotated archives (e.g. cowrie.json.1, cowrie.json.2026-10-03), not the active log."""
    return filename.startswith("cowrie.json") and filename != "cowrie.json"

def list_cowrie_log_files():
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        return []
    files = []
    for f in os.listdir(log_dir):
        if is_cowrie_archive_name(f):
            full_path = os.path.join(log_dir, f)
            files.append({
                "filename": f,
                "size": os.path.getsize(full_path)
            })
    return sorted(files, key=lambda x: x['filename'], reverse=True)

def get_specific_cowrie_log(filename, limit=100):
    # Only bare archive names are accepted, so the request cannot leave the log directory.
    if os.path.basename(filename) != filename or not is_cowrie_archive_name(filename):
        return []
    log_dir = os.path.dirname(LOG_FILE_PATH)
    specific_path = os.path.join(log_dir, filename)
    return get_cowrie_digested_logs(limit=limit, log_path=specific_path)
