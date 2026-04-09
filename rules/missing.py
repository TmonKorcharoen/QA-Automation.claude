def check_missing(df) -> list:
    issues = []
    for idx, row in df.iterrows():
        src = str(row.get("source", "")).strip()
        tgt = str(row.get("target", "")).strip()
        if src and not tgt:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Missing",
                "severity": "Major",
                "message": "ไม่มีคำแปล",
            })
    return issues
