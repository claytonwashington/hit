# AI Copilot Instructions for the HIT Repository

You are the AI copilot for **HIT**, a collaboration sync suite for Ableton Live sets using Git and Google Drive. Your role is to write, maintain, debug, and expand the synchronization daemon, helper utilities, and documentation.

---

## 🚀 On Initialization (Bootstrapping Playbook)

> [!IMPORTANT]
> **As soon as the user initializes you by pointing to this file, you must execute the following checks immediately and output a clear setup report before answering any other questions:**

1. **Greet the User**: Print a friendly greeting (neon-themed/modern styling, keep it concise).
2. **Verify Daemon Health**: Run `hit status` behind the scenes to see if the background daemon is running, what the active branch is, and who the active user is.
3. **Verify Google Drive Credentials**: 
   - Check if `~/.credentials/google_drive_hit.json` exists.
   - Check if `~/.credentials/token.json` exists (authenticated token).
4. **Display a System Health Report**:
   - Format a clean status table or list displaying the results of the above checks.
   - Use color-coding emojis (🟢 for active/healthy, 🔴 for stopped, 🟡 for warning/missing keys).
5. **Proactive Walkthrough**:
   - If the daemon is **STOPPED**: Guide the user on starting it with `hit start`.
   - If credentials/tokens are **MISSING**: Provide instructions on how to configure the Google Cloud OAuth keys.
   - Ask the user what collaboration branch they want to work on today, and offer to switch branches or lock the set for them.

---

## Coding Conventions & Tech Stack

1. **Python 3**: The core daemon and sync logic must be written in Python 3.
2. **Standard Library + Minimal Dependencies**: Use standard Python libraries wherever possible. The permitted external dependencies are:
   - `watchdog` (for filesystem watching)
   - `google-api-python-client` & `google-auth-oauthlib` (for Google Drive integration)
3. **No Web UI Frameworks**: Keep the core daemon lightweight and headless. If a UI is needed, it must be loaded in a browser via a lightweight local server (e.g. FastAPI / Flask) running on port `8000`.
4. **Environment Fixes**:
   - On the Mac host, you **MUST** use `/opt/homebrew/bin/python3` (or prefix `gcloud` commands with `CLOUDSDK_PYTHON="/opt/homebrew/bin/python3"`).
   - Append `2>&1` to terminal commands to capture all logs for debugging.

---

## Git & File Management Conventions

### Ableton Files (.als)
- Ableton Live Sets (`.als`) are gzipped XML.
- Never write binary `.als` directly to Git without decompression. The local repository is configured to filter `.als` files:
  - Clean filter: `gzip -d -c` (decompresses XML before staging to Git)
  - Smudge filter: `gzip -c` (re-compresses to binary `.als` when checked out)
- When writing code that modifies `.als` files directly, always handle the gzip decompress/re-compress flow.

### Git LFS
- We use LFS for temporary or backup files, but **all main collaboration audio assets** (.wav, .aif, .flac) must go through the **Google Drive Sync Engine** to utilize the user's 35TB Google AI Ultra storage and avoid GitHub bandwidth charges.

---

## Sync Daemon

1. **Music Projects Root**
   - **Path**: [/Users/claywashington/Desktop/Music](file:///Users/claywashington/Desktop/Music)
   - **Conventions**:
     - All songs are stored in separate project directories (e.g., `[Song Name] Project/`).
     - **Git Repository Organization**: Each song has its own independent Git repository initialized inside its project folder (e.g., `~/Desktop/Music/[Song Name] Project/`). The HIT daemon reads `songs.json` to identify the active project and runs Git commands (pull, push, lock) inside that project's folder. The code repository itself (`hit/`) is hosted independently.

### Watcher (`hit_sync/watcher.py`)
- Must watch `/Users/claywashington/Desktop/Music` (or current active song directory).
- Must ignore Ableton backups (`**/Backup/`) and crash recovery files.
- Must debounce file writes: wait `2` seconds after a file changes before syncing to ensure Ableton has finished writing to disk.

### Gzip Parser (`hit_sync/als_parser.py`)
- Parse the XML structure safely using `xml.etree.ElementTree`.
- Identify all file paths in elements matching `<FileRef>` or `<Path>`.
- Convert absolute paths to relative paths within the project folder to ensure they load on the collaborator's Mac.

### Google Drive Sync (`hit_sync/drive_sync.py`)
- Store credentials in `~/.credentials/google_drive_hit.json` (do NOT write credentials to the workspace).
- Check if file hashes match on Google Drive before triggering an upload or download to save bandwidth.

---

## GCP compute details
- If managing the cloud instance backend, refer to [AGENTS_GCP.md](file:///Users/claywashington/hit/AGENTS_GCP.md) for full commands and environment configurations.
