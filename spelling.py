# Thai common misspellings dictionary
# format: { wrong: correct }
THAI_MISSPELLINGS = {
    "คลิ๊ก":    "คลิก",
    "แชร์":     "แชร์",        # already correct — placeholder example
    "โปรแกรมม์": "โปรแกรม",
    "อีเมล์":   "อีเมล",
    "อินเตอร์เน็ต": "อินเทอร์เน็ต",
    "เว็บไซท์": "เว็บไซต์",
    "แอพพลิเคชั่น": "แอปพลิเคชัน",
    "แอพ":      "แอป",
    "อัพโหลด":  "อัปโหลด",
    "อัพเดต":   "อัปเดต",
    "ดาวน์โหลด์": "ดาวน์โหลด",
    "เซิฟเวอร์": "เซิร์ฟเวอร์",
    "ไฟล์ล์":   "ไฟล์",
    "พาสเวิร์ด": "รหัสผ่าน",
    "ล็อคอิน":  "เข้าสู่ระบบ",
    "แฮ็ค":     "แฮก",
    "บัค":      "บัก",
}

def check_spelling(df) -> list:
    issues = []
    for idx, row in df.iterrows():
        tgt = str(row.get("target", ""))
        src = str(row.get("source", ""))
        for wrong, correct in THAI_MISSPELLINGS.items():
            if wrong in tgt and wrong != correct:
                issues.append({
                    "row": idx, "source": src, "target": tgt,
                    "rule": "Spelling",
                    "severity": "Minor",
                    "message": f'"{wrong}" ควรสะกด "{correct}"',
                })
    return issues
