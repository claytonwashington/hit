# HIT — Ableton Live Git & Google Drive Sync Manager

HIT is a background synchronization daemon and command-line utility that enables seamless, near-real-time collaboration on Ableton Live sets. 

It uses **Git** to track and version the lightweight arrangement structure (decompressed `.als` XML files) and a **35TB Google Drive** container to store and sync heavy audio assets (recordings, samples, stems).

---

## 1. Collaboration Workflow (Branch-Locking Mode)

To prevent edit conflicts and ensure you never overwrite each other's work, HIT uses a **Branch-Locking** workflow:

1. **Working on Branches**: Each collaborator works on their own branch, e.g. `collab/clay-drums` or `collab/partner-bass`.
2. **Locking the Set**: Before editing, you run `hit lock`. This places a lock file (`project.lock`) in the branch, notifying other collaborators that you are actively working on it.
3. **Synchronizing**: As you work, the daemon runs in the background. Every time you save in Ableton:
   - The daemon decompresses the `.als` file into text XML.
   - Pushes the XML changes to Git.
   - Uploads any new `.wav` recordings or samples to Google Drive.
4. **Desktop Notifications**: When your partner pushes a change, a native macOS notification banner pops up:
   > **🎛️ HIT Sync Manager**
   > *"Partner updated the project: 'Added Vocals'. Click to reload."*

---

## 2. Command Line Interface (CLI)

The `hit` command utility makes managing your sessions simple.

```
Usage: hit <command> [options]

Commands:
  start            Launch the background sync daemon
  stop             Stop the background daemon safely
  restart          Restart the background daemon
  status           Show current daemon, active project, and git branch status
  sync             Force an immediate Git pull/push and Google Drive asset sync
  lock             Acquire the editing lock on the current branch
  unlock           Release the editing lock
  branch [name]    List collaboration branches, or checkout/create a new branch
  config           View or update user and git configurations
```

---

## 3. Directory Structure

```
hit/
├── README.md                    # This user guide
├── AGENTS.md                    # Guidelines for AI copilots in this repository
├── AGENTS_CLI.md                # Guide for AI tools to interact with the hit CLI
├── AGENTS_GCP.md                # Server provisioning guide
├── VST_SYNC_SPEC.md             # Third-party VST/AU plugin sync specification
├── hit_daemon.py                # Core background sync service
├── hit_cli.py                   # Command-line interface implementation
└── hit_sync/
    ├── config.py                # Environmental configs
    ├── watcher.py               # Filesystem watcher (watchdog)
    ├── git_sync.py              # Git pulling/pushing & lock manager
    ├── drive_sync.py            # Google Drive API sync engine (OAuth)
    └── als_parser.py            # Gzip handler & Ableton XML relativizer
```

---

## 4. Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Google Drive API credentials
Place your downloaded client credentials JSON from Google Cloud Console in the target location:
```bash
mv ~/Downloads/client_secret_*.json ~/.credentials/google_drive_hit.json
```

### 3. Initialize your configuration
Set your collab name and project remote repository:
```bash
hit config --username clay --remote git@github.com:claytonwashington/hit.git
```

### 4. Authenticate Google Drive
Run the credentials authentication flow. This opens a browser tab allowing you to log into your Google Drive:
```bash
hit sync
```

### 5. Launch the Sync Service
```bash
hit start
```
*Your music is now automatically backed up and synced in the background. You can close your terminal and open Ableton Live!*

---

## 5. How to Collaborate (Sharing Your 35TB Google Drive)

HIT supports collaborating across different Google Accounts using standard **Google Drive Folder Sharing**. Here is how to configure it:

### Step 1: Owner Shares the Folder
1. As the owner of the 35TB Google Drive account (e.g. Clay), log into Google Drive via your browser.
2. The first time the daemon runs, it will create a folder named **`HIT_DAW_Shared_Projects`** (or whatever name you set during config).
3. Right-click that folder, click **Share**, and enter your collaborator's email address.
4. Set their permission level to **Editor** and click Send.

> [!TIP]
> **Quota Benefits**: Under Google Drive's sharing structure, files uploaded to a shared folder count against the **Folder Owner's** storage quota (Clay's 35TB). This means your collaborator can upload unlimited heavy audio stems/samples without needing their own paid Google subscription!

### Step 2: Collaborator Configures their HIT Client
Once the collaborator accepts the shared folder invitation, they must configure their daemon to point to the exact same folder name:

1. Clone the repository and install dependencies.
2. Place their own desktop API credentials at `~/.credentials/google_drive_hit.json`.
3. Run the interactive setup wizard:
   ```bash
   hit config
   ```
4. Set their own username, paste your shared Git remote URL, and enter the **exact name of the shared folder** (e.g., `HIT_DAW_Shared_Projects`) when prompted.
5. Authenticate via their browser:
   ```bash
   hit sync
   ```
6. Start their daemon:
   ```bash
   hit start
   ```
   *The collaborator's daemon will now automatically download all your audio stems and sync their saves directly to your shared folder!*
