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
        "username": "claytonwashington",
        "remote": "",
        "drive_folder": "HIT_DAW_Shared_Projects",
        "music_dir": os.path.expanduser("~/Desktop/Music")
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

def get_active_song_dir():
    from hit_sync.config import MUSIC_DIR, SONGS_JSON_PATH
    if os.path.exists(SONGS_JSON_PATH):
        try:
            with open(SONGS_JSON_PATH, "r") as f:
                song_data = json.load(f)
                active_proj = song_data.get("active_project")
                if active_proj:
                    proj_path = os.path.join(MUSIC_DIR, active_proj)
                    if os.path.isdir(proj_path):
                        return proj_path
                    # Also check if it's named with " Project" suffix
                    for d in os.listdir(MUSIC_DIR):
                        if d.lower() == active_proj.lower() or d.lower().replace(" project", "") == active_proj.lower():
                            return os.path.join(MUSIC_DIR, d)
        except Exception:
            pass
    return None

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
    print(f"Global Git Remote: {cfg.get('remote') or 'None (Not configured)'}")
    
    # Active project (from songs.json)
    from hit_sync.config import SONGS_JSON_PATH
    active_proj = "None"
    if os.path.exists(SONGS_JSON_PATH):
        try:
            with open(SONGS_JSON_PATH, "r") as f:
                song_data = json.load(f)
                active_proj = song_data.get("active_project", "None")
        except Exception:
            pass
            
    print(f"Active Song: {CYAN}{active_proj}{RESET}")
    
    # Query Git repo info in the active song folder
    song_dir = get_active_song_dir()
    if song_dir and os.path.exists(os.path.join(song_dir, ".git")):
        try:
            # Active branch
            try:
                branch = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=song_dir, stderr=subprocess.DEVNULL, text=True
                ).strip()
            except subprocess.CalledProcessError:
                branch = "master (No commits yet)"
            
            # Remote URL for this song
            try:
                song_remote = subprocess.check_output(
                    ["git", "remote", "get-url", "origin"],
                    cwd=song_dir, stderr=subprocess.DEVNULL, text=True
                ).strip()
            except subprocess.CalledProcessError:
                song_remote = "None (Not configured)"

            print(f"Song Remote: {song_remote}")
            print(f"Git Branch:  {YELLOW}{branch}{RESET}")
            
            # Git status check
            status_output = subprocess.check_output(
                ["git", "status", "--porcelain", "-uno"],
                cwd=song_dir, text=True
            ).strip()
            has_unsaved_als = False
            for line in status_output.splitlines():
                cleaned_line = line.strip()
                if cleaned_line.endswith(".als") and not cleaned_line.startswith("??"):
                    has_unsaved_als = True
                    break
            
            if has_unsaved_als:
                print(f"Uncommitted Changes: {YELLOW}Yes (Unsaved Ableton set changes pending sync){RESET}")
            else:
                print(f"Local State: {GREEN}Clean & In Sync{RESET}")
                
        except Exception as e:
            print(f"{RED}Error reading Git status: {e}{RESET}")
    else:
        if active_proj == "None":
            print(f"{YELLOW}No active song set. Use song_manager.py to set active project.{RESET}")
        else:
            print(f"{RED}No Git Repository initialized in active song directory: {song_dir or 'None'}{RESET}")

def force_sync():
    print("🔄 Triggering manual sync check...")
    cfg = load_local_config()
    username = cfg.get("username", os.getlogin())
    
    # Import and run the daemon sync routine once synchronously
    from hit_daemon import HITAbletonSyncDaemon
    try:
        daemon = HITAbletonSyncDaemon(username)
        # Pull updates from git and download samples from Drive
        daemon.sync_incoming_updates()
        
        # Push any local commits to remote git
        song_dir = get_active_song_dir()
        if song_dir and os.path.exists(os.path.join(song_dir, ".git")):
            from hit_sync.git_sync import GitSyncManager
            git_manager = GitSyncManager(song_dir)
            print("📤 Pushing local commits to remote...")
            success, output = git_manager.push()
            if not success:
                print(f"{YELLOW}⚠️ Push skipped or failed: {output}{RESET}")
                
        print(f"{GREEN}✅ Sync check finished.{RESET}")
    except Exception as e:
        print(f"{RED}❌ Sync failed: {e}{RESET}")

