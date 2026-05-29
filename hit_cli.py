#!/usr/bin/env python3
import os
import sys
import json
import signal
import subprocess
import argparse
from hit_sync.config import HIT_CONFIG_DIR, SONGS_JSON_PATH

PID_FILE = os.path.join(HIT_CONFIG_DIR, "daemon.pid")
LOG_FILE = os.path.join(HIT_CONFIG_DIR, "daemon.log")
CONFIG_FILE = os.path.join(HIT_CONFIG_DIR, "config.json")

# Text Formatting Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def load_local_config():
    default_cfg = {
        "username": os.getlogin(),
        "remote": "",
        "drive_folder": "HIT_DAW_Shared_Projects"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                # Merge loaded configs with defaults
                default_cfg.update(loaded)
                return default_cfg
        except Exception:
            pass
    return default_cfg

def save_local_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"{RED}Error saving config: {e}{RESET}")

def get_daemon_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None

def is_daemon_running():
    pid = get_daemon_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

# --- CLI Commands ---

def start_daemon():
    if is_daemon_running():
        pid = get_daemon_pid()
        print(f"{YELLOW}⚠️ HIT Sync Daemon is already running (PID: {pid}).{RESET}")
        return
        
    cfg = load_local_config()
    username = cfg.get("username", os.getlogin())
    
    print(f"🚀 Starting HIT Sync Daemon for user '{BOLD}{username}{RESET}' in the background...")
    
    # Spawn background daemon process detached from this terminal
    daemon_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hit_daemon.py")
    
    try:
        log_file_handle = open(LOG_FILE, "a")
        # Run process detached
        proc = subprocess.Popen(
            [sys.executable, daemon_script, "--username", username],
            stdout=log_file_handle,
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            close_fds=True,
            start_new_session=True
        )
        
        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
            
        print(f"{GREEN}🟢 Daemon launched successfully! (PID: {proc.pid}){RESET}")
        print(f"Logs are being written to: {CYAN}{LOG_FILE}{RESET}")
    except Exception as e:
        print(f"{RED}❌ Failed to start daemon: {e}{RESET}")

def stop_daemon():
    pid = get_daemon_pid()
    if not is_daemon_running():
        print(f"{YELLOW}⚠️ Daemon is not currently running.{RESET}")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return
        
    print(f"🛑 Stopping HIT Sync Daemon (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait a brief moment for it to shut down
        for _ in range(10):
            try:
                os.kill(pid, 0)
                import time
                time.sleep(0.2)
            except OSError:
                break
        else:
            # Force kill if SIGTERM failed
            os.kill(pid, signal.SIGKILL)
            
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        print(f"{GREEN}🔴 Daemon stopped.{RESET}")
    except Exception as e:
        print(f"{RED}❌ Failed to stop daemon: {e}{RESET}")

def print_status():
    running = is_daemon_running()
    pid = get_daemon_pid()
    cfg = load_local_config()
    
    print(f"📡 {BOLD}HIT System Status:{RESET}")
    print("-" * 50)
    
    if running:
        print(f"Daemon:      {GREEN}RUNNING{RESET} (PID: {pid})")
    else:
        print(f"Daemon:      {RED}STOPPED{RESET}")
        
    print(f"Username:    {cfg.get('username')}")
    print(f"Remote Git:  {cfg.get('remote') or 'None (Not configured)'}")
    
    # Query Git repo info in Music folder
    from hit_sync.config import MUSIC_DIR
    if os.path.exists(os.path.join(MUSIC_DIR, ".git")):
        try:
            # Active branch
            try:
                branch = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=MUSIC_DIR, stderr=subprocess.DEVNULL, text=True
                ).strip()
            except subprocess.CalledProcessError:
                branch = "master (No commits yet)"
            
            # Active project (from songs.json)
            active_proj = "None"
            if os.path.exists(SONGS_JSON_PATH):
                with open(SONGS_JSON_PATH, "r") as f:
                    song_data = json.load(f)
                    active_proj = song_data.get("active_project", "None")
                    
            print(f"Active Song: {CYAN}{active_proj}{RESET}")
            print(f"Git Branch:  {YELLOW}{branch}{RESET}")
            
            # Git status check
            status_output = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=MUSIC_DIR, text=True
            ).strip()
            if status_output:
                print(f"Uncommitted Changes: {YELLOW}Yes (Local changes pending sync){RESET}")
            else:
                print(f"Local State: {GREEN}Clean & In Sync{RESET}")
                
        except Exception:
            pass
    else:
        print(f"{RED}No Git Repository initialized in {MUSIC_DIR}{RESET}")

