"""
column_detector.py — smart source/target column detection
Handles files with many columns (ID, notes, translator, status, etc.)

Strategy (in order):
1. Header name matching  — known EN/TH keywords
2. Language + length scoring — Thai ratio + average text length
3. Positional fallback
"""
import re
import pandas as pd

THAI  = re.compile(r"[\u0E00-\u0E7F]")
LATIN = re.compile(r"[A-Za-z]")

SOURCE_NAMES = {
    "source","src","source text","original","english","en","eng",
    "ต้นฉบับ","ภาษาต้นฉบับ","ต้นทาง",
}
TARGET_NAMES = {
    "target","tgt","target text","translation","translated","thai","th","tha",
    "คำแปล","บทแปล","ภาษาแปล","แปล",
}


def _thai_ratio(series: pd.Series) -> float:
    sample = " ".join(str(v) for v in series.dropna().head(20))
    if not sample:
        return 0.0
    thai  = sum(1 for c in sample if THAI.match(c))
    latin = sum(1 for c in sample if LATIN.match(c))
    total = thai + latin
    return thai / total if total else 0.0


def _avg_len(series: pd.Series) -> float:
    vals = series.dropna().head(20)
    if len(vals) == 0:
        return 0.0
    return sum(len(str(v)) for v in vals) / len(vals)


def _is_natural_text(series: pd.Series) -> bool:
    """Exclude ID/number/short-code columns."""
    avg = _avg_len(series)
    if avg < 5:
        return False
    # Check if >70% values are purely numeric/code
    sample = series.dropna().head(10)
    code_like = sum(1 for v in sample if re.fullmatch(r"[A-Z0-9\-_]{1,10}", str(v).strip()))
    return (code_like / max(len(sample), 1)) < 0.7


def detect_columns(df: pd.DataFrame) -> dict:
    cols = list(df.columns)

    # Filter to natural-text columns only
    text_cols = [c for c in cols if _is_natural_text(df[c])]
    if not text_cols:
        text_cols = cols  # fallback: use all

    src_col = None
    tgt_col = None
    method  = "unknown"

    # ── Step 1: header name matching ────────────────────────────────
    for c in cols:
        norm = c.strip().lower()
        if norm in SOURCE_NAMES and src_col is None:
            src_col = c
        if norm in TARGET_NAMES and tgt_col is None:
            tgt_col = c
    if src_col and tgt_col:
        method = "header name"

    # ── Step 2: language + length scoring ───────────────────────────
    if not src_col or not tgt_col:
        scores = {}
        for c in text_cols:
            thai_r  = _thai_ratio(df[c])
            avg_l   = _avg_len(df[c])
            scores[c] = {"thai_ratio": thai_r, "avg_len": avg_l}

        # Sort candidates: source = low Thai ratio + long text
        # target = high Thai ratio + long text
        candidates = sorted(
            text_cols,
            key=lambda c: (scores[c]["thai_ratio"], -scores[c]["avg_len"])
        )

        if not src_col:
            for c in candidates:
                if c != tgt_col and scores[c]["avg_len"] >= 5:
                    src_col = c
                    break

        if not tgt_col:
            for c in reversed(candidates):
                if c != src_col and scores[c]["avg_len"] >= 3:
                    tgt_col = c
                    break

        method = "content language analysis"

    # ── Step 3: positional fallback ─────────────────────────────────
    if not src_col:
        src_col = text_cols[0] if text_cols else cols[0]
        method  = "positional fallback"
    if not tgt_col:
        remaining = [c for c in text_cols if c != src_col]
        tgt_col   = remaining[0] if remaining else (cols[1] if len(cols) > 1 else cols[0])
        method    = "positional fallback"

    def lang_label(col):
        if col is None: return "unknown"
        r = _thai_ratio(df[col])
        if r > 0.5:   return "Thai"
        if r < 0.1:   return "English / Other"
        return f"Mixed ({r*100:.0f}% Thai)"

    extra = [c for c in cols if c not in (src_col, tgt_col)]
    all_scores = {
        c: {"thai_ratio": round(_thai_ratio(df[c]), 3),
            "avg_len":    round(_avg_len(df[c]), 1),
            "is_text":    _is_natural_text(df[c])}
        for c in cols
    }

    return {
        "source_col":  src_col,
        "target_col":  tgt_col,
        "source_lang": lang_label(src_col),
        "target_lang": lang_label(tgt_col),
        "extra_cols":  extra,
        "method":      method,
        "all_scores":  all_scores,
    }


def apply_column_map(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    src = mapping.get("source_col")
    tgt = mapping.get("target_col")
    rename = {}
    if src and src != "source": rename[src] = "source"
    if tgt and tgt != "target": rename[tgt] = "target"
    df2   = df.rename(columns=rename)
    keep  = ["source","target"] + [c for c in df2.columns if c not in ("source","target")]
    return df2[[c for c in keep if c in df2.columns]]
