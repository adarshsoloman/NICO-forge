# NICO-Forge 🔥

**English–Hindi Bilingual Dataset Generation Pipeline**

NICO-Forge is a modular, production-ready pipeline that converts raw documents (PDF/DOCX/TXT) into high-quality bilingual English–Hindi datasets for machine learning and NLP applications.

## Features

- 📄 **Multi-format extraction**: PDF, DOCX, TXT with streaming support for large files
- 🧹 **Intelligent cleaning**: Removes URLs, emails, references, unicode artifacts
- ✂️ **Smart chunking**: Fixed-size segments with SHA256-based deduplication
- 🌐 **Pluggable translation**: Adapter pattern supporting multiple translation APIs
- 🔄 **Resume capability**: Crash-tolerant with incremental state saving
- ✅ **Quality assurance**: Devanagari validation and automated QA sampling
- 💰 **Cost controls**: Pre-flight estimation and configurable spending guardrails
- 📊 **Rich metadata**: Full provenance tracking for reproducibility
- ⚡ **Async processing**: Concurrent translation with exponential backoff retry

## Quick Start

### 1. Installation

```bash
# Clone or navigate to project directory
cd NICO-forge

# Create virtual environment with uv
uv venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Configuration

Copy the environment template and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```
OPENROUTER_API_KEY=your_key_here
```

### 3. Run Pipeline

```bash
python main.py path/to/your/documents
```

Or point to a specific file:

```bash
python main.py document.pdf another.docx
```

### 4. Check Outputs

Results are saved to `outputs/`:

```
outputs/
├── en_hi_dataset.csv       # CSV dataset
├── en_hi_dataset.json      # JSON dataset with metadata
├── metadata.json           # Pipeline statistics
├── chunks_manifest.json    # Chunking details
└── failed/                 # Failed translations (if any)
```

## Data Cleaning & Preparation

### Why Clean Your Dataset?

Raw datasets extracted from PDFs often contain artifacts that can negatively impact LLM training:
- ❌ Newline characters (`\n`, `\r`, `\t`) embedded in text
- ❌ Repetitive OCR errors (e.g., "UNDERSTUNDERSTUNDERST")
- ❌ PDF extraction artifacts (page numbers, reprint notices, section numbers)
- ❌ Excessive whitespace and formatting issues

The cleaning pipeline ensures your training data is pristine and ready for model fine-tuning.

### Clean Datasets

Use `clean_dataset.py` to prepare your datasets for LLM training:

```bash
# Clean JSON dataset
python clean_dataset.py --input outputs/en_hi_dataset.json --output outputs/cleaned_dataset.json

# Clean CSV dataset
python clean_dataset.py --input outputs/en_hi_dataset.csv --output outputs/cleaned_dataset.csv
```

**What gets cleaned:**
- ✅ Removes all newline, tab, and carriage return characters
- ✅ Fixes repetitive OCR patterns using regex detection
- ✅ Removes PDF artifacts (page numbers, "Reprint 2025-26" text)
- ✅ Normalizes whitespace (multiple spaces → single space)
- ✅ Filters out very short entries (< 10 characters)
- ✅ Preserves metadata and structure

**Output:**
```
============================================================
CLEANING STATISTICS
============================================================
Total entries processed: 110
Cleaned entries: 110
Empty/short entries removed: 0
Average English text length: 245.3 chars
Average Hindi text length: 228.7 chars
============================================================
```

### Merge Multiple Datasets

After processing multiple PDF pairs, combine them into a single dataset using `merge_datasets.py`:

```bash
# Merge specific files
python merge_datasets.py --inputs cleaned_1.json cleaned_2.json --output final_dataset.json

# Merge all cleaned files using wildcards
python merge_datasets.py --inputs outputs/cleaned_*.json --output outputs/merged_dataset.json

# Merge CSV files
python merge_datasets.py --inputs outputs/cleaned_*.csv --output outputs/merged_dataset.csv

# Keep original chunk_ids (no renumbering)
python merge_datasets.py --inputs file1.json file2.json --output merged.json --no-renumber
```

**Features:**
- ✅ Supports both JSON and CSV formats
- ✅ Automatic sequential renumbering of chunk_ids
- ✅ Wildcard support for batch merging (`*.json`)
- ✅ Detailed statistics per file and total counts
- ✅ Preserves all metadata from source files

**Output:**
```
============================================================
MERGE STATISTICS
============================================================
Output format: JSON
Files processed: 3
Total entries in merged dataset: 342

Entries per file:
  - cleaned_dataset_1.json: 110 entries
  - cleaned_dataset_2.json: 125 entries
  - cleaned_dataset_3.json: 107 entries
============================================================
```

### Complete Workflow Example

Process multiple books and create a final training dataset:

```bash
# Step 1: Extract parallel text from multiple PDF pairs
python main.py --english book1_en.pdf --hindi book1_hi.pdf
# Rename outputs: mv outputs/en_hi_dataset.json outputs/raw_book1.json

python main.py --english book2_en.pdf --hindi book2_hi.pdf
# Rename outputs: mv outputs/en_hi_dataset.json outputs/raw_book2.json

python main.py --english book3_en.pdf --hindi book3_hi.pdf
# Rename outputs: mv outputs/en_hi_dataset.json outputs/raw_book3.json

# Step 2: Clean each dataset
python clean_dataset.py --input outputs/raw_book1.json --output outputs/cleaned_book1.json
python clean_dataset.py --input outputs/raw_book2.json --output outputs/cleaned_book2.json
python clean_dataset.py --input outputs/raw_book3.json --output outputs/cleaned_book3.json