def force_sync():
    print("🔄 Triggering manual sync check...")
    cfg = load_local_config()
    username = cfg.get("username", os.getlogin())
    
    # Import and run the daemon sync routine once synchronously
    from hit_daemon import HITAbletonSyncDaemon
    try:
        daemon = HITAbletonSyncDaemon(username)
        # Pull updates
        daemon.sync_incoming_updates()
        print(f"{GREEN}✅ Sync check finished.{RESET}")
    except Exception as e:
        print(f"{RED}❌ Sync failed: {e}{RESET}")

def manage_lock(lock_cmd):
    cfg = load_local_config()
    username = cfg.get("username", os.getlogin())
    
    from hit_sync.git_sync import GitSyncManager
    from hit_sync.config import MUSIC_DIR
    git_manager = GitSyncManager(MUSIC_DIR)
    
    if lock_cmd == "lock":
        success, owner = git_manager.acquire_lock(username)
        if success:
            print(f"{GREEN}🔒 Lock acquired successfully! You now have exclusive editing rights.{RESET}")
        else:
            print(f"{RED}❌ Lock denied. Project is currently locked by: {BOLD}{owner}{RESET}")
    elif lock_cmd == "unlock":
        success = git_manager.release_lock(username)
        if success:
            print(f"{GREEN}🔓 Project unlocked successfully. Others can now edit.{RESET}")
        else:
            print(f"{RED}❌ Unlock failed. Check if you are the lock owner.{RESET}")

def manage_branch(branch_name=None):
    from hit_sync.config import MUSIC_DIR
    
    if not os.path.exists(os.path.join(MUSIC_DIR, ".git")):
        print(f"{RED}Error: Music folder is not a Git repository.{RESET}")
        return
        
    if branch_name is None:
        # List branches
        try:
            branches = subprocess.check_output(
                ["git", "branch", "-a"], cwd=MUSIC_DIR, text=True
            )
            print(f"{BOLD}Active Collaboration Branches:{RESET}")
            print(branches)
        except Exception as e:
            print(f"{RED}Error listing branches: {e}{RESET}")
    else:
        # Normalize branch name to collab/
        full_branch_name = branch_name
        if not branch_name.startswith("collab/"):
            cfg = load_local_config()
            username = cfg.get("username", os.getlogin())
            full_branch_name = f"collab/{username}-{branch_name}"
            
        print(f"Switching to collaboration branch: {YELLOW}{full_branch_name}{RESET}...")
        
        # Check if branch exists
        try:
            # Fetch remote branches first
            subprocess.run(["git", "fetch", "origin"], cwd=MUSIC_DIR, capture_output=True)
            
            # Checkout branch (create if not exist)
            result = subprocess.run(
                ["git", "checkout", full_branch_name],
                cwd=MUSIC_DIR, capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"Creating new collaboration branch: {GREEN}{full_branch_name}{RESET}...")
                subprocess.run(
                    ["git", "checkout", "-b", full_branch_name],
                    cwd=MUSIC_DIR, check=True
                )
            print(f"{GREEN}Checked out branch '{full_branch_name}' successfully.{RESET}")
        except Exception as e:
            print(f"{RED}Failed to switch branch: {e}{RESET}")

