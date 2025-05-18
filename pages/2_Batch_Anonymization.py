"""
📂 Batch Anonymization – multi‑file Presidio de‑identification
This Streamlit page lets the user pick **one or more files** (txt / csv / tsv / docx)
select exactly the same knobs that are available in the single‑file page,
then download all anonymized versions in a ZIP.
"""
from __future__ import annotations

import datetime as _dt
import io
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import streamlit as st

from presidio_helpers import (
    analyzer_engine,
    analyze,
    anonymize,
    create_fake_data,
    get_supported_entities,  # NEW – for the multiselect
)
from openai_fake_data_generator import OpenAIParams

# ---------------------------------------------------------------------------
# ────────────────────────────── SIDEBAR UI ─────────────────────────────────
# ---------------------------------------------------------------------------
st.sidebar.header("Batch anonymization settings")

# Re‑use model choice from the single‑file page (stored in session‑state)
model_pkg: str = st.session_state.get("st_model_package", "spaCy")
model_name: str = st.session_state.get("st_model", "en_core_web_lg")

op = st.sidebar.selectbox(
    "De‑identification operator",
    [
        "redact",
        "replace",
        "synthesize",
        "mask",
        "hash",
        "encrypt",
    ],
    index=1,
)
replace_tok = st.sidebar.text_input("Replacement token", "<ANON>")
mask_char = st.sidebar.text_input("Mask character", "*") if op == "mask" else None
mask_len = (
    st.sidebar.number_input("Mask length", 15, 0, 200) if op == "mask" else None
)
enc_key = st.sidebar.text_input("AES key", "WmZq4t7w!z%C&F)J") if op == "encrypt" else None
threshold = st.sidebar.slider("Acceptance threshold", 0.0, 1.0, 0.35)

# Entity picker (NEW – fixes NoneType bug)
try:
    supported_ents: List[str] = get_supported_entities(model_pkg, model_name, "", "")
except Exception:
    supported_ents = []

st_entities: List[str] = st.sidebar.multiselect(
    "Entities to look for (leave empty for ALL)",
    options=supported_ents,
    default=supported_ents,
)

# OpenAI synthesis parameters ------------------------------------------------
openai_params: Optional[OpenAIParams] = None
if op == "synthesize":

    def _collect_openai_params() -> OpenAIParams:
        api_type = st.sidebar.selectbox("OpenAI API type", ["openai", "azure"], 0)
        api_key = st.sidebar.text_input("OPENAI_KEY", type="password")
        model = st.sidebar.text_input("Model", "gpt-3.5-turbo-instruct")
        base = (
            st.sidebar.text_input("Azure endpoint") if api_type == "azure" else None
        )
        deployment = (
            st.sidebar.text_input("Deployment name") if api_type == "azure" else ""
        )
        version = (
            st.sidebar.text_input("API version", "2023-05-15")
            if api_type == "azure"
            else None
        )
        return OpenAIParams(
            openai_key=api_key,
            model=model,
            api_base=base,
            deployment_id=deployment,
            api_version=version,
            api_type=api_type,
        )

    openai_params = _collect_openai_params()

# ---------------------------------------------------------------------------
# ────────────────────────────── MAIN AREA ──────────────────────────────────
# ---------------------------------------------------------------------------
st.title("📂 Batch Anonymization")

uploaded_files = st.file_uploader(
    "Select one or more files",
    type=["txt", "csv", "tsv", "docx"],
    accept_multiple_files=True,
)
run_btn = st.button("🚀 Anonymize")

# Helper ─────────────────────────────────────────────────────────────────────

def file_to_text(uf: "UploadedFile") -> Optional[str]:
    """Read the contents of *uf* according to its suffix and return a str.
    Supports utf‑8 plain text and Word (.docx).
    Returns **None** if the file cannot be read.
    """
    name = uf.name
    suffix = Path(name).suffix.lower()
    try:
        if suffix in {".txt", ".csv", ".tsv"}:  # naive – all read as text
            return uf.getvalue().decode("utf-8", errors="ignore")
        elif suffix == ".docx":
            try:
                import docx2txt as _d2t

                # Write to a temp file because docx2txt works with paths
                with tempfile.NamedTemporaryFile(suffix=".docx") as tmp:
                    tmp.write(uf.getvalue())
                    tmp.flush()
                    return _d2t.process(tmp.name)
            except ImportError:
                try:
                    import docx as _docx

                    doc = _docx.Document(io.BytesIO(uf.getvalue()))
                    return "\n".join(p.text for p in doc.paragraphs)
                except ImportError:
                    raise ValueError(
                        "python‑docx/docx2txt not installed – cannot read .docx"
                    )
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    except Exception as ex:
        st.session_state._debug_log.write(f"❌ {name}: {ex}\n")
        return None

# Initialize debug log ──────────────────────────────────────────────────────
if "_debug_log" not in st.session_state:
    st.session_state._debug_log = st.empty()

def log(msg: str):
    st.session_state._debug_text = st.session_state.get("_debug_text", "") + msg
    st.session_state._debug_log.text("📝 Debug log\n\n" + st.session_state._debug_text)

# Run button pressed ---------------------------------------------------------
if run_btn:
    if not uploaded_files:
        st.warning("Please choose at least one file first ⬆")
        st.stop()

    work_dir = Path(tempfile.mkdtemp())
    out_dir = work_dir / "anonymized"
    out_dir.mkdir(exist_ok=True)

    eng = analyzer_engine(model_pkg, model_name, "", "")
    total = len(uploaded_files)
    prog = st.progress(0.0, text="Starting…")

    for idx, uf in enumerate(uploaded_files, start=1):
        log(f"▶ {uf.name} → reading…\n")
        txt = file_to_text(uf)
        if txt is None:
            continue  # failure already logged

        # ---------- ANALYZE ----------
        analyze_kwargs = dict(
            text=txt,
            language="en",
            score_threshold=threshold,
            return_decision_process=False,
        )
        if st_entities:  # only include key if we have a real iterable
            analyze_kwargs["entities"] = st_entities

        results = analyze(model_pkg, model_name, "", "", **analyze_kwargs)

        # ---------- ANONYMIZE ----------
        anon_kwargs = dict(
            text=txt,
            operator=op,
            analyze_results=results,
            mask_char=mask_char,
            number_of_chars=mask_len,
            encrypt_key=enc_key,
            replace_text=replace_tok,
        )
        # strip None entries (anonymize() doesn’t accept them)
        anon_kwargs = {k: v for k, v in anon_kwargs.items() if v is not None}

        try:
            if op == "synthesize":
                de_text = create_fake_data(txt, results, openai_params)
            else:
                de_text = anonymize(**anon_kwargs).text
        except TypeError as te:
            # Fallback for older presidio‑anonymizer signatures (no replace_text)
            if "replace_text" in str(te):
                anon_kwargs.pop("replace_text", None)
                de_text = anonymize(**anon_kwargs).text
            else:
                raise

        # write output
        out_path = out_dir / uf.name
        out_path.write_text(de_text, encoding="utf-8")
        log(f"✔ {uf.name} – done\n")
        prog.progress(idx / total, text=f"{idx}/{total} done")

    # Bundle ZIP -------------------------------------------------------------
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in out_dir.iterdir():
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
