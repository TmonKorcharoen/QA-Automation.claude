def check_style_guide(df, style_guide: dict) -> list:
    issues = []
    allow_exclamation = style_guide.get("exclamation_mark", False)
    allow_ellipsis    = style_guide.get("ellipsis", True)
    tone              = style_guide.get("tone", "ทางการ")

    # Informal markers to flag in formal tone
    informal_words = ["นะ", "เลย", "ครับผม", "จ้า", "จ้าา", "อ่ะ", "อ่ะนะ", "โอเค", "โอเคนะ"]
    formal_words   = ["กรุณา", "โปรด", "ท่าน"]

    for idx, row in df.iterrows():
        tgt = str(row.get("target", ""))
        src = str(row.get("source", ""))
        if not tgt:
            continue

        # Exclamation mark
        if not allow_exclamation and "!" in tgt:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Style guide",
                "severity": "Minor",
                "message": "Style guide: ไม่อนุญาตใช้เครื่องหมาย !",
            })

        # Ellipsis
        if not allow_ellipsis and "..." in tgt:
            issues.append({
                "row": idx, "source": src, "target": tgt,
                "rule": "Style guide",
                "severity": "Minor",
                "message": "Style guide: ไม่อนุญาตใช้ ...",
            })

        # Tone check
        if tone == "ทางการ":
            found = [w for w in informal_words if w in tgt]
            if found:
                issues.append({
                    "row": idx, "source": src, "target": tgt,
                    "rule": "Style guide",
                    "severity": "Minor",
                    "message": f"Tone: พบคำไม่เป็นทางการ — {', '.join(found)}",
                })

    return issues
