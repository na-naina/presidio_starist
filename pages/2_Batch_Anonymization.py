"""
📂 Batch Anonymization – multi‑file Presidio de‑identification
This Streamlit page lets the user pick **one or more files** (txt / csv / tsv / docx)
select exactly the same knobs that are available in the single‑file page,
then download all anonymized versions in a ZIP.
"""
from __future__ import annotations

import datetime as _dt
import logging
import dotenv
import os, io
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import streamlit as st
from streamlit_tags import st_tags

# To Read docx files
import docx as _docx
#from docx import Document
import docx2txt

from presidio_helpers import (
    get_supported_entities,
    analyze,
    anonymize,
    annotate,
    create_fake_data,
    analyzer_engine,
)


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
TEXT_SUFFIXES   = {".txt", ".csv", ".tsv", ".log", ".jsonl"}
ENCODING_TRIALS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")  # tweak to taste
MAX_BYTES       = 20 * 1024 * 1024      # 20 MB safety net


dotenv.load_dotenv()
logger = logging.getLogger("presidio-streamlit")

allow_other_models = os.getenv("ALLOW_OTHER_MODELS", False)

# ---------------------------------------------------------------------------
# ────────────────────────────── SIDEBAR UI ─────────────────────────────────
# ---------------------------------------------------------------------------
st.sidebar.header("Batch Anonymization - Presidio")

#######################################################################
# Model Selection
#######################################################################
model_help_text = """
    Select which Named Entity Recognition (NER) model to use for PII detection, in parallel to rule-based recognizers.
    Presidio supports multiple NER packages off-the-shelf, such as spaCy, Huggingface, Stanza and Flair.
    """
st_ta_key = st_ta_endpoint = ""

model_list = [
    "spaCy/en_core_web_lg",
    "flair/ner-english-large",
    "HuggingFace/obi/deid_roberta_i2b2",
    "HuggingFace/StanfordAIMI/stanford-deidentifier-base",
    "stanza/en",
    "Other",
]
if not allow_other_models:
    model_list.pop()
# Select model
st_model = st.sidebar.selectbox(
    "NER model package",
    model_list,
    index=1,
    help=model_help_text,
)



# Extract model package.
st_model_package = st_model.split("/")[0]

# Remove package prefix (if needed)
st_model = (
    st_model
    if st_model_package.lower() not in ("spacy", "stanza", "huggingface")
    else "/".join(st_model.split("/")[1:])
)

if st_model == "Other":
    st_model_package = st.sidebar.selectbox(
        "NER model OSS package", options=["spaCy", "stanza", "Flair", "HuggingFace"]
    )
    st_model = st.sidebar.text_input(f"NER model name", value="")


st.sidebar.warning("Note: Models might take some time to download. ")

analyzer_params = (st_model_package, st_model, st_ta_key, st_ta_endpoint)
logger.debug(f"analyzer_params: {analyzer_params}")
#######################################################################


st_operator = st.sidebar.selectbox(
    "De-identification approach",
    ["redact", "replace", "synthesize", "highlight", "mask", "hash", "encrypt"],
    index=1,
    help="""
    Select which manipulation to the text is requested after PII has been identified.\n
    - Redact: Completely remove the PII text\n
    - Replace: Replace the PII text with a constant, e.g. <PERSON>\n
    - Synthesize: Replace with fake values (requires an OpenAI key)\n
    - Highlight: Shows the original text with PII highlighted in colors\n
    - Mask: Replaces a requested number of characters with an asterisk (or other mask character)\n
    - Hash: Replaces with the hash of the PII string\n
    - Encrypt: Replaces with an AES encryption of the PII string, allowing the process to be reversed
         """,
)
st_mask_char = "*"
st_number_of_chars = 15
st_encrypt_key = "WmZq4t7w!z%C&F)J"

open_ai_params = None

logger.debug(f"st_operator: {st_operator}")


if st_operator == "mask":
    st_number_of_chars = st.sidebar.number_input(
        "number of chars", value=st_number_of_chars, min_value=0, max_value=100
    )
    st_mask_char = st.sidebar.text_input(
        "Mask character", value=st_mask_char, max_chars=1
    )
elif st_operator == "encrypt":
    st_encrypt_key = st.sidebar.text_input("AES key", value=st_encrypt_key)

st_threshold = st.sidebar.slider(
    label="Acceptance threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.35,
    help="Define the threshold for accepting a detection as PII. See more here: ",
)


# Allow and deny lists
st_deny_allow_expander = st.sidebar.expander(
    "Allowlists and denylists",
    expanded=False,
)

with st_deny_allow_expander:
    st_allow_list = st_tags(
        label="Add words to the allowlist", text="Enter word and press enter."
    )
    st.caption(
        "Allowlists contain words that are not considered PII, but are detected as such."
    )

    st_deny_list = st_tags(
        label="Add words to the denylist", text="Enter word and press enter."
    )
    st.caption(
        "Denylists contain words that are considered PII, but are not detected as such."
    )