def manage_config(args):
    cfg = load_local_config()
    
    # Check if we should run the interactive wizard (no flags provided)
    if not (args.username or args.remote or args.drive_folder):
        print(f"{BOLD}HIT Configuration Wizard{RESET}")
        print("Press Enter to keep the current value shown in brackets.\n")
        
        # 1. Username
        current_username = cfg.get("username", os.getlogin())
        user_input = input(f"Username [{current_username}]: ").strip()
        if user_input:
            cfg["username"] = user_input
            print(f"Username updated to: {GREEN}{user_input}{RESET}")
            
        # 2. Git Remote
        current_remote = cfg.get("remote", "")
        remote_input = input(f"Git Remote URL [{current_remote or 'None'}]: ").strip()
        if remote_input:
            cfg["remote"] = remote_input
            print(f"Remote Git URL updated to: {GREEN}{remote_input}{RESET}")
            from hit_sync.config import MUSIC_DIR
            try:
                subprocess.run(["git", "remote", "remove", "origin"], cwd=MUSIC_DIR, capture_output=True)
                subprocess.run(["git", "remote", "add", "origin", remote_input], cwd=MUSIC_DIR, check=True)
                print(f"Git remote 'origin' configured successfully.")
            except Exception as e:
                print(f"{YELLOW}Warning: Could not configure Git remote 'origin': {e}{RESET}")
                
        # 3. Drive Folder
        current_folder = cfg.get("drive_folder", "HIT_DAW_Shared_Projects")
        folder_input = input(f"Google Drive Shared Folder Name [{current_folder}]: ").strip()
        if folder_input:
            cfg["drive_folder"] = folder_input
            print(f"Google Drive folder updated to: {GREEN}{folder_input}{RESET}")
            
        save_local_config(cfg)
        print(f"\n{GREEN}✓ Configurations saved successfully!{RESET}")
    else:
        # Non-interactive mode (flags provided)
        if args.username:
            cfg["username"] = args.username
            print(f"Username updated to: {GREEN}{args.username}{RESET}")
            
        if args.remote:
            cfg["remote"] = args.remote
            print(f"Remote Git URL updated to: {GREEN}{args.remote}{RESET}")
            from hit_sync.config import MUSIC_DIR
            try:
                subprocess.run(["git", "remote", "remove", "origin"], cwd=MUSIC_DIR, capture_output=True)
                subprocess.run(["git", "remote", "add", "origin", args.remote], cwd=MUSIC_DIR, check=True)
                print(f"Git remote 'origin' configured successfully.")
            except Exception as e:
                print(f"{YELLOW}Warning: Could not configure Git remote 'origin': {e}{RESET}")
                
        if args.drive_folder:
            cfg["drive_folder"] = args.drive_folder
            print(f"Google Drive folder updated to: {GREEN}{args.drive_folder}{RESET}")
            
        save_local_config(cfg)
    
    print(f"\n{BOLD}Current Configurations:{RESET}")
    print(f"  Username:     {cfg.get('username')}")
    print(f"  Remote:       {cfg.get('remote') or 'Not configured'}")
    print(f"  Drive Folder: {cfg.get('drive_folder')}")

def main():
    parser = argparse.ArgumentParser(description="HIT Ableton Live Sync Manager CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # Daemon controls
    subparsers.add_parser("start", help="Start background sync daemon")
    subparsers.add_parser("stop", help="Stop background sync daemon")
    subparsers.add_parser("restart", help="Restart background sync daemon")
    subparsers.add_parser("status", help="Show system status")
    subparsers.add_parser("sync", help="Trigger manual project sync")
    
    # Lock controls
    subparsers.add_parser("lock", help="Acquire editing lock on current branch")
    subparsers.add_parser("unlock", help="Release editing lock")
    
    # Branch controls
    branch_parser = subparsers.add_parser("branch", help="Switch or list branches")
    branch_parser.add_argument("name", nargs="?", help="Name of the branch to switch/create")
    
    # Config controls
    config_parser = subparsers.add_parser("config", help="Manage settings")
    config_parser.add_argument("--username", help="Set collaborator username")
    config_parser.add_argument("--remote", help="Set Git remote repository URL")
    config_parser.add_argument("--drive-folder", help="Set custom Google Drive shared folder name")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_daemon()
    elif args.command == "stop":
        stop_daemon()
    elif args.command == "restart":
        stop_daemon()
        start_daemon()
    elif args.command == "status":
        print_status()
    elif args.command == "sync":
        force_sync()
    elif args.command in ["lock", "unlock"]:
        manage_lock(args.command)
    elif args.command == "branch":
        manage_branch(args.name)
    elif args.command == "config":
        manage_config(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
