# HIT CLI Management Guide for AI Copilots

This document details the interface, commands, and operations of the **`hit` CLI tool** for the HIT Ableton Live Sync suite. It is designed to guide AI agents in automating and monitoring the sync daemon.

---

## 1. Environment & Setup

* **Executable Location**: `/Users/claywashington/.local/bin/hit` (or symlinked python execution)
* **Underlying Python Script**: `/Users/claywashington/hit/hit_cli.py`
* **Log Location**: `~/.config/hit/daemon.log`
* **PID File Location**: `~/.config/hit/daemon.pid`
* **Config File Location**: `~/.config/hit/config.json`

Always run commands with the Mac environment prefix if calling `gcloud` or custom python binaries:
```bash
export CLOUDSDK_PYTHON="/opt/homebrew/bin/python3"
```

---

## 2. Command Reference

AI agents should use these commands to manage the daemon state and track cooperation branches.

### Daemon Control
* **Start Daemon**:
  ```bash
  hit start
  ```
  *Spawns the background sync process, writes the PID file, and redirects stdout/stderr to `daemon.log`.*

* **Stop Daemon**:
  ```bash
  hit stop
  ```
  *Reads the active PID file and terminates the background daemon safely.*

* **Restart Daemon**:
  ```bash
  hit restart
  ```

* **Check Status**:
  ```bash
  hit status
  ```
  *Outputs whether the daemon is running, the active PID, active song, git branch, and sync status.*

* **Force Immediate Sync**:
  ```bash
  hit sync
  ```
  *Triggers an immediate Git pull/push check and Google Drive file sync.*

### Branch & Lock Management
* **List Active Collaboration Branches**:
  ```bash
  hit branch
  ```
  
* **Switch or Create a Branch**:
  ```bash
  hit branch [branch-name]
  ```
  *Switches branches or creates a new branch named `collab/[username]-[branch-name]` if it does not exist.*

* **Lock Project (Branch Lock)**:
  ```bash
  hit lock
  ```
  *Acquires a collaborative lock on the current branch to notify other users you are editing.*

* **Unlock Project**:
  ```bash
  hit unlock
  ```

### Configuration
* **View Config**:
  ```bash
  hit config
  ```

* **Update Settings**:
  ```bash
  hit config --username [username] --remote [git-remote-url] --drive-folder [shared-folder-name]
  ```

---

## 3. Automation Sequences (Playbooks)

### Pulling Collaborator Changes Safely:
1. Stop the daemon: `hit stop`
2. Fetch branches: `git fetch origin`
3. Switch branch: `hit branch [target-branch]`
4. Force sync to pull files and download Google Drive assets: `hit sync`
5. Start the daemon back up: `hit start`

### Starting a New Session:
1. Switch to a new branch: `hit branch new-ideas`
2. Acquire the session lock: `hit lock`
3. Open Ableton Live and make edits.
4. On save, the daemon will automatically commit/push the XML and upload any new recordings to Google Drive.
5. When finished, release the lock: `hit unlock`
