"""
Glossary reader — supports .xlsx, .csv, .xliff, .tmx
Returns list of dicts: [{source, target, severity}, ...]
"""
import pandas as pd
from pathlib import Path
from lxml import etree

POSSIBLE_SRC = ["source", "src", "Source", "SOURCE", "english", "English", "EN", "en", "term_source"]
POSSIBLE_TGT = ["target", "tgt", "Target", "TARGET", "thai", "Thai", "TH", "th", "term_target", "translation"]
POSSIBLE_SEV = ["severity", "Severity", "level", "Level", "ระดับ"]


def _infer_cols(df):
    cols = list(df.columns)
    src = next((c for c in POSSIBLE_SRC if c in cols), None)
    tgt = next((c for c in POSSIBLE_TGT if c in cols), None)
    sev = next((c for c in POSSIBLE_SEV if c in cols), None)

    # fallback positional
    if src is None and len(cols) >= 1:
        src = cols[0]
    if tgt is None and len(cols) >= 2:
        tgt = cols[1]
    if sev is None and len(cols) >= 3:
        sev = cols[2]

    return src, tgt, sev


def read_glossary_xlsx(file) -> list:
    df = pd.read_excel(file, dtype=str).fillna("")
    src, tgt, sev = _infer_cols(df)
    rows = []
    for _, row in df.iterrows():
        s = str(row.get(src, "")).strip()
        t = str(row.get(tgt, "")).strip()
        v = str(row.get(sev, "Major")).strip() if sev else "Major"
        if v not in ("Critical", "Major", "Minor"):
            v = "Major"
        if s:
            rows.append({"source": s, "target": t, "severity": v})
    return rows


def read_glossary_csv(file) -> list:
    df = pd.read_csv(file, dtype=str).fillna("")
    src, tgt, sev = _infer_cols(df)
    rows = []
    for _, row in df.iterrows():
        s = str(row.get(src, "")).strip()
        t = str(row.get(tgt, "")).strip()
        v = str(row.get(sev, "Major")).strip() if sev else "Major"
        if v not in ("Critical", "Major", "Minor"):
            v = "Major"
        if s:
            rows.append({"source": s, "target": t, "severity": v})
    return rows


def read_glossary_xliff(file) -> list:
    """Read XLIFF as glossary — each trans-unit becomes a term pair."""
    try:
        tree = etree.parse(file)
        root = tree.getroot()
        ns12 = {"x": "urn:oasis:names:tc:xliff:document:1.2"}
        rows = []

        # XLIFF 1.2
        for unit in root.findall(".//x:trans-unit", ns12):
            src_el = unit.find("x:source", ns12)
            tgt_el = unit.find("x:target", ns12)
            s = (src_el.text or "").strip() if src_el is not None else ""
            t = (tgt_el.text or "").strip() if tgt_el is not None else ""
            if s:
                rows.append({"source": s, "target": t, "severity": "Major"})

        if not rows:
            # XLIFF 2.x
            ns20 = "urn:oasis:names:tc:xliff:document:2.0"
            for unit in root.findall(f".//{{{ns20}}}unit"):
                src_el = unit.find(f".//{{{ns20}}}source")
                tgt_el = unit.find(f".//{{{ns20}}}target")
                s = (src_el.text or "").strip() if src_el is not None else ""
                t = (tgt_el.text or "").strip() if tgt_el is not None else ""
                if s:
                    rows.append({"source": s, "target": t, "severity": "Major"})

        return rows
    except Exception:
        return []


def read_glossary_tmx(file) -> list:
    """Read TMX as glossary — each TU becomes a term pair."""
    try:
        tree = etree.parse(file)
        root = tree.getroot()
        rows = []
        for tu in root.findall(".//tu"):
            tuvs = tu.findall("tuv")
            s, t = "", ""
            for i, tuv in enumerate(tuvs):
                seg = tuv.find("seg")
                text = (seg.text or "").strip() if seg is not None else ""
                if i == 0:
                    s = text
                else:
                    t = text
            if s:
                rows.append({"source": s, "target": t, "severity": "Major"})
        return rows
    except Exception:
        return []


def read_glossary_file(file) -> tuple[list, str]:
    """
    Auto-detect format and return (entries, error_message).
    entries = [] on failure, error_message = "" on success.
    """
    name = file.name if hasattr(file, "name") else str(file)
    ext = Path(name).suffix.lower()

    try:
        if ext in (".xlsx", ".xls"):
            return read_glossary_xlsx(file), ""
        elif ext == ".csv":
            return read_glossary_csv(file), ""
        elif ext in (".xliff", ".xlf"):
            return read_glossary_xliff(file), ""
        elif ext == ".tmx":
            return read_glossary_tmx(file), ""
        else:
            return [], f"ไม่รองรับไฟล์ประเภท {ext}"
    except Exception as e:
        return [], f"อ่านไฟล์ไม่ได้: {e}"