# Initialize debug log ──────────────────────────────────────────────────────
# if "_debug_text" not in st.session_state:
#     st.session_state._debug_text = ""

# def log(msg: str):
#     st.session_state._debug_text = st.session_state.get("_debug_text", "") + msg
#     st.session_state._debug_log.text("📝 Debug log\n\n" + st.session_state._debug_text)

if "_debug_text" not in st.session_state:
    st.session_state._debug_text = ""
    

def log(msg: str):
    """Append a message to the in-memory debug log."""
    st.session_state._debug_text += msg


# ── SIDEBAR (optional clear-log button) ──────────────────────────────
if st.sidebar.button("🧹 Clear debug log"):
    st.session_state._debug_text = ""




# ---------------------------------------------------------------------------
# ────────────────────────────── MAIN AREA ──────────────────────────────────
# ---------------------------------------------------------------------------
st.title("📂 Batch Anonymization")

analyzer_load_state = st.info("Starting Presidio batch analyzer...")

analyzer_load_state.empty()


uploaded_files = st.file_uploader(
    "Select one or more files",
    type=["txt", "csv", "tsv", "docx"],
    accept_multiple_files=True,
)
run_btn = st.button("🚀 Anonymize")



# Helper ─────────────────────────────────────────────────────────────────────

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
TEXT_SUFFIXES = {".txt", ".csv", ".tsv", ".log", ".jsonl"}
ENCODING_TRIALS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")  # tweak to taste
MAX_BYTES = 20 * 1024 * 1024      # 20 MB safety net


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def file_to_text(upload, encoding: str | None = None) -> str:
    """
    Convert a Streamlit UploadedFile (or any file-like obj with .read/.getvalue)
    into **plain text**.

    Parameters
    ----------
    upload : streamlit.runtime.uploaded_file_manager.UploadedFile | BinaryIO
        The uploaded object.
    encoding : str | None
        Force a specific encoding for text files; None → try a fallback list.

    Raises
    ------
    ValueError : if the file type is not supported or required libs are missing
    UnicodeDecodeError : if none of the encodings work on a text file
    """


    # 0. Name / size checks
    name    = getattr(upload, "name", "stream")
    suffix  = (Path(name).suffix or "").lower()
    raw     = upload.getvalue() if hasattr(upload, "getvalue") else upload.read()

    if len(raw) > MAX_BYTES:
        msg = f"{name}: file is too large ({len(raw)/1e6:.1f} MB)"
        st.session_state._debug_log.write(f"❌ {msg}\n")
        raise ValueError(msg)


    # 1. Plain-text family -----------------------------------------------------
    if suffix in TEXT_SUFFIXES:
        trials = [encoding] if encoding else []   # user-override first
        trials += [enc for enc in ENCODING_TRIALS if enc != encoding]

        for enc in trials:
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        tried = ", ".join(trials)
        msg = f"{name}: could not decode – tried {tried}"
        st.session_state._debug_log.write(f"❌ {msg}\n")
        raise UnicodeDecodeError(f"{name}: could not decode - tried {tried}")


    # 2. .docx -----------------------------------------------------------------
    if suffix == ".docx":
        # Option A – high-fidelity paragraph+table text with python-docx
        try:
            doc = _docx.Document(io.BytesIO(raw))
            parts: list[str] = [p.text for p in doc.paragraphs]
            for tbl in doc.tables:                           # grab tables too
                for row in tbl.rows:
                    parts.extend(cell.text for cell in row.cells)
            # print documents for debugging, cosnidering that is streamlit
            #print("DOCX FUNTION: "+"\n".join(parts).strip(), file=sys.stdout)
            return "\n".join(parts).strip()

        except ModuleNotFoundError:
            pass  # fall through to docx2txt

        # Option B – “good enough” full-text with docx2txt
        try:
            return docx2txt.process(io.BytesIO(raw)).strip()
        except ModuleNotFoundError as exc:
            msg = (f"{name}: cannot read - neither `python-docx` nor `docx2txt` available")
            st.session_state._debug_log.write(f"❌ {msg}\n")
            raise ValueError(msg) from exc


    # 3. .xlsx / .xls (optional) ----------------------------------------------
    if suffix in {".xlsx", ".xls"}:
        try:
            df = pd.read_excel(io.BytesIO(raw), sheet_name=None)
            return "\n\n".join(df[s].to_csv(index=False) for s in df)
        except ModuleNotFoundError as exc:
            raise ValueError("`pandas` and `openpyxl` are required for Excel.") from exc


    # 4️⃣ Fallback --------------------------------------------------------------
    msg = f"{name}: unsupported file type ({suffix or 'no suffix'})"
    st.session_state._debug_log.write(f"❌ {msg}\n")
    raise ValueError(msg)