def manage_lock(lock_cmd):
    cfg = load_local_config()
    username = cfg.get("username", os.getlogin())
    
    song_dir = get_active_song_dir()
    if not song_dir or not os.path.exists(os.path.join(song_dir, ".git")):
        print(f"{RED}Error: Active project directory is not a Git repository.{RESET}")
        return
        
    from hit_sync.git_sync import GitSyncManager
    git_manager = GitSyncManager(song_dir)
    
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
    song_dir = get_active_song_dir()
    if not song_dir or not os.path.exists(os.path.join(song_dir, ".git")):
        print(f"{RED}Error: Active project directory is not a Git repository.{RESET}")
        return
        
    if branch_name is None:
        # List branches
        try:
            branches = subprocess.check_output(
                ["git", "branch", "-a"], cwd=song_dir, text=True
            )
            print(f"{BOLD}Active Collaboration Branches:{RESET}")
            print(branches)
        except Exception as e:
            print(f"{RED}Error listing branches: {e}{RESET}")
    else:
        # Fetch remote branches first to populate our branches list
        try:
            subprocess.run(["git", "fetch", "origin"], cwd=song_dir, capture_output=True)
        except Exception:
            pass

        # Determine the full branch name dynamically
        full_branch_name = branch_name
        branch_exists = False
        try:
            # List all branches (local and remote)
            all_branches_raw = subprocess.check_output(
                ["git", "branch", "-a"], cwd=song_dir, text=True
            )
            # Parse branches to list of clean names
            all_branches = []
            for b in all_branches_raw.split("\n"):
                b_clean = b.replace("*", "").strip()
                if b_clean:
                    # Strip remotes/origin/ prefix for comparison
                    if b_clean.startswith("remotes/origin/"):
                        all_branches.append(b_clean[15:])
                    all_branches.append(b_clean)
            
            # Check if exact match or common prefix matches exist
            if branch_name in all_branches:
                full_branch_name = branch_name
                branch_exists = True
            elif f"collab/{branch_name}" in all_branches:
                full_branch_name = f"collab/{branch_name}"
                branch_exists = True
            else:
                # Also check if it exists as collab/[username]-branch_name
                cfg = load_local_config()
                username = cfg.get("username", os.getlogin())
                prefixed_name = f"collab/{username}-{branch_name}"
                if prefixed_name in all_branches:
                    full_branch_name = prefixed_name
                    branch_exists = True
        except Exception:
            pass

        if not branch_exists:
            # If it doesn't match an existing branch, create it under the user's namespace
            if branch_name in ["main", "master"]:
                full_branch_name = branch_name
            elif branch_name.startswith("collab/"):
                full_branch_name = branch_name
            else:
                cfg = load_local_config()
                username = cfg.get("username", os.getlogin())
                if branch_name.startswith(f"{username}-"):
                    full_branch_name = f"collab/{branch_name}"
                else:
                    full_branch_name = f"collab/{username}-{branch_name}"
            
        print(f"Switching to collaboration branch: {YELLOW}{full_branch_name}{RESET}...")
        
        # Check if branch exists
        try:
            # Checkout branch (create if not exist)
            result = subprocess.run(
                ["git", "checkout", full_branch_name],
                cwd=song_dir, capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"Creating new collaboration branch: {GREEN}{full_branch_name}{RESET}...")
                subprocess.run(
                    ["git", "checkout", "-b", full_branch_name],
                    cwd=song_dir, check=True
                )
                print(f"Publishing new branch to remote origin...")
                subprocess.run(
                    ["git", "push", "-u", "origin", full_branch_name],
                    cwd=song_dir, check=True
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
                
        if args.drive_folder:
            cfg["drive_folder"] = args.drive_folder
            print(f"Google Drive folder updated to: {GREEN}{args.drive_folder}{RESET}")
            
        save_local_config(cfg)
    
    print(f"\n{BOLD}Current Configurations:{RESET}")
    print(f"  Username:     {cfg.get('username')}")
    print(f"  Remote:       {cfg.get('remote') or 'Not configured'}")
    print(f"  Drive Folder: {cfg.get('drive_folder')}")

def manage_checkpoint(message=None, tag=None):
    """Amend the last auto-saved commit with a custom message and optionally tag the commit."""
    song_dir = get_active_song_dir()
    if not song_dir or not os.path.exists(os.path.join(song_dir, ".git")):
        print(f"{RED}Error: Active project directory is not a Git repository.{RESET}")
        return
        
    try:
        # Check if there are any commits in the repository
        try:
            current_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=song_dir, stderr=subprocess.DEVNULL, text=True
            ).strip()
            subprocess.check_call(
                ["git", "rev-parse", "HEAD"],
                cwd=song_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            print(f"{RED}Error: No commits found. Please save your project in Ableton first to create an initial save.{RESET}")
            return

        # 1. Prompt for message if not provided
        if not message:
            print(f"{BOLD}Creating Checkpoint for {CYAN}{os.path.basename(song_dir)}{RESET}")
            message = input("Enter checkpoint description (amends last save): ").strip()
            if not message:
                print(f"{YELLOW}Warning: Checkpoint description is required.{RESET}")
                return

        formatted_message = f"[HIT Checkpoint] {message}"
        
        # 2. Amend the last commit
        print(f"Amending last commit with message: '{formatted_message}'...")
        subprocess.run(
            ["git", "commit", "--amend", "-m", formatted_message],
            cwd=song_dir, check=True
        )
        print(f"{GREEN}✓ Last save amended successfully.{RESET}")

        # 3. Prompt for tag if not provided in args
        if tag is None:
            tag_input = input("Enter tag name (e.g. v1.0, press Enter to skip): ").strip()
            if tag_input:
                tag = tag_input

        # 4. Create tag if specified
        if tag:
            print(f"Tagging commit as '{tag}'...")
            subprocess.run(["git", "tag", "-d", tag], cwd=song_dir, capture_output=True)
            subprocess.run(["git", "tag", tag], cwd=song_dir, check=True)
            print(f"{GREEN}✓ Tag '{tag}' created successfully.{RESET}")

        # 5. Push changes to GitHub
        print("📤 Pushing checkpoint to GitHub...")
        subprocess.run(
            ["git", "push", "-f", "origin", current_branch],
            cwd=song_dir, check=True
        )
        
        if tag:
            print(f"📤 Pushing tag '{tag}' to GitHub...")
            subprocess.run(
                ["git", "push", "origin", tag, "--force"],
                cwd=song_dir, check=True
            )
            
        print(f"\n{GREEN}🎉 SUCCESS! Checkpoint created and pushed to GitHub!{RESET}")
        if tag:
            print(f"Tag checkpoint: {BOLD}{CYAN}git checkout {tag}{RESET}")
            
    except Exception as e:
        print(f"{RED}❌ Checkpoint failed: {e}{RESET}")

def manage_history(count=15):
    """Show a simplified, color-coded timeline of commits and checkpoints."""
    song_dir = get_active_song_dir()
    if not song_dir or not os.path.exists(os.path.join(song_dir, ".git")):
        print(f"{RED}Error: Active project directory is not a Git repository.{RESET}")
        return

    import subprocess
    cmd = ["git", "log", f"--pretty=format:%h|%an|%ar|%d|%s", "--all", "-n", str(count)]
    try:
        result = subprocess.run(cmd, cwd=song_dir, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running git log: {e.stderr or e.stdout}{RESET}")
        return

    if not lines or not lines[0].strip():
        print(f"{YELLOW}No history found in active song directory.{RESET}")
        return

    cfg = load_local_config()
    local_user = cfg.get("username", "").lower()

    MAGENTA = "\033[95m"
    DARK_GRAY = "\033[90m"
    LIGHT_GRAY = "\033[37m"

    print(f"\n🎼 {BOLD}HIT Song History: {CYAN}{os.path.basename(song_dir)}{RESET}")
    print("─" * 60)

    for line in lines:
        if not line.strip():
            continue
        parts = line.split("|", 4)
        if len(parts) < 5:
            continue
        
        commit_hash, author, relative_time, ref_part, message = parts
        
        # Format refs
        ref_str = ""
        ref_part = ref_part.strip()
        is_current_head = False
        if ref_part:
            ref_content = ref_part.lstrip("(").rstrip(")")
            refs = [r.strip() for r in ref_content.split(",")]
            formatted_refs = []
            for r in refs:
                if "HEAD ->" in r:
                    is_current_head = True
                    formatted_refs.append(f"{BOLD}{YELLOW}👉 {r}{RESET}")
                elif r.startswith("tag: "):
                    tag_name = r[5:]
                    formatted_refs.append(f"{CYAN}🏷️  {tag_name}{RESET}")
                else:
                    formatted_refs.append(f"{YELLOW}{r}{RESET}")
            ref_str = f"({', '.join(formatted_refs)})"
            
        # Format author
        if author.lower() == local_user or local_user in author.lower():
            author_formatted = f"{GREEN}{author} (You){RESET}"
        else:
            author_formatted = f"{MAGENTA}{author}{RESET}"
            
        # Format message icon and prefix
        msg_formatted = message
        icon = "🟢"
        if "[HIT Checkpoint]" in message:
            icon = "✨"
            msg_content = message.replace("[HIT Checkpoint]", "").strip()
            msg_formatted = f"{BOLD}{CYAN}[Checkpoint] {msg_content}{RESET}"
        elif "[HIT Init]" in message:
            icon = "🎬"
            msg_content = message.replace("[HIT Init]", "").strip()
            msg_formatted = f"{BOLD}{GREEN}[Init] {msg_content}{RESET}"
        elif "[HIT Sync]" in message:
            icon = "💾"
            msg_content = message.replace("[HIT Sync]", "").strip()
            msg_formatted = f"{msg_content}"
            
        ref_suffix = f" {ref_str}" if ref_str else ""
        
        # Build timeline node
        node_char = "●"
        if is_current_head:
            node_char = f"{BOLD}{YELLOW}▶{RESET}"
        elif "[HIT Checkpoint]" in message:
            node_char = f"{CYAN}★{RESET}"
            
        print(f" {node_char}  {BOLD}{DARK_GRAY}[{commit_hash}]{RESET}  {LIGHT_GRAY}({relative_time}){RESET}{ref_suffix}")
        print(f"    └─ {author_formatted}: {icon} {msg_formatted}\n")

def manage_import(target):
    """Import a collaborator's version of the Ableton set as a side-file."""
    song_dir = get_active_song_dir()
    if not song_dir or not os.path.exists(os.path.join(song_dir, ".git")):
        print(f"{RED}Error: Active project directory is not a Git repository.{RESET}")
        return

    # 1. Fetch updates from origin
    print("🔄 Fetching updates from remote origin...")
    try:
        subprocess.run(["git", "fetch", "origin"], cwd=song_dir, capture_output=True, text=True)
    except Exception as e:
        print(f"{YELLOW}Warning: Failed to fetch from remote origin: {e}{RESET}")

    # 2. Get list of branches
    try:
        branches_raw = subprocess.check_output(
            ["git", "branch", "-a"], cwd=song_dir, text=True
        )
        all_branches = []
        for line in branches_raw.split("\n"):
            line = line.replace("*", "").strip()
            if not line:
                continue
            all_branches.append(line)
    except Exception as e:
        print(f"{RED}Error listing branches: {e}{RESET}")
        return

    # 3. Resolve target branch
    resolved_branch = None
    target_lower = target.lower()
    
    exact_candidates = [
        target,
        f"collab/{target}",
        f"remotes/origin/{target}",
        f"remotes/origin/collab/{target}"
    ]
    for cand in exact_candidates:
        if cand in all_branches:
            resolved_branch = cand
            break
            
    if not resolved_branch:
        # Check local collab branches
        for b in all_branches:
            if not b.startswith("remotes/") and "collab/" in b and target_lower in b.lower():
                resolved_branch = b
                break
        if not resolved_branch:
            # Check remote collab branches
            for b in all_branches:
                if b.startswith("remotes/") and "collab/" in b and target_lower in b.lower():
                    resolved_branch = b
                    break
        if not resolved_branch:
            # Check any branch
            for b in all_branches:
                if target_lower in b.lower():
                    resolved_branch = b
                    break

    if not resolved_branch:
        print(f"{RED}Error: Could not resolve branch or collaborator matching '{target}'.{RESET}")
        print("Available branches:")
        for b in all_branches:
            print(f"  {b}")
        return
        
    print(f"🎯 Resolved target to branch: {YELLOW}{resolved_branch}{RESET}")

    # 4. Find active song's main .als file
    from hit_sync.config import SONGS_JSON_PATH
    active_als_filename = None
    if os.path.exists(SONGS_JSON_PATH):
        try:
            with open(SONGS_JSON_PATH, "r") as f:
                song_data = json.load(f)
                active_proj = song_data.get("active_project")
                if active_proj and "songs" in song_data and active_proj in song_data["songs"]:
                    relative_als = song_data["songs"][active_proj].get("path")
                    if relative_als:
                        active_als_filename = os.path.basename(relative_als)
        except Exception as e:
            print(f"{YELLOW}Warning: Error reading active song filename: {e}{RESET}")
            
    if not active_als_filename:
        als_files = [f for f in os.listdir(song_dir) if f.endswith(".als") and "_collab_" not in f]
        if als_files:
            active_als_filename = als_files[0]
            
    if not active_als_filename:
        print(f"{RED}Error: Could not find main .als file in project.{RESET}")
        return

    # 5. Extract the file contents from Git
    git_show_path = f"{resolved_branch}:{active_als_filename}"
    print(f"📖 Extracting {active_als_filename} from {YELLOW}{resolved_branch}{RESET}...")
    try:
        xml_bytes = subprocess.check_output(
            ["git", "show", git_show_path],
            cwd=song_dir, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode(errors='replace').strip()
        print(f"{RED}Error extracting file from git: {error_msg}{RESET}")
        return

    # Ensure Ableton XML header is present
    if not xml_bytes.startswith(b"<?xml"):
        xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes

    # 6. Clean branch name for file name (e.g. remotes/origin/collab/nik-vox -> nik-vox)
    branch_clean = resolved_branch
    if branch_clean.startswith("remotes/origin/"):
        branch_clean = branch_clean[15:]
    if branch_clean.startswith("collab/"):
        branch_clean = branch_clean[7:]
    branch_clean = branch_clean.replace("/", "_")

    song_name = active_als_filename[:-4] if active_als_filename.endswith(".als") else active_als_filename
    output_filename = f"{song_name}_collab_{branch_clean}.als"
    output_path = os.path.join(song_dir, output_filename)

    # 7. Compress and write
    import gzip
    print(f"💾 Saving imported set to: {CYAN}{output_filename}{RESET}...")
    try:
        with open(output_path, "wb") as f_out:
            with gzip.GzipFile(filename="project.als", mode="wb", fileobj=f_out) as gz:
                gz.write(xml_bytes)
        print(f"{GREEN}🟢 Collaboration set imported successfully!{RESET}")
        
        # 8. Add to .gitignore if not present
        gitignore_path = os.path.join(song_dir, ".gitignore")
        ignore_pattern = "*_collab_*.als"
        try:
            lines_git = []
            if os.path.exists(gitignore_path):
                with open(gitignore_path, "r") as f_git:
                    lines_git = f_git.read().splitlines()
            if ignore_pattern not in lines_git:
                with open(gitignore_path, "a") as f_git:
                    if lines_git and not lines_git[-1].strip() == "":
                        f_git.write("\n")
                    f_git.write(f"{ignore_pattern}\n")
        except Exception as e:
            print(f"{YELLOW}Warning: Could not update .gitignore: {e}{RESET}")
    except Exception as e:
        print(f"{RED}Error saving imported file: {e}{RESET}")
        return

    print("\n💡 " + BOLD + "How to use this imported set in Ableton Live:" + RESET)
    print("1. Open your main set in Ableton Live.")
    print(f"2. In Ableton's browser sidebar, click 'Add Folder...' and select your project directory:")
    print(f"   {CYAN}{song_dir}{RESET}")
    print(f"3. In the sidebar, expand the imported file: {BOLD}{output_filename}{RESET}")
    print("4. You will see all of your collaborator's tracks, groups, and master chain listed.")
    print("5. Drag and drop any track directly into your current project to merge their work conflict-free!")

def manage_gui():
    """Launch the local HIT Web GUI server and open it in the default browser."""
    import webbrowser
    import time
    import threading
    from hit_gui import start_server, PORT
    
    print(f"\n🌐 {BOLD}Starting HIT Ableton Sync Web GUI...{RESET}")
    print(f"Server is running on: {CYAN}http://localhost:{PORT}{RESET}")
    print(f"Press {YELLOW}Ctrl+C{RESET} in this terminal to shut down the GUI server.\n")

    # Start the server in a daemon thread so it runs in background
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # Wait 0.5 seconds for server socket to bind, then open browser
    time.sleep(0.5)
    webbrowser.open(f"http://localhost:{PORT}")

    # Keep the main thread alive so the server doesn't exit immediately
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down HIT Web GUI server...")

def clone_project(git_url):
    """Clone a collaboration song repository into ~/Desktop/Music and configure its Ableton settings."""
    from hit_sync.config import MUSIC_DIR
    
    # Extract project name from Git URL (e.g. git@github.com:clay/my-project.git -> my-project)
    project_name = git_url.split("/")[-1]
    if project_name.endswith(".git"):
        project_name = project_name[:-4]
        
    target_dir = os.path.join(MUSIC_DIR, project_name)
    if os.path.exists(target_dir):
        print(f"{RED}Error: Directory {target_dir} already exists.{RESET}")
        return
        
    print(f"📥 Cloning song repository: {CYAN}{git_url}{RESET}...")
    try:
        subprocess.run(["git", "clone", git_url, target_dir], check=True)
        print(f"{GREEN}✓ Cloned successfully into {target_dir}{RESET}")
        
        # Configure Ableton Live Set XML clean/smudge filters inside the cloned repository
        print("⚙️  Configuring Ableton XML Git filters...")
        subprocess.run(["git", "config", "filter.als.clean", "gzip -d -c"], cwd=target_dir, check=True)
        subprocess.run(["git", "config", "filter.als.smudge", "python3 -c \"import sys, gzip; data = sys.stdin.buffer.read(); xml = data if data.startswith(b'<?xml') else b'<?xml version=\\\"1.0\\\" encoding=\\\"UTF-8\\\"?>\\n' + data; f = gzip.GzipFile(filename='project.als', mode='wb', fileobj=sys.stdout.buffer); f.write(xml); f.close()\""], cwd=target_dir, check=True)
        print(f"{GREEN}✓ Ableton filters configured successfully.{RESET}")
        
        # Trigger song manager sync to register the new project in songs.json
        print("📇 Registering project in songs catalog...")
        subprocess.run([sys.executable, "/Users/claywashington/Desktop/Music/song_manager.py", "sync"], capture_output=True)
        print(f"{GREEN}🎉 Project '{project_name}' is ready! Run 'hit start' to begin collaborating.{RESET}")
    except Exception as e:
        print(f"{RED}❌ Cloning failed: {e}{RESET}")

def create_project(project_folder):
    """Initialize a local project as a collaborative Git repository and publish it to GitHub using the 'gh' CLI."""
    from hit_sync.config import MUSIC_DIR
    
    target_dir = os.path.join(MUSIC_DIR, project_folder)
    if not os.path.exists(target_dir):
        # Create folder if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        print(f"Created new project directory: {target_dir}")
        
    print(f"🎬 Initializing project '{BOLD}{project_folder}{RESET}' as a collaborative HIT repository...")
    
    # 1. git init
    try:
        subprocess.run(["git", "init"], cwd=target_dir, check=True)
        # Rename default branch to main
        subprocess.run(["git", "branch", "-M", "main"], cwd=target_dir, check=True)
        
        # 2. Configure local git filters
        subprocess.run(["git", "config", "filter.als.clean", "gzip -d -c"], cwd=target_dir, check=True)
        subprocess.run(["git", "config", "filter.als.smudge", "python3 -c \"import sys, gzip; data = sys.stdin.buffer.read(); xml = data if data.startswith(b'<?xml') else b'<?xml version=\\\"1.0\\\" encoding=\\\"UTF-8\\\"?>\\n' + data; f = gzip.GzipFile(filename='project.als', mode='wb', fileobj=sys.stdout.buffer); f.write(xml); f.close()\""], cwd=target_dir, check=True)
        
        # 3. Write default .gitattributes
        with open(os.path.join(target_dir, ".gitattributes"), "w") as f:
            f.write("*.als filter=als\n")
            f.write("*.wav filter=lfs diff=lfs merge=lfs -text\n")
            f.write("*.aif filter=lfs diff=lfs merge=lfs -text\n")
            f.write("*.mp3 filter=lfs diff=lfs merge=lfs -text\n")
            f.write("*.flac filter=lfs diff=lfs merge=lfs -text\n")
            
        # 4. Write default .gitignore
        with open(os.path.join(target_dir, ".gitignore"), "w") as f:
            f.write("**/Backup/\n")
            f.write("*.tmp\n")
            f.write("* [Crash Recovery] *\n")
            f.write(".DS_Store\n")
            
        # 5. First commit
        subprocess.run(["git", "add", "."], cwd=target_dir, check=True)
        commit_res = subprocess.run(
            ["git", "commit", "-m", "[HIT Init] Setup Ableton Live collaboration repository"],
            cwd=target_dir, capture_output=True, text=True
        )
        if commit_res.returncode != 0:
            # If the error is just "nothing to commit", we can safely ignore it and proceed
            if "nothing to commit" in commit_res.stdout or "nothing to commit" in commit_res.stderr:
                print("Working tree is already clean. Proceeding...")
            else:
                raise Exception(f"Git commit failed: {commit_res.stderr or commit_res.stdout}")
        
        # 6. Publish to GitHub using 'gh' CLI
        print(f"☁️  Publishing private repository to GitHub (claytonwashington)...")
        # Check if remote origin already exists
        remote_check = subprocess.run(["git", "remote", "get-url", "origin"], cwd=target_dir, capture_output=True, text=True)
        if remote_check.returncode != 0:
            subprocess.run(
                ["/opt/homebrew/bin/gh", "repo", "create", project_folder, "--private", "--source=.", "--push"],
                cwd=target_dir, check=True
            )
        else:
            print("Remote 'origin' already exists. Pushing changes...")
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=target_dir, check=True)
        
        # Get remote URL
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=target_dir, text=True
        ).strip()
        
        # Trigger song manager sync to register the new project
        subprocess.run([sys.executable, "/Users/claywashington/Desktop/Music/song_manager.py", "sync"], capture_output=True)
        
        print(f"\n{GREEN}🎉 SUCCESS! Collaborative repository created on GitHub!{RESET}")
        print(f"Share this link with your friends to let them join:")
        print(f"👉 {BOLD}{CYAN}hit clone {remote_url}{RESET}")
        
    except Exception as e:
        print(f"{RED}❌ Project creation failed: {e}{RESET}")
        print(f"{YELLOW}Make sure you are logged in to GitHub CLI by running 'gh auth login' first.{RESET}")

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
    
    # Clone and Create controls
    clone_parser = subparsers.add_parser("clone", help="Clone a song repository and register it")
    clone_parser.add_argument("url", help="Git remote repository URL to clone")
    
    create_parser = subparsers.add_parser("create", help="Create a new song repository and push to GitHub")
    create_parser.add_argument("project_folder", help="Name of the project folder to initialize")
    
    # Checkpoint controls
    checkpoint_parser = subparsers.add_parser("checkpoint", help="Label the last save and optionally tag it")
    checkpoint_parser.add_argument("-m", "--message", help="Custom message for the checkpoint (amends last save)")
    checkpoint_parser.add_argument("-t", "--tag", help="Optional Git tag for this version (e.g., v1.0)")
    
    # History controls
    history_parser = subparsers.add_parser("history", help="Show simplified, color-coded commit and checkpoint timeline")
    history_parser.add_argument("-n", "--count", type=int, default=15, help="Number of commits to show")

    # Import controls
    import_parser = subparsers.add_parser("import", help="Import collaborator branch/user .als file as a conflict-free side-file")
    import_parser.add_argument("target", help="Collaborator name or branch to import (e.g., nik, collab/nik-vox)")

    # GUI controls
    subparsers.add_parser("gui", help="Launch the local Web GUI dashboard")

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
    elif args.command == "clone":
        clone_project(args.url)
    elif args.command == "create":
        create_project(args.project_folder)
    elif args.command == "checkpoint":
        manage_checkpoint(args.message, args.tag)
    elif args.command == "history":
        manage_history(args.count)
    elif args.command == "import":
        manage_import(args.target)
    elif args.command == "gui":
        manage_gui()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
