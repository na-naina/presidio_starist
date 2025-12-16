# Quick Start Guide

## Ubuntu 24.04 - 2 Steps

### Step 1: Install
```bash
git clone <repository-url>
cd presidio_demo-1
chmod +x install_ubuntu.sh
./install_ubuntu.sh
```

### Step 2: Run
Double-click **`run_app.sh`** (or run `streamlit run 1_📂_Batch_Anonymization.py`)

The application opens automatically at **http://localhost:8501**

---

## Manual Start (Terminal)

```bash
source presidio-venv/bin/activate
streamlit run 1_📂_Batch_Anonymization.py
```

---

## First Time Usage

1. **Upload files** using the file uploader
2. Click **🚀 Anonymize**
3. Download the **ZIP file** with anonymized documents

> ⏳ First run downloads NER models (~1.5GB). This is normal and only happens once.

---

## Default Settings (Recommended for Most Use Cases)

| Setting | Default | Description |
|---------|---------|-------------|
| Model | flair/ner-english-large | Best accuracy |
| Approach | replace | `John Smith` → `PERSON_1` |
| Track Entity IDs | ✓ Enabled | Same person = same ID |
| Threshold | 0.35 | Balanced detection |

---

## Troubleshooting

**App won't start?**
```bash
source presidio-venv/bin/activate  # Must activate venv first!
```

**Port in use?**
```bash
streamlit run 1_📂_Batch_Anonymization.py --server.port 8502
```

**See full documentation:** [README.md](README.md)
