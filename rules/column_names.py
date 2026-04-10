"""
Column name checker.
Detects:
1. English column headers that should be in Thai (or vice-versa) per project convention.
2. Column names that look like they may be mislabelled (e.g. Thai text in an 'English' column).
3. Inconsistent naming within the same file (mix of EN/TH header styles).
"""
import re
import unicodedata

THAI_RANGE = re.compile(r"[\u0E00-\u0E7F]")
ENGLISH_WORD = re.compile(r"[A-Za-z]{2,}")

# Expected EN-only column names (source) — any Thai characters here = likely wrong
EN_COLUMN_HINTS = ["source", "src", "english", "en", "original", "source text"]
# Expected TH-only column names (target)
TH_COLUMN_HINTS = ["target", "tgt", "thai", "th", "translation", "คำแปล", "ต้นฉบับ"]


def has_thai(text: str) -> bool:
    return bool(THAI_RANGE.search(text))

def has_english(text: str) -> bool:
    return bool(ENGLISH_WORD.search(text))

def thai_ratio(text: str) -> float:
    if not text:
        return 0.0
    thai_chars = sum(1 for c in text if "\u0E00" <= c <= "\u0E7F")
    return thai_chars / len(text)

def english_ratio(text: str) -> float:
    if not text:
        return 0.0
    en_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    return en_chars / len(text)


def check_column_names(df) -> list:
    """
    Check that source column contains mostly English and target column contains
    Thai content, flag rows where content seems swapped or wrong.
    Returns list of issue dicts.
    """
    issues = []
    columns = list(df.columns)

    # ── 1. Column header style consistency ─────────────────────────────
    header_has_thai = [has_thai(c) for c in columns]
    header_has_en   = [has_english(c) for c in columns]

    if any(header_has_thai) and any(header_has_en):
        thai_hdrs = [c for c, t in zip(columns, header_has_thai) if t]
        en_hdrs   = [c for c, t in zip(columns, header_has_en) if t]
        issues.append({
            "row": -1,
            "source": ", ".join(en_hdrs),
            "target": ", ".join(thai_hdrs),
            "rule": "Column names",
            "severity": "Minor",
            "message": (
                f"ชื่อคอลัมน์ผสมภาษาไทย/อังกฤษ: "
                f"EN → {', '.join(en_hdrs)} | TH → {', '.join(thai_hdrs)}"
            ),
        })

    # ── 2. Source column content — should be mostly English ────────────
    src_col = "source"
    tgt_col = "target"
    if src_col not in df.columns or tgt_col not in df.columns:
        return issues

    for idx, row in df.iterrows():
        src = str(row.get(src_col, "")).strip()
        tgt = str(row.get(tgt_col, "")).strip()

        if not src or not tgt:
            continue

        src_thai_r = thai_ratio(src)
        tgt_en_r   = english_ratio(tgt)
        src_en_r   = english_ratio(src)
        tgt_thai_r = thai_ratio(tgt)

        # Source looks like Thai (>50% Thai chars) — columns may be swapped
        if src_thai_r > 0.5 and tgt_en_r > 0.5:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Column names",
                "severity": "Major",
                "message": "คอลัมน์อาจสลับกัน: source ดูเหมือนภาษาไทย, target ดูเหมือนภาษาอังกฤษ",
            })
            continue

        # Source contains heavy Thai mixed with expected EN — flag as mixed
        if src_thai_r > 0.3 and src_en_r > 0.3:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Column names",
                "severity": "Minor",
                "message": f"Source มีภาษาไทยปนอยู่ ({src_thai_r*100:.0f}% Thai chars)",
            })

        # Target is all-English when it should contain Thai translation
        if tgt_thai_r == 0 and tgt_en_r > 0.7 and len(tgt) > 3:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Column names",
                "severity": "Minor",
                "message": "Target ดูเหมือนเป็นภาษาอังกฤษทั้งหมด — อาจยังไม่ได้แปล",
            })

    return issues


def detect_column_map(df) -> dict:
    """
    Returns best-guess column mapping: {source_col, target_col, extra_cols}.
    Useful for files where column names are non-standard.
    """
    columns = list(df.columns)
    src_col = None
    tgt_col = None

    # First try name matching
    for c in columns:
        cl = c.lower().strip()
        if cl in EN_COLUMN_HINTS and src_col is None:
            src_col = c
        if cl in TH_COLUMN_HINTS and tgt_col is None:
            tgt_col = c

    # Fallback: sample content to detect language
    if src_col is None or tgt_col is None:
        for c in columns:
            sample = " ".join(str(v) for v in df[c].dropna().head(5))
            if src_col is None and english_ratio(sample) > 0.5:
                src_col = c
            elif tgt_col is None and thai_ratio(sample) > 0.3:
                tgt_col = c

    extra = [c for c in columns if c not in (src_col, tgt_col)]
    return {"source_col": src_col, "target_col": tgt_col, "extra_cols": extra}
