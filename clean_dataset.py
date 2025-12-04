"""
Data Cleaning Script for NICO-Forge Datasets

This script cleans English-Hindi parallel datasets by:
- Removing newline characters (\n, \r, \t)
- Fixing repetitive OCR errors
- Normalizing whitespace
- Removing artifacts that could affect LLM training

Usage:
    python clean_dataset.py --input outputs/en_hi_dataset.json --output outputs/cleaned_dataset.json
    python clean_dataset.py --input outputs/en_hi_dataset.csv --output outputs/cleaned_dataset.csv
"""

import json
import csv
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextCleaner:
    """Handles all text cleaning operations"""
    
    @staticmethod
    def remove_newlines(text: str) -> str:
        """Remove all newline, carriage return, and tab characters"""
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        text = text.replace('\t', ' ')
        return text
    
    @staticmethod
    def fix_repetitive_patterns(text: str) -> str:
        """
        Fix repetitive OCR errors like 'UNDERSTUNDERSTUNDERST'
        Detects patterns where a word fragment repeats 3+ times consecutively
        """
        # Pattern: capture a word/fragment that repeats 3+ times
        # Look for sequences like "UNDERST" repeated multiple times
        pattern = r'\b(\w{3,}?)(\1{2,})\b'
        
        def replace_repetition(match):
            word_fragment = match.group(1)
            # Keep only one instance of the repeated fragment
            return word_fragment
        
        text = re.sub(pattern, replace_repetition, text, flags=re.IGNORECASE)
        return text
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize multiple spaces to single space and strip"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    @staticmethod
    def remove_page_artifacts(text: str) -> str:
        """Remove common PDF extraction artifacts"""
        # Remove 'Reprint YYYY-YY' patterns
        text = re.sub(r'Reprint\s+\d{4}-\d{2,4}', '', text)
        
        # Remove standalone numbers that are likely page numbers or section numbers
        # Only if they're at the start/end or surrounded by spaces
        text = re.sub(r'\s+\d+\.\d+(\.\d+)*\s+', ' ', text)
        
        return text
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        """Apply all cleaning operations to text"""
        if not text or not isinstance(text, str):
            return text
        
        text = cls.remove_newlines(text)
        text = cls.fix_repetitive_patterns(text)
        text = cls.remove_page_artifacts(text)
        text = cls.normalize_whitespace(text)
        
        return text


class DatasetCleaner:
    """Cleans datasets in JSON or CSV format"""
    
    def __init__(self, input_path: str, output_path: str):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.cleaner = TextCleaner()
        self.stats = {
            'total_entries': 0,
            'cleaned_entries': 0,
            'empty_entries_removed': 0,
            'avg_english_length': 0,
            'avg_hindi_length': 0
        }
    
    def clean_json_dataset(self):
        """Clean JSON format dataset"""
        logger.info(f"Reading JSON dataset from: {self.input_path}")
        
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total_entries'] = len(data)
        cleaned_data = []
        
        english_lengths = []
        hindi_lengths = []
        
        for entry in data:
            # Clean English and Hindi text
            cleaned_english = self.cleaner.clean_text(entry.get('english', ''))
            cleaned_hindi = self.cleaner.clean_text(entry.get('hindi', ''))
            
            # Skip entries with very short or empty text (likely artifacts)
            if len(cleaned_english.strip()) < 10 or len(cleaned_hindi.strip()) < 10:
                self.stats['empty_entries_removed'] += 1
                continue
            
            # Create cleaned entry
            cleaned_entry = {
                'chunk_id': entry.get('chunk_id'),
                'english': cleaned_english,
                'hindi': cleaned_hindi,
                'metadata': entry.get('metadata', {})
            }
            
            cleaned_data.append(cleaned_entry)
            english_lengths.append(len(cleaned_english))
            hindi_lengths.append(len(cleaned_hindi))
        
        self.stats['cleaned_entries'] = len(cleaned_data)
        if english_lengths:
            self.stats['avg_english_length'] = sum(english_lengths) / len(english_lengths)
        if hindi_lengths:
            self.stats['avg_hindi_length'] = sum(hindi_lengths) / len(hindi_lengths)
        
        # Save cleaned data
        logger.info(f"Writing cleaned JSON dataset to: {self.output_path}")
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    def clean_csv_dataset(self):
        """Clean CSV format dataset"""
        logger.info(f"Reading CSV dataset from: {self.input_path}")
        
        with open(self.input_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
        
        self.stats['total_entries'] = len(rows)
        cleaned_rows = []
        
        english_lengths = []
        hindi_lengths = []
        
        for row in rows:
            # Clean English and Hindi text
            cleaned_english = self.cleaner.clean_text(row.get('english', ''))
            cleaned_hindi = self.cleaner.clean_text(row.get('hindi', ''))
            
            # Skip entries with very short or empty text
            if len(cleaned_english.strip()) < 10 or len(cleaned_hindi.strip()) < 10:
                self.stats['empty_entries_removed'] += 1
                continue
            
            # Update row with cleaned text
            row['english'] = cleaned_english
            row['hindi'] = cleaned_hindi
            
            cleaned_rows.append(row)
            english_lengths.append(len(cleaned_english))
            hindi_lengths.append(len(cleaned_hindi))
        
        self.stats['cleaned_entries'] = len(cleaned_rows)
        if english_lengths:
            self.stats['avg_english_length'] = sum(english_lengths) / len(english_lengths)
        if hindi_lengths:
            self.stats['avg_hindi_length'] = sum(hindi_lengths) / len(hindi_lengths)
        
        # Save cleaned data
        logger.info(f"Writing cleaned CSV dataset to: {self.output_path}")
        with open(self.output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cleaned_rows)
    
    def clean(self):
        """Clean dataset based on file extension"""
        if self.input_path.suffix == '.json':
            self.clean_json_dataset()
        elif self.input_path.suffix == '.csv':
            self.clean_csv_dataset()
        else:
            raise ValueError(f"Unsupported file format: {self.input_path.suffix}")
        
        self.print_stats()
    
    def print_stats(self):
        """Print cleaning statistics"""
        logger.info("\n" + "="*60)
        logger.info("CLEANING STATISTICS")
        logger.info("="*60)
        logger.info(f"Total entries processed: {self.stats['total_entries']}")
        logger.info(f"Cleaned entries: {self.stats['cleaned_entries']}")
        logger.info(f"Empty/short entries removed: {self.stats['empty_entries_removed']}")
        logger.info(f"Average English text length: {self.stats['avg_english_length']:.1f} chars")
        logger.info(f"Average Hindi text length: {self.stats['avg_hindi_length']:.1f} chars")
        logger.info("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Clean NICO-Forge datasets for LLM training'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input dataset file (JSON or CSV)'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output cleaned dataset file'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        return
    
    # Clean dataset
    cleaner = DatasetCleaner(args.input, args.output)
    cleaner.clean()
    
    logger.info(f"✓ Dataset cleaning completed successfully!")
    logger.info(f"✓ Cleaned dataset saved to: {args.output}")


if __name__ == '__main__':
    main()
