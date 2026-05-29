import os
import sys
import json
import re
import io
import contextlib
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Add parent directory to path so we can import hit_cli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import hit_cli

def find_available_port(start_port=8000):
    import socket
    port = start_port
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("localhost", port))
            s.close()
            return port
        except OSError:
            port += 1

PORT = find_available_port(8000)
GUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")

def strip_ansi(text):
    """Strip ANSI color codes from stdout captures."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def run_cli_capture(func, *args, **kwargs):
    """Run a hit_cli function and capture its stdout/stderr."""
    f = io.StringIO()
    with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
        try:
            func(*args, **kwargs)
            success = True
        except Exception as e:
            print(f"Error executing command: {e}")
            success = False
    return success, strip_ansi(f.getvalue().strip())

class HITHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute default HTTP logging to stdout to keep console clean
        pass

    def _set_headers(self, content_type="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(status=200)

    def do_GET(self):
        # Serve frontend static assets
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(os.path.join(GUI_DIR, "index.html"), "text/html")
            return
        elif self.path == "/style.css":
            self._serve_file(os.path.join(GUI_DIR, "style.css"), "text/css")
            return
        elif self.path == "/app.js":
            self._serve_file(os.path.join(GUI_DIR, "app.js"), "application/javascript")
            return

        # API: Status
        if self.path == "/api/status":
            self._handle_get_status()
        # API: History
        elif self.path == "/api/history":
            self._handle_get_history()
        # API: Branches
        elif self.path == "/api/branches":
            self._handle_get_branches()
        # API: Songs
        elif self.path == "/api/songs":
            self._handle_get_songs()
        # API: Config
        elif self.path == "/api/config":
            self._handle_get_config()
        else:
            self._set_headers("text/plain", 404)
            self.wfile.write(b"Not Found")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = b""
        if content_length > 0:
            post_data = self.rfile.read(content_length)

        data = {}
        if post_data:
            try:
                data = json.loads(post_data.decode('utf-8'))
            except Exception:
                pass

        # API: Toggle Daemon
        if self.path == "/api/daemon/toggle":
            self._handle_post_daemon_toggle()
        # API: Switch Branch
        elif self.path == "/api/branch/switch":
            self._handle_post_branch_switch(data)
        # API: Toggle Lock
        elif self.path == "/api/lock/toggle":
            self._handle_post_lock_toggle(data)
        # API: Checkpoint
        elif self.path == "/api/checkpoint":
            self._handle_post_checkpoint(data)
        # API: Import
        elif self.path == "/api/import":
            self._handle_post_import(data)
        # API: Select Active Song
        elif self.path == "/api/songs/active":
            self._handle_post_active_song(data)
        # API: Save Config
        elif self.path == "/api/config":
            self._handle_post_config(data)
        # API: Sync
        elif self.path == "/api/sync":
            self._handle_post_sync()
        else:
            self._set_headers("application/json", 404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    def _serve_file(self, file_path, content_type):
        if os.path.exists(file_path):
            self._set_headers(content_type)
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self._set_headers("text/plain", 404)
            self.wfile.write(f"File {os.path.basename(file_path)} not found".encode('utf-8'))

    # --- GET API Handlers ---

    def _handle_get_status(self):
        running = hit_cli.is_daemon_running()
        cfg = hit_cli.load_local_config()
        
        # Load songs config
        from hit_sync.config import SONGS_JSON_PATH
        active_proj = "None"
        if os.path.exists(SONGS_JSON_PATH):
            try:
                with open(SONGS_JSON_PATH, "r") as f:
                    song_data = json.load(f)
                    active_proj = song_data.get("active_project", "None")
            except Exception:
                pass

        # Git details
        song_dir = hit_cli.get_active_song_dir()
        branch = "None"
        song_remote = "None"
        is_clean = True
        lock_owner = None
        has_git = False

        if song_dir and os.path.exists(os.path.join(song_dir, ".git")):
            has_git = True
            try:
                # Active branch
                branch = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=song_dir, stderr=subprocess.DEVNULL, text=True
                ).strip()
            except Exception:
                branch = "main"

            try:
                # Remote URL
                song_remote = subprocess.check_output(
                    ["git", "remote", "get-url", "origin"],
                    cwd=song_dir, stderr=subprocess.DEVNULL, text=True
                ).strip()
            except Exception:
                song_remote = "None"

            try:
                # Git status check
                status_output = subprocess.check_output(
                    ["git", "status", "--porcelain"],
                    cwd=song_dir, text=True
                ).strip()
                is_clean = not bool(status_output)
            except Exception:
                is_clean = True

            # Lock status
            try:
                # Check if there is an active lock ref
                # Locking is checked via git ref or a .lock file or git_sync manager
                from hit_sync.git_sync import GitSyncManager
                git_manager = GitSyncManager(song_dir)
                lock_owner = git_manager.get_lock_owner()
            except Exception:
                lock_owner = None

        # Check Google Drive health
        drive_sync_healthy = False
        from hit_sync.config import GOOGLE_CREDENTIALS_PATH
        token_path = os.path.join(os.path.dirname(GOOGLE_CREDENTIALS_PATH), "token.json")
        if os.path.exists(GOOGLE_CREDENTIALS_PATH) and os.path.exists(token_path):
            drive_sync_healthy = True

        response = {
            "daemon_running": running,
            "username": cfg.get("username"),
            "global_remote": cfg.get("remote") or "None",
            "drive_folder": cfg.get("drive_folder"),
            "drive_sync_healthy": drive_sync_healthy,
            "music_dir": cfg.get("music_dir"),
            "active_song": active_proj,
            "song_dir": song_dir,
            "has_git": has_git,
            "branch": branch,
            "song_remote": song_remote,
            "is_clean": is_clean,
            "lock_owner": lock_owner
        }
        self._set_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def _handle_get_history(self):
        song_dir = hit_cli.get_active_song_dir()
        if not song_dir or not os.path.exists(os.path.join(song_dir, ".git")):
            self._set_headers()
            self.wfile.write(json.dumps([]).encode('utf-8'))
            return

        cmd = ["git", "log", "--pretty=format:%h|%an|%ar|%d|%s", "--all", "-n", "30"]
        try:
            result = subprocess.run(cmd, cwd=song_dir, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split("\n")
        except Exception:
            lines = []

        history = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue
            
            commit_hash, author, relative_time, ref_part, message = parts
            
            # Format refs
            ref_list = []
            is_head = False
            ref_part = ref_part.strip()
            if ref_part:
                ref_content = ref_part.lstrip("(").rstrip(")")
                refs = [r.strip() for r in ref_content.split(",")]
                for r in refs:
                    if "HEAD ->" in r:
                        is_head = True
                        ref_list.append(r.replace("HEAD ->", "HEAD 👉"))
                    else:
                        ref_list.append(r)
            
            # Determine commit type
            commit_type = "save"
            clean_msg = message
            if "[HIT Checkpoint]" in message:
                commit_type = "checkpoint"
                clean_msg = message.replace("[HIT Checkpoint]", "").strip()
            elif "[HIT Init]" in message:
                commit_type = "init"
                clean_msg = message.replace("[HIT Init]", "").strip()
            elif "[HIT Sync]" in message:
                commit_type = "sync"
                clean_msg = message.replace("[HIT Sync]", "").strip()

            history.append({
                "hash": commit_hash,
                "author": author,
                "relative_time": relative_time,
                "refs": ref_list,
                "is_head": is_head,
                "message": clean_msg,
                "type": commit_type
            })

        self._set_headers()
        self.wfile.write(json.dumps(history).encode('utf-8'))

    def _handle_get_branches(self):
        song_dir = hit_cli.get_active_song_dir()
        if not song_dir or not os.path.exists(os.path.join(song_dir, ".git")):
            self._set_headers()
            self.wfile.write(json.dumps([]).encode('utf-8'))
            return

        try:
            branches_raw = subprocess.check_output(
                ["git", "branch", "-a"], cwd=song_dir, text=True
            )
            # Find active
            active_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=song_dir, text=True
            ).strip()
            
            branches = []
            seen = set()
            for line in branches_raw.split("\n"):
                line_clean = line.replace("*", "").strip()
                if not line_clean:
                    continue
                
                # Format name
                name = line_clean
                is_remote = False
                if name.startswith("remotes/origin/"):
                    name = name[15:]
                    is_remote = True
                    if name == "HEAD":
                        continue

                if name in seen:
                    continue
                seen.add(name)

                branches.append({
                    "name": name,
                    "is_active": (name == active_branch),
                    "is_remote": is_remote
                })
        except Exception:
            branches = []

        self._set_headers()
        self.wfile.write(json.dumps(branches).encode('utf-8'))

    def _handle_get_songs(self):
        from hit_sync.config import SONGS_JSON_PATH
        songs_data = {"songs": {}, "active_project": "None"}
        if os.path.exists(SONGS_JSON_PATH):
            try:
                with open(SONGS_JSON_PATH, "r") as f:
                    songs_data = json.load(f)
            except Exception:
                pass
        self._set_headers()
        self.wfile.write(json.dumps(songs_data).encode('utf-8'))

    def _handle_get_config(self):
        cfg = hit_cli.load_local_config()
        self._set_headers()
        self.wfile.write(json.dumps(cfg).encode('utf-8'))

    # --- POST API Handlers ---

    def _handle_post_daemon_toggle(self):
        running = hit_cli.is_daemon_running()
        if running:
            success, output = run_cli_capture(hit_cli.stop_daemon)
        else:
            success, output = run_cli_capture(hit_cli.start_daemon)
            
        self._set_headers()
        self.wfile.write(json.dumps({
            "success": success,
            "output": output,
            "running": hit_cli.is_daemon_running()
        }).encode('utf-8'))

    def _handle_post_branch_switch(self, data):
        branch_name = data.get("name")
        if not branch_name:
            self._set_headers(status=400)
            self.wfile.write(json.dumps({"error": "Branch name is required"}).encode('utf-8'))
            return

        success, output = run_cli_capture(hit_cli.manage_branch, branch_name)
        self._set_headers()
        self.wfile.write(json.dumps({
            "success": success,
            "output": output
        }).encode('utf-8'))

    def _handle_post_lock_toggle(self, data):
        # Check current lock state
        song_dir = hit_cli.get_active_song_dir()
        if not song_dir:
            self._set_headers(status=400)
            self.wfile.write(json.dumps({"error": "No active project found"}).encode('utf-8'))
            return
            
        from hit_sync.git_sync import GitSyncManager
        git_manager = GitSyncManager(song_dir)
        lock_owner = git_manager.get_lock_owner()
        
        cfg = hit_cli.load_local_config()
        username = cfg.get("username", os.getlogin())

        if lock_owner:
            success, output = run_cli_capture(hit_cli.manage_lock, "unlock")
        else:
            success, output = run_cli_capture(hit_cli.manage_lock, "lock")
            
        self._set_headers()
        self.wfile.write(json.dumps({
            "success": success,
            "output": output
        }).encode('utf-8'))

    def _handle_post_checkpoint(self, data):
        msg = data.get("message")
        tag = data.get("tag") or None
        
        if not msg:
            self._set_headers(status=400)
            self.wfile.write(json.dumps({"error": "Checkpoint message is required"}).encode('utf-8'))
            return

        success, output = run_cli_capture(hit_cli.manage_checkpoint, msg, tag)
        self._set_headers()
        self.wfile.write(json.dumps({
            "success": success,
            "output": output
        }).encode('utf-8'))

    def _handle_post_import(self, data):
        target = data.get("target")
        if not target:
            self._set_headers(status=400)
            self.wfile.write(json.dumps({"error": "Import target is required"}).encode('utf-8'))
            return

        success, output = run_cli_capture(hit_cli.manage_import, target)
        self._set_headers()
        self.wfile.write(json.dumps({
            "success": success,
            "output": output
        }).encode('utf-8'))

    def _handle_post_active_song(self, data):
        song_name = data.get("name")
        if not song_name:
            self._set_headers(status=400)
            self.wfile.write(json.dumps({"error": "Song name is required"}).encode('utf-8'))
            return

        from hit_sync.config import SONGS_JSON_PATH
        success = False
        output = ""
        if os.path.exists(SONGS_JSON_PATH):
            try:
                with open(SONGS_JSON_PATH, "r") as f:
                    song_data = json.load(f)
                
                if song_name in song_data.get("songs", {}):
                    song_data["active_project"] = song_name
                    with open(SONGS_JSON_PATH, "w") as f:
                        json.dump(song_data, f, indent=2)
                    success = True
                    output = f"Active song updated to: {song_name}"
                    
                    # If daemon is running, restart it to watch the new folder
                    if hit_cli.is_daemon_running():
                        output += "\nRestarting daemon to monitor new project..."
                        hit_cli.stop_daemon()
                        hit_cli.start_daemon()
                else:
                    output = f"Error: Song '{song_name}' not found in catalog."
            except Exception as e:
                output = f"Error updating active song: {e}"
        else:
            output = "Error: songs.json file not found."

        self._set_headers()
        self.wfile.write(json.dumps({
            "success": success,
            "output": output
        }).encode('utf-8'))

    def _handle_post_config(self, data):
        cfg = hit_cli.load_local_config()
        if "username" in data:
            cfg["username"] = data["username"]
        if "remote" in data:
            cfg["remote"] = data["remote"]
        if "drive_folder" in data:
            cfg["drive_folder"] = data["drive_folder"]
        if "music_dir" in data:
            cfg["music_dir"] = data["music_dir"]
            
        hit_cli.save_local_config(cfg)
        self._set_headers()
        self.wfile.write(json.dumps({
            "success": True,
            "output": "Configuration saved successfully."
        }).encode('utf-8'))

    def _handle_post_sync(self):
        success, output = run_cli_capture(hit_cli.force_sync)
        self._set_headers()
        self.wfile.write(json.dumps({
            "success": success,
            "output": output
        }).encode('utf-8'))

def start_server():
    server = HTTPServer(("localhost", PORT), HITHTTPRequestHandler)
    print(f"Server started on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    start_server()
