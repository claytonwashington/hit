# HIT Collaboration Workflows & Playbooks

This document provides step-by-step, real-world examples for using the **`hit` CLI** to collaborate on Ableton Live sets. 

---

## 🚀 Workflow 1: Starting a New Collaborative Project (Project Creator)

If you are starting a new song and want to share it with your collaborators:

1. **Save your Ableton Set**: Save your Ableton Live project folder inside `~/Desktop/Music/` (e.g., `~/Desktop/Music/Midnight Groove Project/`).
2. **Initialize the HIT Repository**:
   Run the `create` command to initialize git tracking and configure Ableton's decompression filters:
   ```bash
   hit create "Midnight Groove Project"
   ```
   *This initializes a Git repository inside the song folder, registers Ableton `.als` clean/smudge filters, and prompts you to publish the repo to GitHub using the GitHub CLI (`gh`).*

3. **Set the Song as Active**:
   Configure the HIT environment to watch this project:
   ```bash
   python3 /Users/claywashington/Desktop/Music/song_manager.py active "Midnight Groove Project"
   ```

4. **Start the Sync Daemon**:
   Launch the background watcher and sync engine:
   ```bash
   hit start
   ```

5. **Share with Collaborators**:
   Copy the Git remote URL from GitHub (e.g., `git@github.com:username/midnight-groove-project.git`) and send it to your collaborators.

---

## 📥 Workflow 2: Joining an Existing Project (Collaborator)

If a collaborator has sent you a Git remote URL for a song:

1. **Clone the Project**:
   ```bash
   hit clone git@github.com:username/midnight-groove-project.git
   ```
   *This clones the repository directly into your `~/Desktop/Music/` directory and configures all Ableton XML filters.*

2. **Set the Song as Active**:
   ```bash
   python3 /Users/claywashington/Desktop/Music/song_manager.py active "midnight-groove-project"
   ```

3. **Start the Sync Daemon**:
   ```bash
   hit start
   ```
   *The daemon will automatically download any heavy audio samples (.wav, .aif) associated with the project from Google Drive.*

---

## 🌿 Workflow 3: Working on a New Idea (Branching & Locking)

To work on new ideas without affecting the `main` branch or causing conflicts:

1. **Switch or Create a Branch**:
   To create a branch for your work (e.g., recording vocals), run:
   ```bash
   hit branch vox-ideas
   ```
   *HIT automatically prefixes your branch with `collab/[username]-`. For Clayton, this creates `collab/claytonwashington-vox-ideas`.*
   
   > [!NOTE]
   > **Double-Prefix Prevention**: If you explicitly include your username (e.g., `hit branch claytonwashington-vox-ideas`), HIT recognizes the pattern and creates `collab/claytonwashington-vox-ideas` directly, avoiding duplicate prefixes like `collab/claytonwashington-claytonwashington-vox-ideas`.

2. **Acquire the Editing Lock**:
   Before making edits in Ableton, lock the project to let others know you're editing:
   ```bash
   hit lock
   ```
   *This acts as a soft lock on the branch, notifying other collaborators if they try to edit or run `hit lock` on this branch.*

3. **Open Ableton & Make Edits**:
   Open `Midnight Groove.als` in Ableton Live. Every time you save (e.g., `Cmd+S`), the background daemon decompresses the XML, commits it to your local branch, uploads any new recorded audio assets to Google Drive, and pushes the Git commit to GitHub.

4. **Release the Lock**:
   When you're finished with your session, release the lock:
   ```bash
   hit unlock
   ```

---

## ✨ Workflow 4: Saving Key Milestones (Checkpointing)

While the daemon auto-commits your saves silently, you can label major milestones (e.g., "Intro complete" or "Vocal tracks tuned") to make the history readable.

1. **Save in Ableton**: Press `Cmd+S` in Ableton Live.
2. **Create a Checkpoint**:
   ```bash
   hit checkpoint "Completed vocal tuning"
   ```
   *This amends the daemon's last auto-save commit with your message, prefixing it with `[HIT Checkpoint]`, and force-pushes it to GitHub.*

3. **Optional Tagging**:
   To tag this checkpoint for easy future reference (e.g., `v1.0-vocals`):
   ```bash
   hit checkpoint "Completed vocal tuning" --tag v1.0-vocals
   ```
   Now, any collaborator can jump back to this exact point in time using `git checkout v1.0-vocals`.

---

## 🎼 Workflow 5: Reviewing the Session Timeline (History)

To see who has been working on the project and check for checkpoints:

```bash
hit history
```

### Example Output:
```text
🎼 HIT Song History: Midnight Groove Project
────────────────────────────────────────────────────────────
 ▶  [a7b8c9d]  (2 mins ago)  (HEAD -> 👉 collab/claytonwashington-vox-ideas, origin/collab/claytonwashington-vox-ideas)
    └─ claytonwashington (You): ✨ [Checkpoint] Completed vocal tuning

 ●  [d4e5f6a]  (10 mins ago)  
    └─ claytonwashington (You): 💾 Save project from Ableton

 ★  [e2f3a4b]  (2 hours ago)  (tag: 🏷️  v1.0-demo)
    └─ collab_partner: ✨ [Checkpoint] Finalized rough arrangement

 ●  [b1c2d3e]  (1 day ago)  (origin/main, main)
    └─ claytonwashington (You): 🎬 Initialized project
```

---

## 🎯 Workflow 6: Conflict-Free Importing

Instead of performing a traditional Git merge which can easily corrupt or cause conflicts in Ableton's complex XML files, HIT allows you to import another collaborator's set as a side-file, enabling you to selectively drag and drop their tracks.

1. **Import the Collaborator's Set**:
   If your partner `nik` has pushed changes to their branch `collab/nik-vox`, run:
   ```bash
   hit import nik-vox
   ```
   *This fetches from origin, extracts the main `.als` file from `collab/nik-vox`, and saves it in your project folder as `Midnight Groove_collab_nik-vox.als`.*

2. **Open your Main Set**: Open your current working file `Midnight Groove.als` in Ableton Live.
3. **Add the Project Folder to Ableton's Browser**:
   - In Ableton's sidebar, click **Add Folder...**
   - Choose your project directory `~/Desktop/Music/Midnight Groove Project`.
4. **Drag & Drop Tracks**:
   - In Ableton's browser, expand `Midnight Groove_collab_nik-vox.als`.
   - You will see their tracks, groups, and master chain.
   - Drag their vocal track directly into your active set.
   - Your project is updated conflict-free!

---

## 🛠️ Diagnostics & Troubleshooting

### Check Daemon Health
To verify if the watcher is running and checking for changes:
```bash
hit status
```

### View Live Daemon Logs
If files are not syncing, inspect the log file:
```bash
tail -n 50 ~/.config/hit/daemon.log
```

### Trigger a Manual Sync
Force the daemon to check for updates and sync immediately:
```bash
hit sync
```
