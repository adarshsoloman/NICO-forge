"""Text extraction module for PDFs, DOCX, and TXT files."""

import os
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
from docx import Document

from utils.exceptions import (
    UnsupportedFileTypeError,
    PDFReadError,
    EncodingError
)
from utils.logger import get_logger
from utils.progress import ProgressBar
from utils.state_manager import StateManager

logger = get_logger(__name__)


class TextExtractor:
    """Extract text from various document formats."""
    
    SUPPORTED_FORMATS = {'.pdf', '.docx', '.txt'}
    
    def __init__(
        self,
        output_path: str,
        failed_output: str,
        max_file_size_mb: int = 100,
        state_manager: StateManager = None
    ):
        """Initialize text extractor.
        
        Args:
            output_path: Path to save extracted text
            failed_output: Path to save failed files info
            max_file_size_mb: Max file size for in-memory processing
            state_manager: State manager for resume capability
        """
        self.output_path = Path(output_path)
        self.failed_output = Path(failed_output)
        self.max_file_size_mb = max_file_size_mb
        self.state_manager = state_manager
        self.failed_files = []
        
        # Create output directory
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.failed_output.parent.mkdir(parents=True, exist_ok=True)
    
    def extract_from_sources(self, source_paths: List[str]) -> Dict[str, Any]:
        """Extract text from multiple source files.
        
        Args:
            source_paths: List of file or directory paths
            
        Returns:
            Dictionary with extraction statistics
        """
        # Collect all files
        all_files = self._collect_files(source_paths)
        
        if not all_files:
            logger.warning("No supported files found")
            return {"total_files": 0, "extracted": 0, "failed": 0}
        
        logger.info(f"Found {len(all_files)} files to process")
        
        # Extract text from each file
        extracted_count = 0
        
        with ProgressBar(
            total=len(all_files),
            desc="Extracting text",
            unit="file"
        ) as pbar:
            with open(self.output_path, 'w', encoding='utf-8') as out_file:
                for file_path in all_files:
                    try:
                        text = self._extract_file(file_path)
                        if text.strip():
                            out_file.write(text + "\n\n")
                            extracted_count += 1
                        pbar.update()
                    except Exception as e:
                        logger.warning(f"Failed to extract {file_path}: {e}")
                        self.failed_files.append({
                            "file": str(file_path),
                            "error": str(e)
                        })
                        pbar.update()
            
            pbar.close(f"Extraction complete: {extracted_count}/{len(all_files)} files")
        
        # Save failed files info
        if self.failed_files:
            import json
            with open(self.failed_output, 'w', encoding='utf-8') as f:
                json.dump(self.failed_files, f, indent=2, ensure_ascii=False)
            logger.info(f"Failed files saved to {self.failed_output}")
        
        # Update state
        if self.state_manager:
            self.state_manager.save_state(
                "extraction",
                "completed",
                {
                    "total_files": len(all_files),
                    "extracted": extracted_count,
                    "failed": len(self.failed_files)
                }
            )
        
        return {
            "total_files": len(all_files),
            "extracted": extracted_count,
            "failed": len(self.failed_files),
            "output_path": str(self.output_path)
        }
    
    def _collect_files(self, source_paths: List[str]) -> List[Path]:
        """Collect all supported files from source paths.
        
        Args:
            source_paths: List of file or directory paths
            
        Returns:
            List of file paths
        """
        files = []
        
        for source in source_paths:
            source_path = Path(source)
            
            if not source_path.exists():
                logger.warning(f"Path not found: {source}")
                continue
            
            if source_path.is_file():
                if source_path.suffix.lower() in self.SUPPORTED_FORMATS:
                    files.append(source_path)
            elif source_path.is_dir():
                for ext in self.SUPPORTED_FORMATS:
                    files.extend(source_path.rglob(f"*{ext}"))
        
        return files
    
    def _extract_file(self, file_path: Path) -> str:
        """Extract text from a single file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted text
            
        Raises:
            UnsupportedFileTypeError: If file format not supported
        """
        suffix = file_path.suffix.lower()
        
        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        use_streaming = file_size_mb > self.max_file_size_mb
        
        if suffix == '.pdf':
            return self._extract_pdf(file_path, streaming=use_streaming)
        elif suffix == '.docx':
            return self._extract_docx(file_path)
        elif suffix == '.txt':
            return self._extract_txt(file_path)
        else:
            raise UnsupportedFileTypeError(f"Unsupported format: {suffix}")
    
    def _extract_pdf(self, file_path: Path, streaming: bool = False) -> str:
        """Extract text from PDF file.
        
        Args:
            file_path: Path to PDF
            streaming: Whether to use page-by-page streaming
            
        Returns:
            Extracted text
        """
        try:
            text_parts = []
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                for page_num in range(len(reader.pages)):
                    try:
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        logger.debug(f"Failed to extract page {page_num} from {file_path}: {e}")
            
            return "\n".join(text_parts)
        
        except Exception as e:
            raise PDFReadError(f"Failed to read PDF {file_path}: {e}")
    
    def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file.
        
        Args:
            file_path: Path to DOCX
            
        Returns:
            Extracted text
        """
        try:
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            raise Exception(f"Failed to read DOCX {file_path}: {e}")
    
    def _extract_txt(self, file_path: Path) -> str:
        """Extract text from TXT file.
        
        Args:
            file_path: Path to TXT
            
        Returns:
            Extracted text
        """
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        raise EncodingError(f"Could not decode {file_path} with any encoding")
