import os
import io
import logging
import hashlib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Scopes required for managing Drive files
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveSyncManager:
    def __init__(self, credentials_path, token_path=None):
        self.credentials_path = credentials_path
        # Store token file in the same directory as credentials by default
        if token_path is None:
            self.token_path = os.path.join(os.path.dirname(credentials_path), "token.json")
        else:
            self.token_path = token_path
            
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate user using OAuth flow and build Google Drive API service."""
        # Load existing tokens if present
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
        # If credentials are not valid or missing, run OAuth consent flow
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    self.creds = None
                    
            if not self.creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Google credentials file not found at {self.credentials_path}. "
                        "Please download the OAuth Client ID JSON from GCP Console and place it there."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
                
            # Save the credentials for next runs
            with open(self.token_path, "w") as token_file:
                token_file.write(self.creds.to_json())
                
        self.service = build("drive", "v3", credentials=self.creds)
        logging.info("Google Drive authenticated successfully.")

    def get_or_create_folder(self, folder_name, parent_id=None):
        """Find a folder on Google Drive or create it if not found."""
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get("files", [])
        
        if items:
            return items[0]["id"]
            
        # Create folder if it doesn't exist
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]
            
        folder = self.service.files().create(body=file_metadata, fields="id").execute()
        logging.info(f"Created Google Drive folder: '{folder_name}' (ID: {folder['id']})")
        return folder["id"]

    def get_file_md5(self, file_path):
        """Compute the MD5 checksum of a local file."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def upload_file(self, file_path, drive_parent_folder_id):
        """Upload a file to Google Drive. Skips upload if MD5 hash matches."""
        filename = os.path.basename(file_path)
        local_md5 = self.get_file_md5(file_path)
        
        # Check if file already exists in this folder on Drive
        query = f"name = '{filename}' and '{drive_parent_folder_id}' in parents and trashed = false"
        results = self.service.files().list(q=query, fields="files(id, md5Checksum)").execute()
        files = results.get("files", [])
        
        if files:
            drive_file = files[0]
            # Compare MD5 checksums
            if drive_file.get("md5Checksum") == local_md5:
                logging.info(f"Skipping upload. File {filename} already exists and is in sync.")
                return drive_file["id"]
            else:
                # Update existing file
                logging.info(f"Updating file {filename} on Google Drive...")
                media = MediaFileUpload(file_path, resumable=True)
                updated_file = self.service.files().update(
                    fileId=drive_file["id"],
                    media_body=media
                ).execute()
                return updated_file["id"]
        
        # Upload new file
        logging.info(f"Uploading new file {filename} to Google Drive...")
        file_metadata = {
            "name": filename,
            "parents": [drive_parent_folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        logging.info(f"File {filename} uploaded successfully (ID: {file['id']})")
        return file["id"]

    def download_file(self, drive_file_id, output_path):
        """Download a file from Google Drive."""
        # Check if local file exists and compare size/hash if possible
        request = self.service.files().get_media(fileId=drive_file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            logging.info(f"Download progress: {int(status.progress() * 100)}%")
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(fh.getvalue())
        logging.info(f"Downloaded file successfully to: {output_path}")
        return True

    def sync_file_from_drive(self, filename, drive_parent_folder_id, local_output_path):
        """Check if file exists on Google Drive, download it if missing or outdated."""
        query = f"name = '{filename}' and '{drive_parent_folder_id}' in parents and trashed = false"
        results = self.service.files().list(q=query, fields="files(id, md5Checksum)").execute()
        files = results.get("files", [])
        
        if not files:
            logging.warning(f"File {filename} not found on Google Drive.")
            return False
            
        drive_file = files[0]
        drive_md5 = drive_file.get("md5Checksum")
        
        # If local file exists, check MD5
        if os.path.exists(local_output_path):
            local_md5 = self.get_file_md5(local_output_path)
            if local_md5 == drive_md5:
                logging.info(f"Local file {filename} is already up to date.")
                return True
                
        logging.info(f"Downloading updated version of {filename}...")
        return self.download_file(drive_file["id"], local_output_path)
