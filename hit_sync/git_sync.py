import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GitSyncManager:
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def _run_git(self, args):
        """Helper to run git commands in the repository directory."""
        try:
            cmd = ["git"] + args
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip(), True
        except subprocess.CalledProcessError as e:
            logging.error(f"Git command failed: {' '.join(cmd)}")
            logging.error(f"Error output: {e.stderr}")
            return e.stderr, False

    def is_repo_clean(self):
        output, success = self._run_git(["status", "--porcelain"])
        if not success:
            return False
        return len(output) == 0

    def get_current_branch(self):
        output, success = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        if success:
            return output
        return "unknown"

    def pull(self):
        logging.info("Pulling latest changes from remote...")
        output, success = self._run_git(["pull", "origin", self.get_current_branch()])
        return success, output

    def push(self):
        logging.info("Pushing changes to remote...")
        output, success = self._run_git(["push", "origin", self.get_current_branch()])
        return success, output

    def commit_file(self, file_path, commit_message):
        """Stage and commit a specific file."""
        # Convert path to relative to repo path
        rel_path = os.path.relpath(file_path, self.repo_path)
        
        # Stage file
        _, success_add = self._run_git(["add", rel_path])
        if not success_add:
            return False
            
        # Commit file
        output, success_commit = self._run_git(["commit", "-m", commit_message])
        if success_commit:
            logging.info(f"Committed changes for {rel_path} successfully.")
            return True
        else:
            # If nothing to commit, return True
            if "nothing to commit" in output or "working tree clean" in output:
                return True
            return False

    # --- Locking System ---
    def acquire_lock(self, user_name):
        """Create a lock file to declare ownership of the active editing session."""
        lock_file = os.path.join(self.repo_path, "project.lock")
        if os.path.exists(lock_file):
            with open(lock_file, "r") as f:
                current_owner = f.read().strip()
            if current_owner != user_name:
                logging.warning(f"Project is locked by another user: {current_owner}")
                return False, current_owner
                
        with open(lock_file, "w") as f:
            f.write(user_name)
            
        # Push lock to git immediately so others see it
        self.commit_file(lock_file, f"[LOCK] Project locked by {user_name}")
        self.push()
        logging.info(f"Lock acquired by {user_name}")
        return True, user_name

    def release_lock(self, user_name):
        """Delete the lock file and push updates."""
        lock_file = os.path.join(self.repo_path, "project.lock")
        if not os.path.exists(lock_file):
            return True
            
        with open(lock_file, "r") as f:
            current_owner = f.read().strip()
            
        if current_owner == user_name:
            os.remove(lock_file)
            # Push lock deletion to remote
            self._run_git(["rm", "project.lock"])
            self._run_git(["commit", "-m", f"[UNLOCK] Project released by {user_name}"])
            self.push()
            logging.info(f"Lock released by {user_name}")
            return True
        else:
            logging.warning(f"Cannot release lock owned by {current_owner} (current user: {user_name})")
            return False
