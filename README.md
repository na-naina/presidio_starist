---
title: Presidio Demo
emoji: 🅿
colorFrom: purple
colorTo: gray
sdk: docker
app_port: 7860
license: mit
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

## Application Structure

This Presidio demo application has two pages:
1. **Batch Anonymization** (Main/Default Page) - Process multiple files at once
2. **Single File Analysis** - Detailed analysis of individual text inputs

## Supported File Formats

**Batch Anonymization** supports the following file formats:
- Text files: `.txt`, `.log`, `.csv`, `.tsv`, `.jsonl`
- Documents: `.docx`, `.doc`
- Excel files: `.xlsx`, `.xls`, `.xlsm` (including macro-enabled)

## Running the Application

To start the application:
```bash
source presidio-venv/bin/activate
streamlit run 1_📂_Batch_Anonymization.py
```

The Batch Anonymization page will open by default. You can navigate to the Single File page using the sidebar.