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
  checkpoint       Label the last save and optionally tag it as a new version
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
Make sure you have Python 3 and pip installed, then run:
```bash
pip install -r requirements.txt
```

### 2. Install the `hit` Command Line Tool
To be able to run the `hit` command from any directory in your terminal, link it to your local binary path:
```bash
# Create local bin directory if it doesn't exist
mkdir -p ~/.local/bin

# Symlink the CLI script
ln -sf "$PWD/hit_cli.py" ~/.local/bin/hit
chmod +x ~/.local/bin/hit
```
*(Ensure `~/.local/bin` is in your shell's `PATH` variable. For example, add `export PATH="$HOME/.local/bin:$PATH"` to your `~/.zshrc` or `~/.bash_profile`).*

### 3. Configure Google Drive API credentials
Place your downloaded client credentials JSON from Google Cloud Console in the target location:
```bash
mv ~/Downloads/client_secret_*.json ~/.credentials/google_drive_hit.json
```

### 4. Run the Configuration Wizard
Initialize your settings by running the interactive setup wizard:
```bash
hit config
```
*Simply press Enter to accept the defaults, or type in your name, shared Git remote, and Google Drive shared folder name.*

### 5. Authenticate Google Drive
Run the credentials authentication flow. This opens a browser tab allowing you to log into your Google Drive:
```bash
hit sync
```

### 6. Launch the Sync Service
Start the background daemon:
```bash
hit start
```
*Your music is now automatically backed up and synced in the background. You can close your terminal and open Ableton Live!*

---

---

## 5. Song Collaboration Playbook (Step-by-Step)

Here is the exact sequence of steps to create and share a collaborative song.

### Workflow A: For You (The Creator)

1. **Create and Save**: Open Ableton Live, record your ideas, and save the project inside your music folder, e.g., `~/Desktop/Music/My_New_Song Project/My_New_Song.als`.
2. **Collect Audio Assets**: Run **"Collect All and Save"** from Ableton's menu. This copies all external audio recordings and samples into the project's local `Samples/` folder.
3. **Publish to GitHub**: Turn the project directory into a collaborative HIT repository:
   ```bash
   hit create "My_New_Song Project"
   ```
   *This initializes Git, creates a private repository on your GitHub account (`claytonwashington`) using the `gh` CLI, and pushes the XML data.*
4. **Set Active**: Mark the song as active in your catalog:
   ```bash
   songs active "My_New_Song"
   ```
5. **Start Daemon**: Launch the sync runner:
   ```bash
   hit start
   ```
   *The daemon will automatically scan the project and upload the audio assets to your 35TB Google Drive.*

---

### Workflow B: For Your Friend (The Collaborator)

Once you send them the clone repository link:

1. **Clone the Song**: In their terminal, they run:
   ```bash
   hit clone git@github.com:claytonwashington/My_New_Song.git
   ```
   *This clones the project directory into their music folder, sets up local Git filters, and registers it in their catalog.*
2. **Set Active**: They mark the song as active:
   ```bash
   songs active "My_New_Song"
   ```
3. **Start Daemon**: Start syncing:
   ```bash
   hit start
   ```
   *Their background process will pull the XML and automatically download all missing audio stems from your shared 35TB Google Drive.*
4. **Open and Play**: They double-click the local `.als` file. Ableton opens it instantly, finds all audio stems ready to play, and they are ready to edit!

---

## 5. Checkpoints and Version Tagging

By default, the HIT daemon automatically commits every Ableton save with a generic `[HIT Sync] ...` message. If you want to label a specific state (e.g. you finished a mix or want to mark a milestone), you can create a **Checkpoint**:

```bash
hit checkpoint
```

*   **Interactive Prompts**: You will be prompted to enter a description (which will replace/amend the daemon's last auto-save commit message) and an optional version tag (e.g., `v1.0` or `draft-mix`).
*   **Command Line Flags**: You can also run it non-interactively using flags:
    ```bash
    hit checkpoint -m "Finalized vocal arrangement" -t "v1.1"
    ```
*   **Force-Push and Publish**: The CLI automatically force-pushes the updated commit history and tag to GitHub in a single step so it is visible to your collaborator.

---

## 6. How to Collaborate (Sharing Your 35TB Google Drive)

HIT supports collaborating across different Google Accounts using standard **Google Drive Folder Sharing**:

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