# Step 3: Merge all cleaned datasets
python merge_datasets.py --inputs outputs/cleaned_book*.json --output outputs/FINAL_TRAINING_DATASET.json
```

Now your `FINAL_TRAINING_DATASET.json` is ready for LLM training! 🚀

## Configuration

Edit `config.yaml` to customize:

```yaml
pipeline:
  chunk_size: 60          # Words per chunk
  batch_size: 20          # Chunks per API call
  concurrency: 10         # Parallel workers

translation:
  model: "google/gemini-2.0-flash-thinking-exp:free"
  retries: 3
  timeout: 30

cost:
  abort_threshold: 1000   # Abort if cost exceeds ₹1000
  
qa:
  sample_rate: 0.01       # QA 1% of translations
  devanagari_threshold: 0.7  # Min 70% Devanagari chars
```

## Advanced Usage

### Resume After Interruption

If the pipeline crashes or is interrupted, simply run it again:

```bash
python main.py path/to/documents
```

State is automatically saved. The pipeline will skip completed stages.

### Force Restart

To clear state and restart from beginning:

```bash
python main.py --force-restart path/to/documents
```

### Custom Config

Use a different config file:

```bash
python main.py --config my-config.yaml path/to/documents
```

## Architecture

```
NICO-forge/
├── config.yaml              # Configuration
├── main.py                  # Main orchestrator
├── clean_dataset.py         # Dataset cleaning utility
├── merge_datasets.py        # Dataset merging utility
├── modules/
│   ├── extraction.py        # PDF/DOCX/TXT extraction
│   ├── cleaner.py          # Text cleaning
│   ├── chunker.py          # Chunking + deduplication
│   ├── pipeline.py         # Translation pipeline
│   └── translators/
│       ├── base.py         # Abstract translator
│       └── openrouter.py   # OpenRouter adapter
└── utils/
    ├── config_loader.py    # Config management
    ├── logger.py           # Structured logging
    ├── progress.py         # Progress bars
    ├── state_manager.py    # Resume capability
    └── exceptions.py       # Custom exceptions
```

## Pipeline Stages

1. **Extraction**: Extract text from PDFs, DOCX, TXT files
2. **Cleaning**: Remove noise, normalize whitespace
3. **Chunking**: Split into 60-word segments with deduplication
4. **Cost Estimation**: Calculate and verify translation costs
5. **Translation**: Async batch translation with retry logic
6. **QA Sampling**: Validate 1% of translations for quality
7. **Export**: Generate CSV + JSON datasets

## Translation Adapters

NICO-Forge uses a pluggable adapter pattern. Currently supported:

- **OpenRouter** (default): Access to multiple LLM providers

### Adding Custom Translators

Extend `BaseTranslator` in `modules/translators/base.py`:

```python
class MyTranslator(BaseTranslator):
    async def translate_batch(self, chunks: List[str]) -> List[str]:
        # Your implementation
        pass
    
    def get_model_info(self) -> dict:
        return {"adapter": "my-translator", "model": "..."}
    
    def estimate_cost(self, word_count: int) -> float:
        # Cost calculation
        return 0.0
```

## Quality Assurance

The pipeline automatically validates translations:

- ✅ **Devanagari check**: Ensures ≥70% Devanagari characters
- ✅ **Length ratio**: Flags suspicious length mismatches
- ✅ **Empty response**: Catches blank translations
- ✅ **Error detection**: Identifies error markers

Failed QA samples are saved to `outputs/failed/translation_qc_failed.json`.

## Cost Controls

### Pre-flight Estimation

Before translation, the pipeline estimates costs:

```
Unique chunks to translate: 4,355
Total words: 246,780
Estimated cost: ₹ 487.50
```

### Guardrails

Set `abort_threshold` in config to prevent runaway costs:

```yaml
cost:
  abort_threshold: 1000  # Abort if > ₹1000
```

## Logging

Logs are saved to `outputs/logs/`:

- **Console**: INFO level (progress, key events)
- **File**: DEBUG level (everything)

## Troubleshooting

### API Key Errors

```
APIKeyMissingError: OpenRouter API key not provided
```

**Solution**: Set `OPENROUTER_API_KEY` in `.env` file.

### Rate Limit Errors

The pipeline automatically retries with exponential backoff.

To reduce rate limits:
- Decrease `concurrency` in config
- Decrease `batch_size`

### Empty Translations

Check `outputs/failed/translation_failed.json` for error details.

### QA Failures

High QA failure rate (>2%) may indicate:
- Wrong model selected
- Poor source text quality
- API issues

Check `outputs/failed/translation_qc_failed.json` for specifics.

## Development

### Project Structure

```
├── .env                    # API keys (gitignored)
├── .env.example            # Template
├── config.yaml             # Configuration
├── requirements.txt        # Dependencies
├── main.py                 # Entry point
├── clean_dataset.py        # Data cleaning utility
├── merge_datasets.py       # Dataset merging utility
├── modules/                # Core pipeline modules
├── utils/                  # Utilities
└── outputs/                # Generated files (gitignored)
```

### Dependencies

- `PyPDF2`: PDF extraction
- `python-docx`: DOCX extraction
- `aiohttp`: Async HTTP for translation
- `tenacity`: Retry logic
- `tqdm`: Progress bars
- `pyyaml`: Config parsing

## Performance

Typical throughput (with free tier models):

- **Extraction**: ~50 pages/sec
- **Cleaning**: ~10,000 lines/sec
- **Chunking**: ~100,000 words/sec
- **Translation**: ~20-50 chunks/sec (depends on API, concurrency)

## License

This project is provided as-is for research and development purposes.

## Support

For issues, questions, or contributions, please refer to your project repository or contact the development team.

---

**Built with ❤️ for bilingual NLP research**
