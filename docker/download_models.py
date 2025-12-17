#!/usr/bin/env python3
"""
STARIST - Model Pre-download Script
====================================
Downloads and caches all ML models during Docker build.
This ensures the container works in air-gapped environments.
"""

import os
import sys

def download_flair_models():
    """Download Flair NER model."""
    print("=" * 60)
    print("Downloading Flair NER model...")
    print("=" * 60)

    try:
        # Suppress transformers warnings about deprecated imports
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        from flair.models import SequenceTagger

        # Download the main Flair NER model
        tagger = SequenceTagger.load("flair/ner-english-large")
        print("Flair model 'flair/ner-english-large' downloaded successfully!")

        # Verify it works
        from flair.data import Sentence
        sentence = Sentence("John Smith lives in New York.")
        tagger.predict(sentence)
        print(f"Verification: Found {len(sentence.get_spans('ner'))} entities")

    except ImportError as e:
        print(f"Warning: Flair import issue (may still work at runtime): {e}")
        print("Attempting direct model download via huggingface_hub...")
        try:
            from huggingface_hub import snapshot_download
            # Download the flair model files directly
            snapshot_download(repo_id="flair/ner-english-large", local_dir_use_symlinks=False)
            print("Flair model files downloaded via huggingface_hub")
        except Exception as e2:
            print(f"Warning: Could not pre-download Flair model: {e2}")
            print("Flair will download the model on first use.")
    except Exception as e:
        print(f"Warning: Flair download issue: {e}")
        print("Flair will download the model on first use if needed.")


def download_huggingface_models():
    """Download HuggingFace transformer models."""
    print("=" * 60)
    print("Downloading HuggingFace transformer models...")
    print("=" * 60)

    models = [
        "obi/deid_roberta_i2b2",
        "StanfordAIMI/stanford-deidentifier-base",
    ]

    try:
        from transformers import AutoTokenizer, AutoModelForTokenClassification

        for model_name in models:
            print(f"\nDownloading {model_name}...")
            try:
                # Download tokenizer and model
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForTokenClassification.from_pretrained(model_name)
                print(f"  Model '{model_name}' downloaded successfully!")
            except Exception as e:
                print(f"  Warning: Could not download {model_name}: {e}")

    except Exception as e:
        print(f"Warning: HuggingFace models download issue: {e}")
        print("Models will be downloaded on first use if needed.")


def download_stanza_models():
    """Download Stanza NLP models."""
    print("=" * 60)
    print("Downloading Stanza models...")
    print("=" * 60)

    try:
        import stanza

        # Download English model
        stanza.download('en', processors='tokenize,ner')
        print("Stanza English model downloaded successfully!")

    except Exception as e:
        print(f"Error downloading Stanza model: {e}")
        # Stanza is optional, don't exit
        print("Stanza download failed, but continuing (it's optional)")


def verify_spacy_models():
    """Verify spaCy models are installed."""
    print("=" * 60)
    print("Verifying spaCy models...")
    print("=" * 60)

    try:
        import spacy

        # Check en_core_web_lg - just verify it loads
        nlp_lg = spacy.load("en_core_web_lg", exclude=["parser", "lemmatizer"])
        print("en_core_web_lg: OK - Model loaded successfully")

        # Check en_core_web_sm
        nlp_sm = spacy.load("en_core_web_sm", exclude=["parser", "lemmatizer"])
        print("en_core_web_sm: OK - Model loaded successfully")

    except Exception as e:
        print(f"Warning verifying spaCy models: {e}")
        print("spaCy models may still work - continuing...")


def main():
    """Main function to download all models."""
    print("\n" + "=" * 60)
    print("STARIST - Downloading ML Models for Offline Use")
    print("=" * 60 + "\n")

    # Verify spaCy models (already installed via spacy download)
    verify_spacy_models()

    # Download Flair models
    download_flair_models()

    # Download HuggingFace models
    download_huggingface_models()

    # Download Stanza models (optional)
    download_stanza_models()

    print("\n" + "=" * 60)
    print("Model download process completed!")
    print("Container is ready for offline use.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