################################################################################
# Run button pressed ---------------------------------------------------------
################################################################################
if run_btn:
    if not uploaded_files:
        st.warning("Please choose at least one file first ⬆")
        st.stop()

    work_dir = Path(tempfile.mkdtemp())
    out_dir = work_dir / "anonymized"
    out_dir.mkdir(exist_ok=True)

    # Starting analyzer engine
    analyzer_load_state = st.info("Starting Presidio analyzer...")
    analyzer = analyzer_engine(*analyzer_params)
    analyzer_load_state.empty()
    
    # Number of files
    total = len(uploaded_files)
    prog = st.progress(0.0, text="Starting…")


    for idx, uf in enumerate(uploaded_files, start=1):
        log(f"▶ {uf.name} ({uf.size/1e6:.1f} MB) → reading…\n")
        
        # File to text
        st_text = file_to_text(uf)
        
        if st_text is None:
            continue  # failure already logged


        # THIS MAY NOT WORK AS EXPECTED IN THE BATCH MODE
        # Choose entities
        st_entities_expander = st.sidebar.expander("Choose entities to look for")
        st_entities = st_entities_expander.multiselect(
            label="Which entities to look for?",
            options=get_supported_entities(*analyzer_params),
            default=list(get_supported_entities(*analyzer_params)),
            help="Limit the list of PII entities detected. "
            "This list is dynamic and based on the NER model and registered recognizers. "
            "More information can be found here: https://microsoft.github.io/presidio/analyzer/adding_recognizers/",
        )

        # ---------- ANALYZE ----------
        st_analyze_results = analyze(
            *analyzer_params,
            text=st_text,
            entities=st_entities,
            language="en",
            score_threshold=st_threshold,
            return_decision_process=False,
            allow_list=st_allow_list,
            deny_list=st_deny_list,
        )

        # ---------- ANONYMIZE ----------
        if st_operator not in ("highlight", "synthesize"):
            st_anonymize_results = anonymize(
                text=st_text,
                operator=st_operator,
                mask_char=st_mask_char,
                number_of_chars=st_number_of_chars,
                encrypt_key=st_encrypt_key,
                analyze_results=st_analyze_results,
            )


        # write output
        out_path = out_dir / uf.name
        # Rewrite in the format of the original file
        if uf.name.endswith(".csv"):
            # Convert to DataFrame
            df = pd.DataFrame(st_anonymize_results.text)
            # Save as CSV
            out_path = out_path.with_suffix(".csv")
            df.to_csv(out_path, index=False)
        elif uf.name.endswith(".tsv"):
            # Convert to DataFrame
            df = pd.DataFrame(st_anonymize_results.text)
            # Save as TSV
            out_path = out_path.with_suffix(".tsv")
            df.to_csv(out_path, sep="\t", index=False)
        elif uf.name.endswith(".txt"):
            # Save as TXT
            out_path = out_path.with_suffix(".txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(st_anonymize_results.text)
        elif uf.name.endswith(".log"):
            # Save as LOG
            out_path = out_path.with_suffix(".log")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(st_anonymize_results.text)
        elif uf.name.endswith(".jsonl"):
            # Convert to DataFrame
            df = pd.DataFrame(st_anonymize_results.text)
            # Save as JSONL
            out_path = out_path.with_suffix(".jsonl")
            df.to_json(out_path, orient="records", lines=True)
        elif uf.name.endswith(".xlsx"):
            # Convert to DataFrame
            df = pd.DataFrame(st_anonymize_results.text)
            # Save as Excel
            out_path = out_path.with_suffix(".xlsx")
            df.to_excel(out_path, index=False)
        elif uf.name.endswith(".xls"):
            # Convert to DataFrame
            df = pd.DataFrame(st_anonymize_results.text)
            # Save as Excel
            out_path = out_path.with_suffix(".xls")
            df.to_excel(out_path, index=False)
        elif uf.name.endswith(".doc"):
            # Create a new Document
            doc = _docx.Document()
            # Add the anonymized text to the document
            doc.add_paragraph(st_anonymize_results.text)
            # Save the document
            out_path = out_path.with_suffix(".doc")
            doc.save(out_path)
        elif uf.name.endswith(".docx"):
            # Create a new Document
            doc = _docx.Document()
            # Add the anonymized text to the document
            doc.add_paragraph(st_anonymize_results.text)
            # Save the document
            out_path = out_path.with_suffix(".docx")
            doc.save(out_path)
        log(f"✔ {uf.name} – done\n")
        
        prog.progress(idx / total, text=f"{idx}/{total} done")


    #######################################################################
    # Bundle all anonymized files into an in-memory ZIP for user download
    #######################################################################
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in out_dir.iterdir():
            log(f"📦 Adding to ZIP: {p.name}\n")
            zf.write(p, arcname=p.name)
    buf.seek(0)

    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.success("Finished ✔ Files written next to the originals and bundled below.")
    st.download_button(
        "⬇ Download anonymized files (.zip)",
        data=buf,
        file_name=f"anonymized_{ts}.zip",
        mime="application/zip",
    )

    # remember temp dir → will be cleaned on session end
    st.session_state.setdefault("_tmp_dirs", []).append(work_dir)
    import atexit
    atexit.register(lambda: shutil.rmtree(work_dir, ignore_errors=True))
    
    with st.expander("📝 Debug log", expanded=False):
        st.text(st.session_state.get("_debug_text", ""))