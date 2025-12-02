"""Main orchestrator for NICO-Forge pipeline."""

import sys
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

from utils.config_loader import ConfigLoader
from utils.logger import setup_logger
from utils.state_manager import StateManager
from utils.exceptions import CostThresholdExceededError

from modules.extraction import TextExtractor
from modules.cleaner import TextCleaner
from modules.chunker import TextChunker
from modules.translation import GoogleTranslation  # Using Google Translate (free)
# from modules.pipeline import TranslationPipeline  # OpenRouter (kept for reference)

# Initialize logger (will be reconfigured with config)
logger = None


def estimate_cost(
    total_words: int,
    translator,
    token_multiplier: float = 1.5
) -> float:
    """Estimate translation cost.
    
    Args:
        total_words: Total number of words
        translator: Translator instance
        token_multiplier: Word to token multiplier
        
    Returns:
        Estimated cost
    """
    return translator.estimate_cost(total_words, token_multiplier)


def check_cost_guardrail(
    estimated_cost: float,
    abort_threshold: Optional[float],
    currency: str = "INR"
):
    """Check cost against guardrail threshold.
    
    Args:
        estimated_cost: Estimated cost
        abort_threshold: Maximum allowed cost
        currency: Currency code
        
    Raises:
        CostThresholdExceededError: If cost exceeds threshold
    """
    if abort_threshold is not None and estimated_cost > abort_threshold:
        raise CostThresholdExceededError(
            f"Estimated cost {currency} {estimated_cost:.2f} exceeds "
            f"threshold {currency} {abort_threshold:.2f}"
        )


