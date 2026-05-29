import os

# Base Directories
MUSIC_DIR = os.path.expanduser("~/Desktop/Music")
HIT_CONFIG_DIR = os.path.expanduser("~/.config/hit")

# Ensure config directories exist
os.makedirs(HIT_CONFIG_DIR, exist_ok=True)

# File Paths
SONGS_JSON_PATH = os.path.join(MUSIC_DIR, "songs.json")
SONGS_MD_PATH = os.path.join(MUSIC_DIR, "songs.md")
PLUGIN_REGISTRY_PATH = os.path.join(HIT_CONFIG_DIR, "plugin_registry.json")

# Credentials
GOOGLE_CREDENTIALS_DIR = os.path.expanduser("~/.credentials")
GOOGLE_CREDENTIALS_PATH = os.path.join(GOOGLE_CREDENTIALS_DIR, "google_drive_hit.json")
os.makedirs(GOOGLE_CREDENTIALS_DIR, exist_ok=True)

# Sync Settings
POLL_INTERVAL_SECONDS = 30
DEBOUNCE_DELAY_SECONDS = 2.0  # Wait after file writes before syncing to ensure Ableton finishes writing

# Load local config overrides if present
import json
GOOGLE_DRIVE_FOLDER_NAME = "HIT_DAW_Shared_Projects"

if os.path.exists(os.path.join(HIT_CONFIG_DIR, "config.json")):
    try:
        with open(os.path.join(HIT_CONFIG_DIR, "config.json"), "r") as f:
            local_cfg = json.load(f)
            GOOGLE_DRIVE_FOLDER_NAME = local_cfg.get("drive_folder", GOOGLE_DRIVE_FOLDER_NAME)
    except Exception:
        pass

GOOGLE_DRIVE_FOLDER_ID = None  # Populated dynamically by drive_sync

# Git Settings
GIT_BRANCH_PREFIX = "collab/"
