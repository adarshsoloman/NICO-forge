"""
Dataset Merger for NICO-Forge

Merges multiple cleaned English-Hindi datasets into a single combined dataset.
Supports both JSON and CSV formats.

Usage:
    # Merge JSON files
    python merge_datasets.py --inputs cleaned_1.json cleaned_2.json cleaned_3.json --output final_dataset.json
    
    # Merge CSV files
    python merge_datasets.py --inputs cleaned_1.csv cleaned_2.csv cleaned_3.csv --output final_dataset.csv
    
    # Merge all JSON files in outputs folder
    python merge_datasets.py --inputs outputs/cleaned_*.json --output outputs/final_merged.json
"""

import json
import csv
import argparse
from pathlib import Path
from typing import List
import logging
import glob

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetMerger:
    """Merges multiple datasets into a single combined dataset"""
    
    def __init__(self, input_files: List[str], output_file: str, renumber: bool = True):
        self.input_files = [Path(f) for f in input_files]
        self.output_file = Path(output_file)
        self.renumber = renumber
        self.stats = {
            'files_processed': 0,
            'total_entries': 0,
            'entries_per_file': {},
            'output_format': None
        }
    
    def merge_json_files(self):
        """Merge multiple JSON files"""
        logger.info(f"Merging {len(self.input_files)} JSON files...")
        
        merged_data = []
        chunk_id_counter = 1
        
        for file_path in self.input_files:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}, skipping...")
                continue
            
            logger.info(f"Reading: {file_path.name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Track statistics
            entries_count = len(data)
            self.stats['entries_per_file'][file_path.name] = entries_count
            self.stats['files_processed'] += 1
            
            # Renumber chunk_ids if requested
            if self.renumber:
                for entry in data:
                    entry['chunk_id'] = chunk_id_counter
                    chunk_id_counter += 1
            
            merged_data.extend(data)
        
        self.stats['total_entries'] = len(merged_data)
        self.stats['output_format'] = 'JSON'
        
        # Save merged dataset
        logger.info(f"Writing merged dataset to: {self.output_file}")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    def merge_csv_files(self):
        """Merge multiple CSV files"""
        logger.info(f"Merging {len(self.input_files)} CSV files...")
        
        merged_rows = []
        chunk_id_counter = 1
        fieldnames = None
        
        for file_path in self.input_files:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}, skipping...")
                continue
            
            logger.info(f"Reading: {file_path.name}")
            
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                
                # Get fieldnames from first file
                if fieldnames is None:
                    fieldnames = reader.fieldnames
                
                rows = list(reader)
            
            # Track statistics
            entries_count = len(rows)
            self.stats['entries_per_file'][file_path.name] = entries_count
            self.stats['files_processed'] += 1
            
            # Renumber chunk_ids if requested
            if self.renumber:
                for row in rows:
                    row['chunk_id'] = str(chunk_id_counter)
                    chunk_id_counter += 1
            
            merged_rows.extend(rows)
        
        self.stats['total_entries'] = len(merged_rows)
        self.stats['output_format'] = 'CSV'
        
        # Save merged dataset
        logger.info(f"Writing merged dataset to: {self.output_file}")
        with open(self.output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(merged_rows)
    
    def merge(self):
        """Merge datasets based on output file extension"""
        # Validate inputs
        if not self.input_files:
            raise ValueError("No input files provided")
        
        # Determine format from output file extension
        if self.output_file.suffix == '.json':
            self.merge_json_files()
        elif self.output_file.suffix == '.csv':
            self.merge_csv_files()
        else:
            raise ValueError(f"Unsupported output format: {self.output_file.suffix}")
        
        self.print_stats()
    
    def print_stats(self):
        """Print merge statistics"""
        logger.info("\n" + "="*60)
        logger.info("MERGE STATISTICS")
        logger.info("="*60)
        logger.info(f"Output format: {self.stats['output_format']}")
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Total entries in merged dataset: {self.stats['total_entries']}")
        logger.info("\nEntries per file:")
        for filename, count in self.stats['entries_per_file'].items():
            logger.info(f"  - {filename}: {count} entries")
        logger.info("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Merge multiple NICO-Forge datasets into one',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge specific JSON files
  python merge_datasets.py --inputs cleaned_1.json cleaned_2.json --output final.json
  
  # Merge all cleaned JSON files in outputs folder
  python merge_datasets.py --inputs outputs/cleaned_*.json --output outputs/merged.json
  
  # Merge CSV files without renumbering
  python merge_datasets.py --inputs file1.csv file2.csv --output merged.csv --no-renumber
        """
    )
    
    parser.add_argument(
        '--inputs',
        nargs='+',
        required=True,
        help='Input dataset files to merge (supports wildcards like *.json)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output merged dataset file (extension determines format)'
    )
    
    parser.add_argument(
        '--no-renumber',
        action='store_true',
        help='Keep original chunk_ids instead of renumbering sequentially'
    )
    
    args = parser.parse_args()
    
    # Expand wildcards in input files
    input_files = []
    for pattern in args.inputs:
        expanded = glob.glob(pattern)
        if expanded:
            input_files.extend(expanded)
        else:
            input_files.append(pattern)  # Keep original if no wildcard match
    
    # Remove duplicates while preserving order
    input_files = list(dict.fromkeys(input_files))
    
    if not input_files:
        logger.error("No input files found!")
        return
    
    logger.info(f"Found {len(input_files)} files to merge")
    
    # Merge datasets
    merger = DatasetMerger(
        input_files=input_files,
        output_file=args.output,
        renumber=not args.no_renumber
    )
    merger.merge()
    
    logger.info(f"✓ Datasets merged successfully!")
    logger.info(f"✓ Merged dataset saved to: {args.output}")


if __name__ == '__main__':
    main()
