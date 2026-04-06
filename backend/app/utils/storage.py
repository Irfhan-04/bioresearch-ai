"""
Storage utilities using Supabase Storage
"""

import os
from datetime import datetime, timedelta
from typing import BinaryIO, Optional

from supabase import Client, create_client

from app.core.config import settings


class StorageService:
    """
    Supabase Storage service for file uploads/downloads

    Free tier: 1GB storage
    Perfect for exports, file uploads, etc.
    """

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,  # Use service key for admin access
        )
        self.bucket_name = settings.SUPABASE_STORAGE_BUCKET

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """
        Create bucket if it doesn't exist
        """
        try:
            # Try to get bucket
            buckets = self.client.storage.list_buckets()
            bucket_exists = any(b.name == self.bucket_name for b in buckets)

            if not bucket_exists:
                # Create bucket with public access
                self.client.storage.create_bucket(
                    self.bucket_name,
                    options={"public": True},  # Public for easy downloads
                )
                print(f"✅ Created Supabase storage bucket: {self.bucket_name}")
        except Exception as e:
            print(f"Storage bucket check: {e}")

    def upload_file(
        self,
        file_data: bytes,
        file_name: str,
        folder: str = "exports",
        content_type: str = "application/octet-stream",
    ) -> tuple[str, str]:
        """
        Upload file to Supabase Storage

        Args:
            file_data: File content as bytes
            file_name: Name of the file
            folder: Folder path in bucket (e.g., "exports", "uploads/user123")
            content_type: MIME type of the file

        Returns:
            Tuple of (file_path, public_url)
        """
        # Create full path: folder/filename
        file_path = f"{folder}/{file_name}"

        # Upload to Supabase Storage
        response = self.client.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=file_data,
            file_options={
                "content-type": content_type,
                "cache-control": "3600",  # Cache for 1 hour
                "upsert": "true",  # Overwrite if exists
            },
        )

        # Get public URL
        public_url = self.client.storage.from_(self.bucket_name).get_public_url(
            file_path
        )

        return file_path, public_url

    def download_file(self, file_path: str) -> bytes:
        """
        Download file from Supabase Storage

        Args:
            file_path: Path to file in bucket

        Returns:
            File content as bytes
        """
        response = self.client.storage.from_(self.bucket_name).download(file_path)
        return response

    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from Supabase Storage

        Args:
            file_path: Path to file in bucket

        Returns:
            True if successful
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def list_files(self, folder: str = "") -> list:
        """
        List files in a folder

        Args:
            folder: Folder path in bucket

        Returns:
            List of file objects
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(folder)
            return response
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    def get_public_url(self, file_path: str) -> str:
        """
        Get public URL for a file

        Args:
            file_path: Path to file in bucket

        Returns:
            Public URL string
        """
        return self.client.storage.from_(self.bucket_name).get_public_url(file_path)

    def create_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Create signed URL for temporary access

        Args:
            file_path: Path to file in bucket
            expires_in: Expiration in seconds (default: 1 hour)

        Returns:
            Signed URL string
        """
        response = self.client.storage.from_(self.bucket_name).create_signed_url(
            file_path, expires_in
        )
        return response.get("signedURL", "")

    def get_file_size(self, file_path: str) -> Optional[int]:
        """
        Get file size in bytes

        Args:
            file_path: Path to file in bucket

        Returns:
            File size in bytes or None if not found
        """
        try:
            folder = "/".join(file_path.split("/")[:-1])
            file_name = file_path.split("/")[-1]

            files = self.list_files(folder)
            for file in files:
                if file.get("name") == file_name:
                    return file.get("metadata", {}).get("size")

            return None
        except Exception as e:
            print(f"Error getting file size: {e}")
            return None


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """
    Get singleton StorageService instance

    Usage:
        storage = get_storage_service()
        file_path, url = storage.upload_file(data, "export.csv")
    """
    global _storage_service

    if _storage_service is None:
        _storage_service = StorageService()

    return _storage_service


# Convenience functions
def upload_export_file(
    file_data: bytes, user_id: str, file_name: str, content_type: str = "text/csv"
) -> tuple[str, str]:
    """
    Upload export file for a user

    Args:
        file_data: File content
        user_id: User ID for organizing files
        file_name: Original filename
        content_type: MIME type

    Returns:
        Tuple of (file_path, public_url)
    """
    storage = get_storage_service()

    # Create folder structure: exports/user_id/date/filename
    date_folder = datetime.now().strftime("%Y-%m-%d")
    folder = f"exports/{user_id}/{date_folder}"

    return storage.upload_file(file_data, file_name, folder, content_type)


def delete_expired_exports(days: int = 7):
    """
    Delete exports older than N days

    This should be run as a scheduled job
    """
    storage = get_storage_service()

    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")

    # List all files in exports
    files = storage.list_files("exports")

    deleted_count = 0
    for file in files:
        # Check if file is older than cutoff
        # File structure: exports/user_id/date/filename
        parts = file.get("name", "").split("/")
        if len(parts) >= 3:
            file_date = parts[2]  # Date folder
            if file_date < cutoff_str:
                file_path = file.get("name")
                if storage.delete_file(file_path):
                    deleted_count += 1

    return deleted_count


__all__ = [
    "StorageService",
    "get_storage_service",
    "upload_export_file",
    "delete_expired_exports",
]
