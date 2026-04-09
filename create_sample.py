import pandas as pd

data = {
    "source": [
        "Hello, {name}!",
        "Submit the form",
        "Total: $1,250.00",
        "Cancel",
        "COVID-19 report",
        "Click here to continue",
        "Welcome back!",
        "Save changes",
        "Delete account",
        "Version 2.5.1 released",
        "Contact us at support@example.com",
        "Visit https://example.com for more",
        "Processing...",
    ],
    "target": [
        "สวัสดี!",
        "",
        "รวม: 1250",
        "ยกเลิกการดำเนินการ",
        "รายงานโควิด19",
        "คลิ๊กที่นี่เพื่อดำเนินการต่อ",
        "ยินดีต้อนรับกลับมา!",
        "บันทึกการเปลี่ยนแปลง",
        "ลบบัญชี",
        "เวอร์ชัน released",
        "ติดต่อเราที่ support@example.com",
        "เยี่ยมชม https://example.com สำหรับข้อมูลเพิ่มเติม",
        "กำลังประมวลผล...",
    ]
}

df = pd.DataFrame(data)
df.to_excel("sample_translation.xlsx", index=False)
print("Created sample_translation.xlsx")
