import os
import shutil
import zipfile
from pathlib import Path
from typing import Tuple, List, Optional
from fastapi import UploadFile, HTTPException

from app.core.config import settings
from app.core.security import is_safe_path, validate_archive_entry_name


class IngestionError(Exception):
    """Custom exception for file ingestion and archive extraction failures"""
    pass


class IngestionService:
    @staticmethod
    def create_job_workspace(job_id: str) -> Path:
        """Creates a dedicated, isolated workspace directory for an analysis job."""
        job_dir = settings.EXTRACTED_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    @staticmethod
    def cleanup_workspace(job_id: str) -> None:
        """Removes the extracted files and temp workspace for a job."""
        job_dir = settings.EXTRACTED_DIR / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)

    @staticmethod
    async def save_uploaded_zip(file: UploadFile, job_id: str) -> Path:
        """Safely saves the uploaded zip file to disk with upload size verification."""
        temp_zip_path = settings.UPLOAD_DIR / f"{job_id}.zip"
        
        total_size = 0
        chunk_size = 1024 * 1024  # 1 MB chunk
        
        with open(temp_zip_path, "wb") as f:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                    temp_zip_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Upload exceeds maximum allowable size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB"
                    )
                f.write(chunk)
                
        return temp_zip_path

    @staticmethod
    def inspect_and_extract_zip(zip_path: Path, target_dir: Path) -> Tuple[int, int]:
        """
        Validates zip archive security parameters and extracts contents safely.
        Returns: (extracted_file_count, total_uncompressed_bytes)
        """
        if not zipfile.is_zipfile(zip_path):
            raise IngestionError("The provided file is not a valid ZIP archive.")

        total_uncompressed_size = 0
        total_compressed_size = 0
        file_count = 0

        target_dir = target_dir.resolve()

        with zipfile.ZipFile(zip_path, "r") as zf:
            infolist = zf.infolist()

            if len(infolist) > settings.MAX_FILE_COUNT:
                raise IngestionError(
                    f"Archive contains {len(infolist)} entries, exceeding the maximum limit of {settings.MAX_FILE_COUNT} files."
                )

            # Pre-extraction validation pass
            for info in infolist:
                # 1. Validate file name and path traversal
                is_valid, err = validate_archive_entry_name(info.filename)
                if not is_valid:
                    raise IngestionError(f"Security validation failed: {err}")

                # 2. Check for symbolic links (Unix symlink attribute: 0o120000)
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise IngestionError(f"Security validation failed: Symbolic links are not permitted ({info.filename})")

                # Accumulate size
                total_uncompressed_size += info.file_size
                total_compressed_size += info.compress_size
                if not info.is_dir():
                    file_count += 1

                # 3. Check individual file size limit
                if info.file_size > settings.MAX_SINGLE_FILE_SIZE_BYTES:
                    raise IngestionError(
                        f"Entry '{info.filename}' exceeds single file size limit ({settings.MAX_SINGLE_FILE_SIZE_BYTES // (1024 * 1024)} MB)."
                    )

            # 4. Total uncompressed size limit check
            if total_uncompressed_size > settings.MAX_EXTRACTED_SIZE_BYTES:
                raise IngestionError(
                    f"Extracted size ({total_uncompressed_size // (1024 * 1024)} MB) exceeds maximum limit ({settings.MAX_EXTRACTED_SIZE_BYTES // (1024 * 1024)} MB)."
                )

            # 5. Zip bomb decompression ratio check
            if total_compressed_size > 0:
                ratio = total_uncompressed_size / total_compressed_size
                if ratio > settings.MAX_DECOMPRESSION_RATIO and total_uncompressed_size > 10 * 1024 * 1024:
                    raise IngestionError(
                        f"Potential Zip Bomb detected: compression ratio {ratio:.1f} exceeds limit {settings.MAX_DECOMPRESSION_RATIO}."
                    )

            # Extraction pass with safe path verification
            for info in infolist:
                destination = target_dir / info.filename
                if not is_safe_path(target_dir, destination):
                    raise IngestionError(f"ZipSlip directory traversal attempt blocked for: {info.filename}")

                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as source, open(destination, "wb") as target:
                        shutil.copyfileobj(source, target)

        return file_count, total_uncompressed_size

    @staticmethod
    async def save_individual_files(files: List[UploadFile], target_dir: Path) -> Tuple[int, int]:
        """Saves individual uploaded source files to the job workspace."""
        total_size = 0
        file_count = 0
        target_dir = target_dir.resolve()

        for file in files:
            filename = file.filename or "uploaded_source.txt"
            is_valid, err = validate_archive_entry_name(filename)
            if not is_valid:
                raise IngestionError(f"Invalid file path: {err}")

            destination = target_dir / filename
            if not is_safe_path(target_dir, destination):
                raise IngestionError(f"Directory traversal path blocked: {filename}")

            destination.parent.mkdir(parents=True, exist_ok=True)
            content = await file.read()
            if len(content) > settings.MAX_SINGLE_FILE_SIZE_BYTES:
                raise IngestionError(f"File {filename} exceeds max size limit.")

            total_size += len(content)
            if total_size > settings.MAX_EXTRACTED_SIZE_BYTES:
                raise IngestionError("Total size of uploaded files exceeds limit.")

            with open(destination, "wb") as f:
                f.write(content)

            file_count += 1

        return file_count, total_size
