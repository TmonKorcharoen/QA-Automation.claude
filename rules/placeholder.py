import re

PLACEHOLDER_PATTERNS = [
    r"\{[\w\d_]+\}",        # {name}, {count}
    r"%[sd\d]",             # %s, %d, %1
    r"<[^>]+>",             # <b>, <br/>
    r"\[\[[\w\d_]+\]\]",    # [[variable]]
    r"%%[\w\d_]+%%",        # %%VAR%%
]

def extract_placeholders(text: str) -> list:
    found = []
    for pat in PLACEHOLDER_PATTERNS:
        found += re.findall(pat, text)
    return found

def check_placeholders(df) -> list:
    issues = []
    for idx, row in df.iterrows():
        src = str(row.get("source", ""))
        tgt = str(row.get("target", ""))
        src_ph = extract_placeholders(src)
        tgt_ph = extract_placeholders(tgt)
        missing = [p for p in src_ph if p not in tgt_ph]
        extra   = [p for p in tgt_ph if p not in src_ph]
        if missing:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Placeholder",
                "severity": "Critical",
                "message": f"หาย: {', '.join(missing)}",
            })
        if extra:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Placeholder",
                "severity": "Major",
                "message": f"เกิน: {', '.join(extra)}",
            })
    return issues
