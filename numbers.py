import re

# Patterns for numbers and special data
NUMBER_PAT   = re.compile(r"\b\d[\d,\.]*\b")
DATE_PAT     = re.compile(r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b")
CURRENCY_PAT = re.compile(r"[\$\€\£\฿]\s?\d[\d,\.]*|\d[\d,\.]*\s?(?:USD|EUR|THB|GBP|Bath|Baht)")
VERSION_PAT  = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b")
EMAIL_PAT    = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
URL_PAT      = re.compile(r"https?://\S+")

ALL_PATTERNS = [
    ("ตัวเลข",  NUMBER_PAT,   "Critical"),
    ("วันที่",  DATE_PAT,     "Critical"),
    ("สกุลเงิน", CURRENCY_PAT, "Critical"),
    ("Version", VERSION_PAT,  "Major"),
    ("Email",   EMAIL_PAT,    "Major"),
    ("URL",     URL_PAT,      "Major"),
]

def extract_all(text, pat):
    return set(pat.findall(text))

def check_numbers(df) -> list:
    issues = []
    for idx, row in df.iterrows():
        src = str(row.get("source", ""))
        tgt = str(row.get("target", ""))
        for label, pat, severity in ALL_PATTERNS:
            src_vals = extract_all(src, pat)
            tgt_vals = extract_all(tgt, pat)
            missing = src_vals - tgt_vals
            if missing:
                issues.append({
                    "row": idx, "source": src, "target": tgt,
                    "rule": f"ตัวเลข/{label}",
                    "severity": severity,
                    "message": f"{label} หายไป: {', '.join(sorted(missing))}",
                })
    return issues
