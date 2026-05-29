import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Timer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AbletonProjectWatcher:
    def __init__(self, watch_dir, on_changed_callback, debounce_delay=2.0):
        self.watch_dir = watch_dir
        self.on_changed_callback = on_changed_callback
        self.debounce_delay = debounce_delay
        
        self.observer = Observer()
        self.handler = AbletonProjectHandler(self._debounced_trigger)
        self.timers = {}

    def start(self):
        logging.info(f"Starting watcher on: {self.watch_dir}")
        self.observer.schedule(self.handler, self.watch_dir, recursive=True)
        self.observer.start()

    def stop(self):
        logging.info("Stopping watcher...")
        self.observer.stop()
        self.observer.join()
        # Cancel any active timers
        for timer in self.timers.values():
            timer.cancel()

    def _debounced_trigger(self, file_path):
        """Debounce filesystem events to allow Ableton time to finish writing to disk."""
        if file_path in self.timers:
            self.timers[file_path].cancel()

        # Set up a new timer to call the actual sync callback
        timer = Timer(self.debounce_delay, self._execute_callback, [file_path])
        self.timers[file_path] = timer
        timer.start()

    def _execute_callback(self, file_path):
        # Remove reference from active timers
        if file_path in self.timers:
            del self.timers[file_path]
        
        logging.info(f"Debounce finished. Triggering sync for: {file_path}")
        self.on_changed_callback(file_path)


class AbletonProjectHandler(FileSystemEventHandler):
    def __init__(self, trigger_callback):
        self.trigger_callback = trigger_callback

    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Filter: Only trigger on .als files
        if not file_path.endswith(".als"):
            return

        # Filter: Only trigger on the active project's main .als file
        try:
            import json
            from hit_sync.config import MUSIC_DIR, SONGS_JSON_PATH
            if os.path.exists(SONGS_JSON_PATH):
                with open(SONGS_JSON_PATH, "r") as f:
                    song_data = json.load(f)
                active_proj = song_data.get("active_project")
                if active_proj and "songs" in song_data and active_proj in song_data["songs"]:
                    relative_als = song_data["songs"][active_proj].get("path")
                    if relative_als:
                        active_als_path = os.path.abspath(os.path.join(MUSIC_DIR, relative_als))
                        if os.path.abspath(file_path) != active_als_path:
                            return
        except Exception as e:
            logging.error(f"Error filtering active project .als in watcher: {e}")
            
        # Ignore Backup directories
        path_parts = file_path.split(os.sep)
        if "Backup" in path_parts:
            return
            
        # Ignore temporary files
        filename = os.path.basename(file_path)
        if filename.startswith(".") or filename.endswith(".tmp") or "[Crash Recovery]" in filename:
            return

        logging.info(f"Detected modification on: {file_path}")
        self.trigger_callback(file_path)
