def check_glossary(df, glossary: list) -> list:
    issues = []
    for idx, row in df.iterrows():
        src = str(row.get("source", ""))
        tgt = str(row.get("target", ""))
        for entry in glossary:
            term_src = str(entry.get("source", ""))
            term_tgt = str(entry.get("target", ""))
            severity = entry.get("severity", "Major")
            if not term_src:
                continue
            if term_src.lower() in src.lower():
                if term_tgt not in tgt:
                    issues.append({
                        "row": idx, "source": src, "target": tgt,
                        "rule": "Glossary",
                        "severity": severity,
                        "message": f'"{term_src}" ควรแปลว่า "{term_tgt}"',
                    })
    return issues
