"""Chunking module with deduplication."""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
from collections import defaultdict

from utils.exceptions import EmptyTextError, InvalidChunkSizeError
from utils.logger import get_logger
from utils.progress import ProgressBar
from utils.state_manager import StateManager

logger = get_logger(__name__)


class TextChunker:
    """Chunk text into fixed-size segments with deduplication."""
    
    def __init__(
        self,
        chunk_size: int,
        manifest_path: str,
        state_manager: Optional[StateManager] = None,
        enable_deduplication: bool = True,
        fuzzy_matching: bool = False
    ):
        """Initialize text chunker.
        
        Args:
            chunk_size: Number of words per chunk
            manifest_path: Path to save chunks manifest
            state_manager: State manager for resume capability
            enable_deduplication: Whether to deduplicate chunks
            fuzzy_matching: Whether to use fuzzy matching (not implemented)
        """
        if chunk_size <= 0:
            raise InvalidChunkSizeError(f"Invalid chunk size: {chunk_size}")
        
        self.chunk_size = chunk_size
        self.manifest_path = Path(manifest_path)
        self.state_manager = state_manager
        self.enable_deduplication = enable_deduplication
        self.fuzzy_matching = fuzzy_matching
        
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    
    def chunk(self, input_path: str, source_file: str = "unknown") -> Dict[str, Any]:
        """Chunk text from input file.
        
        Args:
            input_path: Path to cleaned text file
            source_file: Original source file name
            
        Returns:
            Dictionary with chunking results
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Read input text
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if not text.strip():
            raise EmptyTextError("Input text is empty")
        
        # Tokenize into words
        words = text.split()
        total_words = len(words)
        
        logger.info(f"Chunking {total_words} words into {self.chunk_size}-word segments")
        
        # Create chunks
        chunks = []
        chunk_id = 0
        
        with ProgressBar(
            total=total_words,
            desc="Creating chunks",
            unit="word"
        ) as pbar:
            for i in range(0, total_words, self.chunk_size):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = ' '.join(chunk_words)
                
                # Calculate chunk hash
                chunk_hash = self._hash_text(chunk_text)
                
                chunk_data = {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "hash": chunk_hash,
                    "start_word_idx": i,
                    "end_word_idx": min(i + self.chunk_size, total_words),
                    "word_count": len(chunk_words),
                    "source_file": source_file,
                }
                
                chunks.append(chunk_data)
                chunk_id += 1
                pbar.update(len(chunk_words))
            
            pbar.close(f"Created {len(chunks)} chunks")
        
        # Deduplication
        if self.enable_deduplication:
            chunks, dedup_map = self._deduplicate(chunks)
        else:
            dedup_map = {}
        
        # Save manifest
        manifest = {
            "total_chunks": len(chunks),
            "unique_chunks": len([c for c in chunks if c.get("is_canonical", True)]),
            "duplicate_chunks": len([c for c in chunks if not c.get("is_canonical", True)]),
            "chunk_size": self.chunk_size,
            "total_words": total_words,
            "deduplication_map": dedup_map,
            "chunks": chunks
        }
        
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Chunks manifest saved to {self.manifest_path}")
        
        # Update state
        if self.state_manager:
            self.state_manager.save_state(
                "chunker",
                "completed",
                {
                    "total_chunks": len(chunks),
                    "unique_chunks": manifest["unique_chunks"],
                    "duplicate_chunks": manifest["duplicate_chunks"]
                }
            )
        
        return {
            "total_chunks": len(chunks),
            "unique_chunks": manifest["unique_chunks"],
            "chunks": chunks,
            "manifest_path": str(self.manifest_path)
        }
    
    def _hash_text(self, text: str) -> str:
        """Create hash of text for deduplication.
        
        Args:
            text: Text to hash
            
        Returns:
            SHA256 hash
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _deduplicate(self, chunks: List[Dict[str, Any]]) -> tuple:
        """Deduplicate chunks based on hash.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Tuple of (deduplicated chunks, dedup map)
        """
        logger.info("Deduplicating chunks...")
        
        hash_to_canonical = {}  # hash -> canonical chunk_id
        dedup_map = {}  # duplicate chunk_id -> canonical chunk_id
        
        for chunk in chunks:
            chunk_hash = chunk["hash"]
            chunk_id = chunk["chunk_id"]
            
            if chunk_hash not in hash_to_canonical:
                # First occurrence - mark as canonical
                hash_to_canonical[chunk_hash] = chunk_id
                chunk["is_canonical"] = True
            else:
                # Duplicate - mark and map to canonical
                canonical_id = hash_to_canonical[chunk_hash]
                chunk["is_canonical"] = False
                chunk["canonical_id"] = canonical_id
                dedup_map[chunk_id] = canonical_id
        
        unique_count = len(hash_to_canonical)
        duplicate_count = len(chunks) - unique_count
        
        if duplicate_count > 0:
            logger.info(
                f"Found {duplicate_count} duplicates ({duplicate_count/len(chunks)*100:.1f}%). "
                f"Unique chunks: {unique_count}"
            )
        else:
            logger.info("No duplicates found")
        
        return chunks, dedup_map
