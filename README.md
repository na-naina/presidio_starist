---
title: Presidio Demo
emoji: 🅿
colorFrom: purple
colorTo: gray
sdk: docker
app_port: 7860
license: mit
---

# STARIST - Presidio De-identification Tool

**STARIST: Stalking Threat AI Recognition (and) Identification Support Tool**

A powerful PII (Personally Identifiable Information) detection and anonymization tool built on [Microsoft Presidio](https://microsoft.github.io/presidio/), designed for processing sensitive documents in law enforcement and investigative contexts.

---

## 🚀 Quick Start (Ubuntu 24.04)

### Method 1: Quick Setup (3 Commands)

```bash
# Clone the repository
git clone <repository-url>
cd presidio_demo-1

# Run the installation script
chmod +x install_ubuntu.sh
./install_ubuntu.sh

# Start the application
source presidio-venv/bin/activate
streamlit run 1_📂_Batch_Anonymization.py
```

### Method 2: Double-Click to Launch (After Installation)

Once `install_ubuntu.sh` completes, you can double-click **`run_app.sh`** to launch the application.

The application will open in your browser at **http://localhost:8501**

---

## 📋 Table of Contents

- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
  - [Ubuntu 24.04 (Recommended)](#ubuntu-2404-recommended)
  - [Other Linux Distributions](#other-linux-distributions)
  - [Docker](#docker)
- [Application Pages](#-application-pages)
- [Supported File Formats](#-supported-file-formats)
- [Configuration Options](#%EF%B8%8F-configuration-options)
- [Entity Tracking](#-entity-tracking)
- [Troubleshooting](#-troubleshooting)
- [Environment Variables](#-environment-variables)

---

## ✨ Features

- **Batch Processing**: Anonymize multiple files at once with ZIP download
- **Entity ID Tracking**: Same person mentioned multiple times receives consistent IDs (PERSON_1, PERSON_2, etc.)
- **Chronological Date Ordering**: Dates are assigned IDs in chronological order
- **Multiple NER Models**: Support for spaCy, Flair, Stanza, and HuggingFace transformers
- **Flexible Anonymization**: Replace, redact, mask, hash, or encrypt PII
- **Allowlist/Denylist**: Customize what should or shouldn't be treated as PII
- **Generic Term Exclusion**: Automatically excludes terms like "caller", "victim", "suspect"
- **Multiple File Formats**: Text, CSV, Excel, Word documents, and more

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Ubuntu 24.04 LTS (or compatible Linux distribution)
- **Python**: 3.10.x
- **RAM**: 8 GB (16 GB recommended for large files)
- **Storage**: 5 GB free space (for models and dependencies)
- **CPU**: Multi-core processor recommended

### Tested Configurations
- Ubuntu 24.04 LTS with Python 3.10
- macOS 14+ with Python 3.10
- Windows 11 with WSL2 (Ubuntu 24.04)

---

## 📦 Installation

### Ubuntu 24.04 (Recommended)

**Option 1: Automated Installation (Recommended)**

```bash
# Clone the repository
git clone <repository-url>
cd presidio_demo-1

# Make the script executable and run it
chmod +x install_ubuntu.sh
./install_ubuntu.sh
```

**Option 2: Manual Installation**

```bash
# 1. Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3.10-dev build-essential gcc g++

# 2. Create and activate virtual environment
python3.10 -m venv presidio-venv
source presidio-venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip setuptools wheel

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Download spaCy models
python -m spacy download en_core_web_lg
python -m spacy download en_core_web_sm
```

### Other Linux Distributions

The installation process is similar for other distributions. Ensure you have:
- Python 3.10
- Development tools (gcc, g++, make)
- Python development headers

### Docker

```bash
# Build the Docker image
docker build -t starist .

# Run the container
docker run -p 7860:7860 starist
```

Access at **http://localhost:7860**

---

## 📄 Application Pages

### 1. Batch Anonymization (Main Page)
The default landing page for processing multiple files simultaneously.

**Features:**
- Upload multiple files at once
- Process all files with consistent settings
- Download results as a ZIP archive
- View entity ID mappings for all processed files

### 2. Single File Analysis
Detailed analysis of individual text inputs with visualization.

**Features:**
- Real-time PII highlighting
- Decision process visualization
- Interactive entity exploration

---

## 📁 Supported File Formats

| Format | Extensions | Notes |
|--------|------------|-------|
| Plain Text | `.txt`, `.log` | UTF-8 encoding recommended |
| CSV/TSV | `.csv`, `.tsv` | Comma or tab-separated |
| JSON Lines | `.jsonl` | One JSON object per line |
| Word Documents | `.docx`, `.doc` | Microsoft Word format |
| Excel | `.xlsx`, `.xls`, `.xlsm` | Including macro-enabled workbooks |

---

## ⚙️ Configuration Options

### Detection Model

| Model | Description | Speed | Accuracy |
|-------|-------------|-------|----------|
| `flair/ner-english-large` | Default. Best accuracy for English | Slow | ⭐⭐⭐⭐⭐ |
| `spaCy/en_core_web_lg` | Good balance of speed and accuracy | Fast | ⭐⭐⭐⭐ |
| `HuggingFace/obi/deid_roberta_i2b2` | Medical/clinical text specialist | Medium | ⭐⭐⭐⭐ |
| `stanza/en` | Stanford NLP toolkit | Medium | ⭐⭐⭐⭐ |

> **Note**: Models are downloaded on first use (~500MB - 1.5GB). This is normal.

### Anonymization Methods

| Method | Description | Example |
|--------|-------------|---------|
| **Replace** | Replace with entity type labels | `John Smith` → `PERSON_1` |
| **Redact** | Completely remove the PII | `John Smith` → `` |
| **Mask** | Replace with mask characters | `John Smith` → `**********` |
| **Hash** | Replace with cryptographic hash | `John Smith` → `a1b2c3d4...` |
| **Encrypt** | AES encryption (reversible) | `John Smith` → `encrypted_text` |

### Detection Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Confidence Threshold** | Minimum score (0-1) to accept a detection | 0.35 |
| **Entity Types** | Select which PII types to detect | All types |
| **Track Entity IDs** | Assign unique IDs to each entity | Enabled |

### Custom Filters

| Filter | Description | Example |
|--------|-------------|---------|
| **Allowlist** | Terms that should NEVER be treated as PII | Company names, product names |
| **Denylist** | Terms that should ALWAYS be treated as PII | Specific names, codes |

---

## 🔍 Entity Tracking

When "Track Entity IDs" is enabled (default), the system:

1. **Assigns Unique IDs**: Each distinct entity gets a unique ID
   - `John Smith` → `PERSON_1`
   - `Jane Doe` → `PERSON_2`
   
2. **Maintains Consistency**: Same entity always gets the same ID
   - First mention: `John Smith` → `PERSON_1`
   - Second mention: `John Smith` → `PERSON_1` (same ID)

3. **Preserves Possessives**: Keeps grammatical structure
   - `John's car` → `PERSON_1's car`

4. **Chronological Dates**: Dates ordered by actual date
   - `13/12/2023` → `DATE_TIME_1`
   - `25/12/2023` → `DATE_TIME_2`

5. **Excludes Generic Terms**: Common descriptors are not anonymized
   - `caller`, `victim`, `suspect`, `witness`, `officer`, etc.

---

## 🔧 Troubleshooting

### Common Issues

**Problem: "Module not found" errors**
```bash
# Ensure virtual environment is activated
source presidio-venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Problem: "Model not found" on first run**
```bash
# Download spaCy models manually
python -m spacy download en_core_web_lg
python -m spacy download en_core_web_sm
```

**Problem: Out of memory errors**
- Close other applications
- Process fewer files at once
- Use a faster but lighter model (spaCy instead of Flair)

**Problem: Excel files not processing correctly**
```bash
# Ensure openpyxl and xlrd are installed
pip install openpyxl xlrd
```

**Problem: Slow performance**
- Flair models are slow but accurate; switch to spaCy for speed
- Reduce file batch size
- Consider using a machine with more RAM/CPU cores

### Port Already in Use

```bash
# Find process using port 8501
lsof -i :8501

# Kill the process
kill -9 <PID>

# Or run on a different port
streamlit run 1_📂_Batch_Anonymization.py --server.port 8502
```

---

## 🔐 Environment Variables

Create a `.env` file in the project root for additional configuration:

```bash
# Optional: Enable downloading additional models from UI
ALLOW_OTHER_MODELS=true

# Optional: Azure Text Analytics (if using Azure backend)
TA_KEY=your_azure_key
TA_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/

# Optional: OpenAI integration (for synthetic data generation)
OPENAI_TYPE=Azure  # or "openai"
OPENAI_KEY=your_openai_key
OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_ENDPOINT=https://your-openai-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

---

## 📂 Project Structure

```
presidio_demo-1/
├── 1_📂_Batch_Anonymization.py    # Main entry point (Batch processing)
├── pages/
│   └── 1_🔍_Presidio_Single_File.py  # Single file analysis page
├── presidio_helpers.py             # Core Presidio integration & entity tracking
├── presidio_nlp_engine_config.py   # NLP engine configuration
├── flair_recognizer.py             # Flair NER model integration
├── openai_fake_data_generator.py   # Synthetic data generation
├── azure_ai_language_wrapper.py    # Azure AI integration
├── images/
│   └── logos.png                   # Application logos
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Poetry configuration
├── install_ubuntu.sh               # Ubuntu installation script
├── Dockerfile                      # Docker configuration
└── README.md                       # This file
```

---

## 📜 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- [Microsoft Presidio](https://microsoft.github.io/presidio/) - Core PII detection and anonymization
- [Streamlit](https://streamlit.io/) - Web application framework
- [spaCy](https://spacy.io/) - Industrial-strength NLP
- [Flair](https://github.com/flairNLP/flair) - State-of-the-art NLP

---

## 📧 Support

For issues or questions, please open an issue in the repository.
