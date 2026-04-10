"""
Style guide rule.
style_guide dict keys:
  punctuation_rules : list of dicts  [{char, label, allow, severity}, ...]
  tone              : str  ทางการ | กึ่งทางการ | ไม่เป็นทางการ
"""

DEFAULT_PUNCT_RULES = [
    {"char": "!",   "label": "เครื่องหมายอัศเจรีย์ (!)",   "allow": False, "severity": "Minor"},
    {"char": "...", "label": "จุดไข่ปลา (...)",              "allow": True,  "severity": "Minor"},
    {"char": "?",   "label": "เครื่องหมายคำถาม (?)",        "allow": True,  "severity": "Minor"},
    {"char": ";",   "label": "เซมิโคลอน (;)",               "allow": False, "severity": "Minor"},
    {"char": ":",   "label": "โคลอน (:)",                   "allow": True,  "severity": "Minor"},
    {"char": "-",   "label": "ยัติภังค์ (-)",               "allow": True,  "severity": "Minor"},
    {"char": '"',   "label": 'อัญประกาศคู่ (")',            "allow": True,  "severity": "Minor"},
    {"char": "'",   "label": "อัญประกาศเดี่ยว (')",         "allow": False, "severity": "Minor"},
    {"char": "()",  "label": "วงเล็บ ()",                   "allow": True,  "severity": "Minor"},
]

INFORMAL_WORDS = ["นะ", "เลย", "จ้า", "จ้าา", "อ่ะ", "อ่ะนะ", "โอเค", "โอเคนะ", "ครับผม"]


def get_default_punct_rules():
    return [r.copy() for r in DEFAULT_PUNCT_RULES]


def check_style_guide(df, style_guide: dict) -> list:
    issues = []
    punct_rules = style_guide.get("punctuation_rules", get_default_punct_rules())
    tone = style_guide.get("tone", "ทางการ")

    for idx, row in df.iterrows():
        tgt = str(row.get("target", ""))
        src = str(row.get("source", ""))
        if not tgt:
            continue

        for rule in punct_rules:
            char  = rule.get("char", "")
            allow = rule.get("allow", True)
            label = rule.get("label", char)
            sev   = rule.get("severity", "Minor")
            if not allow and char and char in tgt:
                issues.append({
                    "row": idx, "source": src, "target": tgt,
                    "rule": "Style guide",
                    "severity": sev,
                    "message": f"Style guide: ไม่อนุญาตใช้ {label}",
                })

        if tone == "ทางการ":
            found = [w for w in INFORMAL_WORDS if w in tgt]
            if found:
                issues.append({
                    "row": idx, "source": src, "target": tgt,
                    "rule": "Style guide",
                    "severity": "Minor",
                    "message": f"Tone: พบคำไม่เป็นทางการ — {', '.join(found)}",
                })

    return issues
