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
import os, io, re
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
TEXT_SUFFIXES = {".txt", ".csv", ".tsv", ".log", ".jsonl"}
ENCODING_TRIALS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")  # tweak to taste
MAX_BYTES       = 40 * 1024 * 1024      # 40 MB safety net


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
st_mask_char        = "*"
st_number_of_chars  = 15
st_encrypt_key      = "WmZq4t7w!z%C&F)J"


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
# ── Sidebar: Allow / Deny lists ────────────────────────────────────────

with st.sidebar.expander("Allowlists & Denylists", expanded=True):
    allow_raw = st_tags(
        label="Allowlist - never treat these as PII",
        text="Type word and press ↩︎",
        key="batch_allow_tags"          # ← UNIQUE KEY  (important!)
    ) or []                       # ← always a list, even if None

    deny_raw = st_tags(
        label="Denylist - always treat these as PII",
        text="Type word and press ↩︎",
        key="batch_deny_tags"           # ← UNIQUE KEY
    ) or []
    
    # These lines force the widgets to stay visible
    _ = allow_raw
    _ = deny_raw

    # Optional visual feedback
    if allow_raw:
        st.caption(f"Current allowlist: {', '.join(allow_raw)}")
    if deny_raw:
        st.caption(f"Current denylist: {', '.join(deny_raw)}")
        
    allow_list = list(w.strip() for w in allow_raw if w.strip())
    deny_list  = list(w.strip() for w in deny_raw  if w.strip())



# --- Let the user choose the entity list once ---
with st.sidebar.expander("Choose entities to look for", expanded=False):
    # build the choices lazily (after model-selection but before run)
    available_ents = get_supported_entities(*analyzer_params)
    st_entities = st.multiselect(
        "Which entities to look for?",
        options=available_ents,
        default=list(available_ents),
        key="batch_entities"        # explicit key is good practice
    )


########  Initialize debug log ##########
if "_debug_text" not in st.session_state:
    st.session_state._debug_text = ""
    

def log(msg: str):
    """Append a message to the in-memory debug log."""
    st.session_state._debug_text += msg
###########################################



# # ── SIDEBAR (optional clear-log button) ──────────
# if st.sidebar.button("🧹 Clear debug log"):
#     st.session_state._debug_text = ""










# ---------------------------------------------------------------------------
# ────────────────────────────── MAIN AREA ──────────────────────────────────
# ---------------------------------------------------------------------------
st.title("📂 Batch Anonymization")

analyzer_load_state = st.info("Starting Presidio batch analyzer...")

analyzer_load_state.empty()

# ----- File uploader ------
# keep a version counter in session_state
if "file_key_version" not in st.session_state:
    st.session_state.file_key_version = 0

def _clear_files():
    """Callback: wipe the current uploader and its files."""
    st.session_state.file_key_version += 1          # → new key → fresh widget
    # nothing else to reset; when the widget disappears its value is dropped

uploader_key = f"batch_files_{st.session_state.file_key_version}"

uploaded_files = st.file_uploader(
    "Select one or more files",
    type=["txt", "csv", "tsv", "docx", "xlsx", "xls", "log", "jsonl"],
    accept_multiple_files=True,
    key=uploader_key,
)

cols = st.columns([1, 0.09])
with cols[1]:
#     # 🗑 Unicode U+1F5D1 (Trash Can) – pick any icon you like
    st.button("🗑", on_click=_clear_files, help="Remove all selected files")
# -------------------------


# uploaded_files = st.file_uploader(
#     "Select one or more files",
#     type=["txt", "csv", "tsv", "docx"],
#     accept_multiple_files=True,
# )
run_btn = st.button("🚀 Anonymize")




# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
MARKER_TOKEN = "§§§"          # any string that will *never* be produced by Presidio
def _escape_markers(txt: str) -> str:
    return txt.replace("<<<sheet:", f"{MARKER_TOKEN}sheet:")
def _unescape_markers(txt: str) -> str:
    return txt.replace(f"{MARKER_TOKEN}sheet:", "<<<sheet:")

def _clean_for_flair(txt: str) -> str:
    """
    Remove control chars and normalise whitespace so that every token Flair
    creates is guaranteed to be found back inside the string.
    """
    # 1⃣ Strip NULs and other C0 controls except \n \t
    txt = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", txt)

    # 2⃣ Convert tabs + CR-LF combos to single spaces / newlines
    txt = txt.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")

    # 3⃣ Collapse runs of whitespace to a single space (keeps \n)
    txt = re.sub(r"[ \u00a0]+", " ", txt)          # nbsp too
    txt = re.sub(r"\n{3,}", "\n\n", txt)           # no >2 blank lines

    return txt.strip()

