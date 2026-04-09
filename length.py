def check_length(df, style_guide: dict) -> list:
    issues = []
    max_ratio = float(style_guide.get("max_length_ratio", 3.0))

    for idx, row in df.iterrows():
        src = str(row.get("source", "")).strip()
        tgt = str(row.get("target", "")).strip()
        if not src or not tgt:
            continue
        ratio = len(tgt) / max(len(src), 1)
        if ratio > max_ratio:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Length",
                "severity": "Minor",
                "message": f"Target ยาวกว่า source {ratio:.1f}× (เกิน {max_ratio}×)",
            })
    return issues