def run_pipeline(
    config_path: str = "config.yaml",
    source_paths: list = None,
    force_restart: bool = False
):
    """Run the complete NICO-Forge pipeline.
    
    Args:
        config_path: Path to config file
        source_paths: List of source file/directory paths
        force_restart: If True, clear state and restart from beginning
    """
    global logger
    
    # Load configuration
    print("Loading configuration...")
    config = ConfigLoader(config_path)
    
    # Setup logger
    logger = setup_logger(
        "nico-forge",
        log_dir=config.get("logging", "log_dir"),
        console_level=config.get("logging", "console_level", default="INFO"),
        file_level=config.get("logging", "file_level", default="DEBUG")
    )
    
    logger.info("="*60)
    logger.info("NICO-FORGE Pipeline Starting")
    logger.info("="*60)
    
    # Initialize state manager
    state_dir = Path(config.get("outputs", "base_dir")) / ".state"
    state_manager = StateManager(state_dir)
    
    if force_restart:
        logger.info("Force restart: Clearing all state")
        state_manager.clear_state()
    
    # Setup paths
    base_dir = Path(config.get("outputs", "base_dir"))
    base_dir.mkdir(parents=True, exist_ok=True)
    
    raw_text_path = base_dir / config.get("outputs", "raw_text")
    cleaned_text_path = base_dir / config.get("outputs", "cleaned_text")
    chunks_manifest_path = base_dir / config.get("outputs", "chunks_manifest")
    dataset_csv_path = base_dir / config.get("outputs", "dataset_csv")
    dataset_json_path = base_dir / config.get("outputs", "dataset_json")
    metadata_path = base_dir / config.get("outputs", "metadata")
    
    failed_dir = base_dir / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    
    # Track pipeline start time
    pipeline_start = datetime.now()
    
    # ========================================================================
    # STEP 1: EXTRACTION
    # ========================================================================
    if not state_manager.is_completed("extraction"):
        logger.info("STEP 1: Extracting text from sources")
        
        if not source_paths:
            logger.error("No source paths provided")
            return
        
        extractor = TextExtractor(
            output_path=raw_text_path,
            failed_output=failed_dir / "extraction_failed.json",
            max_file_size_mb=config.get("extraction", "max_file_size_mb", default=100),
            state_manager=state_manager
        )
        
        extraction_stats = extractor.extract_from_sources(source_paths)
        logger.info(f"Extraction complete: {extraction_stats}")
    else:
        logger.info("STEP 1: Skipping extraction (already completed)")
    
    # ========================================================================
    # STEP 2: CLEANING
    # ========================================================================
    if not state_manager.is_completed("cleaner"):
        logger.info("STEP 2: Cleaning extracted text")
        
        cleaner = TextCleaner(
            output_path=cleaned_text_path,
            preview_path=base_dir / "clean_preview.txt",
            state_manager=state_manager,
            remove_urls=config.get("cleaning", "remove_urls", default=True),
            remove_emails=config.get("cleaning", "remove_emails", default=True),
            remove_references=config.get("cleaning", "remove_references", default=True),
            normalize_whitespace=config.get("cleaning", "normalize_whitespace", default=True)
        )
        
        cleaning_stats = cleaner.clean(raw_text_path)
        logger.info(f"Cleaning complete: {cleaning_stats}")
    else:
        logger.info("STEP 2: Skipping cleaning (already completed)")
    
    # ========================================================================
    # STEP 3: CHUNKING
    # ========================================================================
    if not state_manager.is_completed("chunker"):
        logger.info("STEP 3: Chunking and deduplication")
        
        chunker = TextChunker(
            chunk_size=config.get("pipeline", "chunk_size"),
            manifest_path=chunks_manifest_path,
            state_manager=state_manager,
            enable_deduplication=config.get("deduplication", "enabled", default=True),
            fuzzy_matching=config.get("deduplication", "fuzzy_matching", default=False)
        )
        
        chunking_stats = chunker.chunk(
            cleaned_text_path,
            source_file=str(raw_text_path)
        )
        logger.info(f"Chunking complete: {chunking_stats}")
    else:
        logger.info("STEP 3: Skipping chunking (already completed)")
        # Load chunks from manifest
        import json
        with open(chunks_manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        chunking_stats = {
            "total_chunks": manifest["total_chunks"],
            "unique_chunks": manifest["unique_chunks"],
            "chunks": manifest["chunks"]
        }
    
    chunks = chunking_stats["chunks"]
    
    # ========================================================================
    # STEP 4: TRANSLATION (Using Google Translate - Free!)
    # ========================================================================
    if not state_manager.is_completed("translation"):
        logger.info("="*60)
        logger.info("STEP 4: Translation (Google Translate - Free!)")
        logger.info("="*60)
        
        translation = GoogleTranslation(
            output_csv=dataset_csv_path,
            output_json=dataset_json_path,
            failed_output=failed_dir / "translation_failed.json",
            qc_failed_output=failed_dir / "translation_qc_failed.json",
            state_manager=state_manager,
            qa_sample_rate=config.get("qa", "sample_rate"),
            qa_min_samples=config.get("qa", "min_samples"),
            devanagari_threshold=config.get("qa", "devanagari_threshold"),
            max_length_ratio=config.get("qa", "max_length_ratio"),
            min_length_ratio=config.get("qa", "min_length_ratio")
        )
        
        translation_stats = translation.translate_chunks(chunks)
        logger.info(f"Translation complete: {translation_stats}")
    else:
        logger.info("STEP 4: Skipping translation (already completed)")
        translation_stats = {
            "total_translated": len(chunks),
            "failed": 0,
            "qc_failed": 0
        }
    
    # ========================================================================
    # FINAL REPORT
    # ========================================================================
    pipeline_end = datetime.now()
    duration = (pipeline_end - pipeline_start).total_seconds()
    
    logger.info("="*60)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*60)
    logger.info(f"Total duration: {duration:.2f}s ({duration/60:.2f}m)")
    logger.info(f"Chunks translated: {translation_stats['total_translated']}")
    logger.info(f"Failed chunks: {translation_stats['failed']}")
    logger.info(f"QC failed: {translation_stats['qc_failed']}")
    logger.info(f"Output CSV: {dataset_csv_path}")
    logger.info(f"Output JSON: {dataset_json_path}")
    
    # Save metadata
    import json
    metadata = {
        "pipeline": "NICO-Forge",
        "version": "1.0",
        "completed_at": pipeline_end.isoformat(),
        "duration_seconds": duration,
        "config": config.get_all(),
        "statistics": {
            "chunks_translated": translation_stats['total_translated'],
            "failed_chunks": translation_stats['failed'],
            "qc_failed": translation_stats['qc_failed'],
            "translator": "Google Translate (free)"
        },
        "outputs": {
            "csv": str(dataset_csv_path),
            "json": str(dataset_json_path)
        }
    }
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Metadata saved: {metadata_path}")
    logger.info("="*60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NICO-Forge: English-Hindi Dataset Generation Pipeline"
    )
    
    parser.add_argument(
        "sources",
        nargs="+",
        help="Source files or directories to process"
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    
    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Clear state and restart from beginning"
    )
    
    args = parser.parse_args()
    
    try:
        run_pipeline(
            config_path=args.config,
            source_paths=args.sources,
            force_restart=args.force_restart
        )
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        print("State has been saved. Run again to resume.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nPipeline failed: {e}")
        if logger:
            logger.exception("Pipeline failed with exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