def text_to_excel(text: str, path: Path):
    """
    Rebuild an Excel workbook from the flattened string we produced in
    file_to_text().  •Each <<<sheet:name>>> marker starts a new sheet.
    Cells are reconstructed via pandas.read_csv().
    """
    # ➊ split *including* sheet markers
    parts = re.split(r"\n?<<<sheet:(.+?)>>>\n?", text)
    # parts = ["", sheet1, csv1, sheet2, csv2, …]

    if len(parts) < 3:                     # no sheet markers ⇒ nothing to save
        pd.read_csv(io.StringIO(text)).to_excel(path, index=False)
        return
        #raise ValueError("No sheet data found – cannot rebuild Excel file")


    wb = pd.ExcelWriter(path, engine="openpyxl")

    # ➋ iterate over pairs (sheet, csv)
    for i in range(1, len(parts), 2):
        sheet_name = parts[i][:31] or f"Sheet{i//2+1}"
        csv_block  = parts[i + 1].strip()

        if not csv_block:                  # skip completely empty sheets
            continue

        df = pd.read_csv(io.StringIO(csv_block))
        df.to_excel(wb, sheet_name=sheet_name, index=False)

    wb.close()

    # ➌ Make sure we wrote at least one visible sheet
    if not Path(path).stat().st_size:
        # The file is 0 B ↦ nothing was written (all sheets empty → wb.close() removed them)
        raise ValueError("Workbook ended up with no visible sheets")


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
        log(f"❌ {msg}\n")
        raise ValueError(msg)

    # 1. .docx -----------------------------------------------------------------
    if suffix == ".docx" or suffix == ".doc":
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
            log(f"❌ {msg}\n")
            raise ValueError(msg) from exc

    # 2. .xlsx / .xls --------------------------------------------------
    if suffix in {".xlsx", ".xls"}:
        try:
            # read all sheets into a dict[ sheet-name → DataFrame ]
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, engine=None)
            if not sheets:                       # empty workbook
                raise ValueError(f"{name}: workbook has no sheets")
        except Exception as exc:
            msg = f"{name}: cannot read – {exc}"
            log(f"❌ {msg}\n")
            raise ValueError(msg) from exc

        # Flatten every sheet into CSV-ish lines; keep sheet name as a header
        parts: list[str] = []
        for sheet_name, df in sheets.items():
            parts.append(f"<<<sheet:{sheet_name}>>>")
            parts.append(df.to_csv(index=False, lineterminator="\n"))
        return "\n".join(parts)



    # 3. Plain-text family -----------------------------------------------------
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
        log(f"❌ {msg}\n")
        raise UnicodeDecodeError(f"{name}: could not decode - tried {tried}")


    # 4. Fallback --------------------------------------------------------------
    msg = f"{name}: unsupported file type ({suffix or 'no suffix'})"
    log(f"❌ {msg}\n")
    raise ValueError(msg)




#### Starting Analyzer Engine #####
analyzer_load_state = st.info("Starting Presidio analyzer...")
analyzer = analyzer_engine(*analyzer_params)
analyzer_load_state.empty()



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
    
    # Number of files
    total = len(uploaded_files)
    prog = st.progress(0.0, text="Starting…")


    for idx, uf in enumerate(uploaded_files, start=1):
        log(f"▶ {uf.name} ({uf.size/1e6:.1f} MB) → reading…\n")
        
        # File to text
        st_text = file_to_text(uf)
        st_text  = _escape_markers(st_text)
        
        if st_text is None:
            continue  # failure already logged
        
        log(f"✔ {uf.name} – read {len(st_text)/1e3:.1f} kB\n")
        
        # Clean only if we are using a Flair model
        text_for_nlp = _clean_for_flair(st_text) if st_model_package.lower() == "flair" else st_text

        # ---------- ANALYZE ----------
        st_analyze_results = analyze(
            *analyzer_params,
            text=text_for_nlp,
            entities=st_entities,
            language="en",
            score_threshold=st_threshold,
            return_decision_process=False,
            allow_list=allow_list,
            deny_list=deny_list,
        )

        # ---------- ANONYMIZE ----------
        if st_operator not in ("highlight", "synthesize"):
            st_anonymize_results = anonymize(
                text=text_for_nlp,
                operator=st_operator,
                mask_char=st_mask_char,
                number_of_chars=st_number_of_chars,
                encrypt_key=st_encrypt_key,
                analyze_results=st_analyze_results,
            )
        else:
            raise ValueError(f"Operator {st_operator} not supported for batch anonymization.")


        clean_text = _unescape_markers(st_anonymize_results.text)

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
        elif uf.name.endswith((".xlsx", ".xls")):
            # ——— DEBUG TRACE ————————————————————————————————
            log("• first 120 chars BEFORE rebuild:\n"
                f"{clean_text[:120]!r}\n\n")
            # ————————————————————————————————————————————————
            try:
                text_to_excel(clean_text, out_path.with_suffix(".xlsx"))
            except ValueError as exc:
                log(f"⚠️  {uf.name}: {exc} – keeping original file\n")
                out_path.write_bytes(uf.getvalue())
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
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
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
    
    with st.expander("📝 Log", expanded=False):
        st.text(st.session_state.get("_debug_text", ""))