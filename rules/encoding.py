def check_encoding(df, style_guide: dict) -> list:
    issues = []
    encoding = style_guide.get("encoding", "UTF-8")

    for idx, row in df.iterrows():
        tgt = str(row.get("target", ""))
        src = str(row.get("source", ""))
        if not tgt:
            continue

        # Check encoding compatibility
        if encoding == "TIS-620":
            try:
                tgt.encode("tis-620")
            except (UnicodeEncodeError, LookupError):
                issues.append({
                    "row": idx, "source": src, "target": tgt,
                    "rule": "Font/Encoding",
                    "severity": "Critical",
                    "message": f"มีอักขระที่ไม่รองรับใน {encoding}",
                })

        # Check for common garbled Thai (replacement chars or control chars)
        if "\ufffd" in tgt:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Font/Encoding",
                "severity": "Critical",
                "message": "พบ replacement character (ข้อความเสียหาย)",
            })

        # Check for zero-width chars that cause font rendering issues
        zw_chars = ["\u200b", "\u200c", "\u200d", "\ufeff"]
        found_zw = [hex(ord(c)) for c in tgt if c in zw_chars]
        if found_zw:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Font/Encoding",
                "severity": "Minor",
                "message": f"พบ zero-width character: {', '.join(found_zw)}",
            })

        # Check double spaces
        if "  " in tgt:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Font/Encoding",
                "severity": "Minor",
                "message": "พบช่องว่างซ้ำ (double space)",
            })

    return issues
