#!/usr/bin/env python3
import os
import sys
import time
import logging
import argparse
from hit_sync.config import (
    MUSIC_DIR, GOOGLE_CREDENTIALS_PATH, POLL_INTERVAL_SECONDS, DEBOUNCE_DELAY_SECONDS, GOOGLE_DRIVE_FOLDER_NAME
)
from hit_sync.watcher import AbletonProjectWatcher
from hit_sync.als_parser import decompress_als, compress_als, parse_referenced_samples, make_paths_relative
from hit_sync.git_sync import GitSyncManager
from hit_sync.drive_sync import GoogleDriveSyncManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class HITAbletonSyncDaemon:
    def __init__(self, username):
        self.username = username
        self.music_dir = MUSIC_DIR
        
        logging.info("Initializing HIT Sync Daemon...")
        
        # 1. Initialize Git Manager
        self.git_manager = GitSyncManager(self.music_dir)
        
        # 2. Initialize Google Drive Manager
        try:
            self.drive_manager = GoogleDriveSyncManager(GOOGLE_CREDENTIALS_PATH)
            # Create master project folder on Google Drive
            self.drive_master_folder_id = self.drive_manager.get_or_create_folder(GOOGLE_DRIVE_FOLDER_NAME)
        except Exception as e:
            logging.error(f"Google Drive initialization failed: {e}")
            logging.error("Daemon will run in offline mode for file syncing.")
            self.drive_manager = None
            self.drive_master_folder_id = None
            
        # 3. Setup File System Watcher
        self.watcher = AbletonProjectWatcher(
            watch_dir=self.music_dir,
            on_changed_callback=self.handle_local_change,
            debounce_delay=DEBOUNCE_DELAY_SECONDS
        )

    def handle_local_change(self, file_path):
        """Callback when an .als file is modified locally."""
        logging.info(f"Local save detected: {file_path}")
        
        # Decompress the Ableton set
        xml_content = decompress_als(file_path)
        if not xml_content:
            return
            
        project_dir = os.path.dirname(file_path)
        
        # Parse all referenced audio samples
        sample_paths = parse_referenced_samples(xml_content)
        logging.info(f"Parsed {len(sample_paths)} referenced samples from the set.")
        
        # If Drive is connected, upload new samples
        if self.drive_manager and self.drive_master_folder_id:
            # Create a folder for this specific song on Drive
            song_folder_name = os.path.basename(project_dir)
            song_folder_id = self.drive_manager.get_or_create_folder(song_folder_name, self.drive_master_folder_id)
            
            # Sync local samples to Google Drive
            for sample in sample_paths:
                # Resolve relative paths relative to the project directory
                abs_sample_path = sample
                if not os.path.isabs(sample):
                    abs_sample_path = os.path.abspath(os.path.join(project_dir, sample))
                    
                # Only sync files that exist locally and are inside the project folder
                # (External library samples don't need to be copied unless collected)
                if os.path.exists(abs_sample_path) and abs_sample_path.startswith(os.path.abspath(project_dir)):
                    try:
                        self.drive_manager.upload_file(abs_sample_path, song_folder_id)
                    except Exception as e:
                        logging.error(f"Failed to upload sample {sample} to Google Drive: {e}")

        # Convert absolute paths inside the project to relative paths
        normalized_xml, modified = make_paths_relative(xml_content, project_dir)
        
        # Re-compress and save
        if modified:
            compress_als(normalized_xml, file_path)
            logging.info("Successfully re-wrote .als with normalized relative paths.")

        # Commit and push project structure to Git
        commit_message = f"[HIT Sync] {self.username} updated project: {os.path.basename(file_path)}"
        if self.git_manager.commit_file(file_path, commit_message):
            self.git_manager.push()

    def sync_incoming_updates(self):
        """Pull incoming changes from Git and download missing audio files from Drive."""
        logging.info("Checking for incoming updates...")
        
        # Pull Git repository updates
        success, output = self.git_manager.pull()
        if not success:
            logging.error("Failed to pull from Git remote.")
            return

        if "Already up to date" in output or "Already up-to-date" in output:
            logging.info("Git repository is up to date.")
            return

        logging.info("Received project updates! Scanning for missing samples...")
        
        # Scan all .als files to verify we have all referenced audio files
        for root, dirs, files in os.walk(self.music_dir):
            if "Backup" in root.split(os.sep):
                continue
            for file in files:
                if file.endswith(".als"):
                    als_path = os.path.join(root, file)
                    xml_content = decompress_als(als_path)
                    if not xml_content:
                        continue
                        
                    project_dir = os.path.dirname(als_path)
                    sample_paths = parse_referenced_samples(xml_content)
                    
                    if self.drive_manager and self.drive_master_folder_id:
                        song_folder_name = os.path.basename(project_dir)
                        # Look up corresponding Google Drive folder
                        query = f"name = '{song_folder_name}' and '{self.drive_master_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                        results = self.drive_manager.service.files().list(q=query, fields="files(id)").execute()
                        folders = results.get("files", [])
                        
                        if not folders:
                            continue
                        song_folder_id = folders[0]["id"]
                        
                        # Sync missing samples
                        for sample in sample_paths:
                            # We only sync samples inside the project folder
                            if not os.path.isabs(sample) or sample.startswith(os.path.abspath(project_dir)):
                                abs_sample_path = os.path.abspath(os.path.join(project_dir, sample))
                                if not os.path.exists(abs_sample_path):
                                    filename = os.path.basename(abs_sample_path)
                                    logging.info(f"Downloading missing sample: {filename}")
                                    try:
                                        self.drive_manager.sync_file_from_drive(filename, song_folder_id, abs_sample_path)
                                    except Exception as e:
                                        logging.error(f"Failed to download sample {filename}: {e}")

    def run(self):
        """Start the background daemon loop."""
        # 1. Start file system watcher
        self.watcher.start()
        
        # 2. Main periodic pull/sync loop
        logging.info("HIT Sync Daemon started successfully.")
        try:
            while True:
                self.sync_incoming_updates()
                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logging.info("Shutting down daemon...")
        finally:
            self.watcher.stop()

def main():
    parser = argparse.ArgumentParser(description="HIT Ableton Live Sync Daemon")
    parser.add_argument("--username", required=True, help="Collaborator username for commits")
    args = parser.parse_args()

    daemon = HITAbletonSyncDaemon(args.username)
    daemon.run()

if __name__ == "__main__":
    main()
