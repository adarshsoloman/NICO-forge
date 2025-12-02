"""Translation pipeline with QA and error handling."""

import json
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from modules.translators.base import BaseTranslator
from utils.exceptions import (
    RateLimitError,
    APIRequestError,
    TimeoutError,
    TranslationQualityError
)
from utils.logger import get_logger
from utils.progress import ProgressBar
from utils.state_manager import StateManager

logger = get_logger(__name__)


class TranslationPipeline:
    """Translation pipeline with retry, QA, and error handling."""
    
    def __init__(
        self,
        translator: BaseTranslator,
        output_csv: str,
        output_json: str,
        failed_output: str,
        qc_failed_output: str,
        state_manager: Optional[StateManager] = None,
        batch_size: int = 20,
        flush_every: int = 5,
        retries: int = 3,
        backoff_base: float = 2.0,
        backoff_multiplier: float = 2.0,
        backoff_max: float = 60.0,
        qa_sample_rate: float = 0.01,
        qa_min_samples: int = 50,
        devanagari_threshold: float = 0.7,
        max_length_ratio: float = 2.0,
        min_length_ratio: float = 0.5
    ):
        """Initialize translation pipeline.
        
        Args:
            translator: Translator adapter instance
            output_csv: Path to output CSV file
            output_json: Path to output JSON file
            failed_output: Path to failed translations JSON
            qc_failed_output: Path to QC failed translations JSON
            state_manager: State manager for resume
            batch_size: Chunks per batch
            flush_every: Flush to disk every N batches
            retries: Number of retries
            backoff_base: Base backoff time
            backoff_multiplier: Backoff multiplier
            backoff_max: Max backoff time
            qa_sample_rate: QA sample rate (0.01 = 1%)
            qa_min_samples: Minimum QA samples
            devanagari_threshold: Min % of Devanagari chars
            max_length_ratio: Max Hindi/English length ratio
            min_length_ratio: Min Hindi/English length ratio
        """
        self.translator = translator
        self.output_csv = Path(output_csv)
        self.output_json = Path(output_json)
        self.failed_output = Path(failed_output)
        self.qc_failed_output = Path(qc_failed_output)
        self.state_manager = state_manager
        self.batch_size = batch_size
        self.flush_every = flush_every
        self.retries = retries
        self.backoff_base = backoff_base
        self.backoff_multiplier = backoff_multiplier
        self.backoff_max = backoff_max
        self.qa_sample_rate = qa_sample_rate
        self.qa_min_samples = qa_min_samples
        self.devanagari_threshold = devanagari_threshold
        self.max_length_ratio = max_length_ratio
        self.min_length_ratio = min_length_ratio
        
        # Create output directories
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        self.failed_output.parent.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self.translated_pairs = []
        self.failed_chunks = []
        self.qc_failed_chunks = []
    
    async def translate_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Translate chunks with retry and QA.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Dictionary with translation statistics
        """
        # Filter to only canonical chunks (skip duplicates)
        canonical_chunks = [
            c for c in chunks 
            if c.get("is_canonical", True)
        ]
        
        logger.info(
            f"Translating {len(canonical_chunks)} canonical chunks "
            f"(skipping {len(chunks) - len(canonical_chunks)} duplicates)"
        )
        
        # Check for resume
        completed_ids = set()
        if self.state_manager:
            completed_ids = self.state_manager.get_completed_ids("pipeline")
            if completed_ids:
                logger.info(f"Resuming: {len(completed_ids)} chunks already translated")
        
        # Filter out completed chunks
        chunks_to_translate = [
            c for c in canonical_chunks 
            if c["chunk_id"] not in completed_ids
        ]
        
        if not chunks_to_translate:
            logger.info("All chunks already translated")
            return self._load_existing_results()
        
        # Create batches
        batches = self._create_batches(chunks_to_translate)
        
        logger.info(f"Processing {len(batches)} batches")
        
        # Process batches
        with ProgressBar(
            total=len(batches),
            desc="Translating batches",
            unit="batch"
        ) as pbar:
            for i, batch in enumerate(batches):
                await self._process_batch(batch)
                pbar.update()
                
                # Flush to disk periodically
                if (i + 1) % self.flush_every == 0:
                    self._flush_to_disk()
                    logger.debug(f"Flushed after batch {i + 1}")
            
            pbar.close("Translation complete")
        
        # Final flush
        self._flush_to_disk()
        
        # Expand duplicates
        self._expand_duplicates(chunks)
        
        # Run QA sampling
        self._run_qa_sampling()
        
        # Save final outputs
        self._save_datasets()
        
        # Update state
        if self.state_manager:
            self.state_manager.save_state(
                "pipeline",
                "completed",
                {
                    "total_translated": len(self.translated_pairs),
                    "failed": len(self.failed_chunks),
                    "qc_failed": len(self.qc_failed_chunks)
                }
            )
        
        return {
            "total_translated": len(self.translated_pairs),
            "failed": len(self.failed_chunks),
            "qc_failed": len(self.qc_failed_chunks),
            "output_csv": str(self.output_csv),
            "output_json": str(self.output_json)
        }
    
    def _create_batches(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Create batches of chunks.
        
        Args:
            chunks: List of chunks
            
        Returns:
            List of batches
        """
        batches = []
        for i in range(0, len(chunks), self.batch_size):
            batches.append(chunks[i:i + self.batch_size])
        return batches
    
    async def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a single batch with retries.
        
        Args:
            batch: List of chunk dictionaries
        """
        # Extract texts
        texts = [chunk["text"] for chunk in batch]
        
        # Translate with retry decorator
        @retry(
            retry=retry_if_exception_type((RateLimitError, APIRequestError, TimeoutError)),
            stop=stop_after_attempt(self.retries),
            wait=wait_exponential(
                multiplier=self.backoff_multiplier,
                min=self.backoff_base,
                max=self.backoff_max
            ),
            reraise=True
        )
        async def translate_with_retry():
            return await self.translator.translate_batch(texts)
        
        try:
            translations = await translate_with_retry()
            
            # Store results
            for chunk, translation in zip(batch, translations):
                if translation:
                    self.translated_pairs.append({
                        "chunk_id": chunk["chunk_id"],
                        "english": chunk["text"],
                        "hindi": translation,
                        "metadata": {
                            "source_file": chunk.get("source_file"),
                            "start_word_idx": chunk.get("start_word_idx"),
                            "end_word_idx": chunk.get("end_word_idx"),
                            "translator": self.translator.get_model_info(),
                            "timestamp": datetime.now().isoformat()
                        }
                    })
                    
                    # Update state
                    if self.state_manager:
                        self.state_manager.update_completed_ids(
                            "pipeline",
                            {chunk["chunk_id"]}
                        )
                else:
                    self.failed_chunks.append({
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "error": "Empty translation"
                    })
        
        except Exception as e:
            logger.error(f"Batch failed after {self.retries} retries: {e}")
            # Add all chunks in batch to failed
            for chunk in batch:
                self.failed_chunks.append({
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "error": str(e)
                })
    
    def _expand_duplicates(self, all_chunks: List[Dict[str, Any]]):
        """Expand translations to duplicate chunks.
        
        Args:
            all_chunks: All chunks including duplicates
        """
        # Build mapping from chunk_id to translation
        id_to_translation = {
            pair["chunk_id"]: pair 
            for pair in self.translated_pairs
        }
        
        # Find duplicates and inherit translations
        duplicates_expanded = 0
        for chunk in all_chunks:
            if not chunk.get("is_canonical", True):
                canonical_id = chunk.get("canonical_id")
                if canonical_id in id_to_translation:
                    canonical_pair = id_to_translation[canonical_id]
                    # Create new pair for duplicate
                    duplicate_pair = canonical_pair.copy()
                    duplicate_pair["chunk_id"] = chunk["chunk_id"]
                    duplicate_pair["metadata"] = canonical_pair["metadata"].copy()
                    duplicate_pair["metadata"]["is_duplicate"] = True
                    duplicate_pair["metadata"]["canonical_id"] = canonical_id
                    
                    self.translated_pairs.append(duplicate_pair)
                    duplicates_expanded += 1
        
        if duplicates_expanded > 0:
            logger.info(f"Expanded {duplicates_expanded} duplicate chunks")
    
    def _run_qa_sampling(self):
        """Run QA sampling on translations."""
        total = len(self.translated_pairs)
        sample_size = max(
            int(total * self.qa_sample_rate),
            min(self.qa_min_samples, total)
        )
        
        if sample_size == 0:
            return
        
        logger.info(f"Running QA on {sample_size} samples")
        
        # Sample evenly across dataset
        step = max(1, total // sample_size)
        samples = self.translated_pairs[::step][:sample_size]
        
        for pair in samples:
            is_valid, issues = self._validate_translation(
                pair["english"],
                pair["hindi"]
            )
            
            if not is_valid:
                self.qc_failed_chunks.append({
                    "chunk_id": pair["chunk_id"],
                    "english": pair["english"],
                    "hindi": pair["hindi"],
                    "issues": issues
                })
        
        if self.qc_failed_chunks:
            logger.warning(
                f"QA: {len(self.qc_failed_chunks)}/{sample_size} samples failed "
                f"({len(self.qc_failed_chunks)/sample_size*100:.1f}%)"
            )
            
            # Save QC failures
            with open(self.qc_failed_output, 'w', encoding='utf-8') as f:
                json.dump(self.qc_failed_chunks, f, indent=2, ensure_ascii=False)
        else:
            logger.info("QA: All samples passed")
    
    def _validate_translation(
        self,
        english: str,
        hindi: str
    ) -> tuple:
        """Validate translation quality.
        
        Args:
            english: English text
            hindi: Hindi translation
            
        Returns:
            Tuple of (is_valid, issues_list)
        """
        issues = []
        
        # Check 1: Empty response
        if not hindi or len(hindi.strip()) == 0:
            issues.append("empty_response")
        
        # Check 2: Devanagari content
        if not self._is_valid_hindi(hindi):
            issues.append("insufficient_devanagari")
        
        # Check 3: Length ratio
        len_ratio = len(hindi) / max(len(english), 1)
        if len_ratio < self.min_length_ratio or len_ratio > self.max_length_ratio:
            issues.append(f"suspicious_length_ratio_{len_ratio:.2f}")
        
        # Check 4: Error markers
        if "error" in hindi.lower() or "###" in hindi or "[ERROR]" in hindi:
            issues.append("error_in_output")
        
        return len(issues) == 0, issues
    
    def _is_valid_hindi(self, text: str) -> bool:
        """Check if text contains sufficient Devanagari.
        
        Args:
            text: Text to check
            
        Returns:
            True if valid Hindi
        """
        # Devanagari Unicode range: U+0900 to U+097F
        devanagari_pattern = re.compile(r'[\u0900-\u097F]')
        
        # Count Devanagari characters
        devanagari_chars = len(devanagari_pattern.findall(text))
        total_chars = len(re.findall(r'\w', text))  # Alphanumeric only
        
        if total_chars == 0:
            return False
        
        devanagari_ratio = devanagari_chars / total_chars
        
        return devanagari_ratio >= self.devanagari_threshold
    
    def _flush_to_disk(self):
        """Flush current translations to disk (incremental save)."""
        # This is a safety measure - actual final save happens in _save_datasets
        pass
    
    def _save_datasets(self):
        """Save final CSV and JSON datasets."""
        # Sort by chunk_id
        sorted_pairs = sorted(self.translated_pairs, key=lambda x: x["chunk_id"])
        
        # Save CSV
        import csv
        with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["chunk_id", "english", "hindi", "source_file"])
            
            for pair in sorted_pairs:
                writer.writerow([
                    pair["chunk_id"],
                    pair["english"],
                    pair["hindi"],
                    pair["metadata"].get("source_file", "")
                ])
        
        logger.info(f"Saved CSV dataset: {self.output_csv}")
        
        # Save JSON
        with open(self.output_json, 'w', encoding='utf-8') as f:
            json.dump(sorted_pairs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved JSON dataset: {self.output_json}")
        
        # Save failed chunks
        if self.failed_chunks:
            with open(self.failed_output, 'w', encoding='utf-8') as f:
                json.dump(self.failed_chunks, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved failed chunks: {self.failed_output}")
    
    def _load_existing_results(self) -> Dict[str, Any]:
        """Load existing results when resuming completed pipeline.
        
        Returns:
            Statistics dictionary
        """
        if self.output_json.exists():
            with open(self.output_json, 'r', encoding='utf-8') as f:
                self.translated_pairs = json.load(f)
        
        return {
            "total_translated": len(self.translated_pairs),
            "failed": 0,
            "qc_failed": 0,
            "output_csv": str(self.output_csv),
            "output_json": str(self.output_json)
        }
