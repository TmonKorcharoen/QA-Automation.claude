import streamlit as st
import pandas as pd
import json
import io
from pathlib import Path

from readers.excel_reader import read_excel
from readers.xliff_reader import read_xliff
from readers.tmx_reader import read_tmx
from rules.placeholder import check_placeholders
from rules.glossary import check_glossary
from rules.missing import check_missing
from rules.numbers import check_numbers
from rules.spelling import check_spelling
from rules.encoding import check_encoding
from rules.style_guide import check_style_guide
from rules.length import check_length
from exporters.export import export_excel, export_csv

st.set_page_config(
    page_title="Translation QA Tool",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
    .badge-critical { background:#FCEBEB; color:#A32D2D; padding:2px 8px; border-radius:6px; font-size:12px; font-weight:600; }
    .badge-major    { background:#FAECE7; color:#993C1D; padding:2px 8px; border-radius:6px; font-size:12px; font-weight:600; }
    .badge-minor    { background:#FAEEDA; color:#854F0B; padding:2px 8px; border-radius:6px; font-size:12px; font-weight:600; }
    .badge-pass     { background:#EAF3DE; color:#3B6D11; padding:2px 8px; border-radius:6px; font-size:12px; font-weight:600; }
    .stat-box { background:#f8f9fa; border-radius:10px; padding:14px 18px; text-align:center; }
    .stat-num { font-size:28px; font-weight:700; }
    .stat-label { font-size:12px; color:#888; margin-top:2px; }
    div[data-testid="stMetric"] { background:#f8f9fa; border-radius:10px; padding:10px 16px; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ──────────────────────────────────────────────
if "glossary" not in st.session_state:
    st.session_state.glossary = [
        {"source": "Submit",    "target": "ส่ง",       "severity": "Critical"},
        {"source": "Cancel",    "target": "ยกเลิก",    "severity": "Major"},
        {"source": "Dashboard", "target": "แดชบอร์ด",  "severity": "Minor"},
    ]
if "style_guide" not in st.session_state:
    st.session_state.style_guide = {
        "exclamation_mark": False,
        "ellipsis": True,
        "encoding": "UTF-8",
        "thai_font": "Sarabun",
        "tone": "ทางการ",
        "max_length_ratio": 3.0,
    }
if "results" not in st.session_state:
    st.session_state.results = []

# ── Header ──────────────────────────────────────────────────────────
st.title("🔍 Translation QA Tool")
st.caption("รองรับ .xlsx · .xliff · .tmx | ตรวจสอบคุณภาพงานแปลอัตโนมัติ")
st.divider()

# ── Tabs ─────────────────────────────────────────────────────────────
tab_qa, tab_glossary, tab_style, tab_history = st.tabs(
    ["QA Check", "Glossary", "Style Guide", "History"]
)

# ════════════════════════════════════════════════════════════════════
# TAB 1 — QA CHECK
# ════════════════════════════════════════════════════════════════════
with tab_qa:
    col_left, col_right = st.columns([1, 3], gap="large")

    with col_left:
        st.subheader("อัปโหลดไฟล์")
        uploaded = st.file_uploader(
            "เลือกไฟล์งานแปล",
            type=["xlsx", "xliff", "tmx"],
            help="รองรับ .xlsx, .xliff, .tmx",
        )
        if uploaded:
            st.success(f"✅ {uploaded.name}")

        st.subheader("QA Rules")
        rule_placeholder  = st.toggle("Placeholder  {x} %s <tag>", value=True)
        rule_glossary     = st.toggle("Glossary",                   value=True)
        rule_missing      = st.toggle("Missing translation",        value=True)
        rule_numbers      = st.toggle("ตัวเลข / ข้อมูลเฉพาะ",      value=True)
        rule_spelling     = st.toggle("Spelling",                   value=True)
        rule_encoding     = st.toggle("Font & Encoding",            value=True)
        rule_style        = st.toggle("Style guide",                value=True)
        rule_length       = st.toggle("Length check",               value=False)

        st.subheader("ระดับความรุนแรง")
        st.markdown("""
- 🔴 **Critical** — ห้ามผ่านเด็ดขาด
- 🟠 **Major** — ต้องแก้ไขก่อน deliver
- 🟡 **Minor** — ควรแก้ไข
- 🟢 **Pass** — ผ่าน
        """)

        run = st.button("▶ รัน QA", type="primary", use_container_width=True)

    with col_right:
        if run and uploaded:
            # Read file
            ext = Path(uploaded.name).suffix.lower()
            with st.spinner("กำลังอ่านไฟล์..."):
                if ext == ".xlsx":
                    df = read_excel(uploaded)
                elif ext == ".xliff":
                    df = read_xliff(uploaded)
                elif ext == ".tmx":
                    df = read_tmx(uploaded)
                else:
                    st.error("ไม่รองรับประเภทไฟล์นี้")
                    st.stop()

            if df is None or df.empty:
                st.warning("ไม่พบข้อมูลในไฟล์ กรุณาตรวจสอบโครงสร้างคอลัมน์ (source, target)")
                st.stop()

            # Run rules
            all_issues = []
            with st.spinner("กำลังตรวจสอบ..."):
                if rule_missing:
                    all_issues += check_missing(df)
                if rule_placeholder:
                    all_issues += check_placeholders(df)
                if rule_numbers:
                    all_issues += check_numbers(df)
                if rule_glossary:
                    all_issues += check_glossary(df, st.session_state.glossary)
                if rule_spelling:
                    all_issues += check_spelling(df)
                if rule_encoding:
                    all_issues += check_encoding(df, st.session_state.style_guide)
                if rule_style:
                    all_issues += check_style_guide(df, st.session_state.style_guide)
                if rule_length:
                    all_issues += check_length(df, st.session_state.style_guide)

            # Mark pass rows
            flagged_rows = {i["row"] for i in all_issues}
            for idx in range(len(df)):
                if idx not in flagged_rows:
                    all_issues.append({
                        "row": idx,
                        "source": df.iloc[idx].get("source", ""),
                        "target": df.iloc[idx].get("target", ""),
                        "rule": "—",
                        "severity": "Pass",
                        "message": "—",
                    })

            all_issues.sort(key=lambda x: (
                {"Critical": 0, "Major": 1, "Minor": 2, "Pass": 3}.get(x["severity"], 4),
                x["row"]
            ))
            st.session_state.results = all_issues

        if st.session_state.results:
            results = st.session_state.results
            total    = len(results)
            n_pass   = sum(1 for r in results if r["severity"] == "Pass")
            n_minor  = sum(1 for r in results if r["severity"] == "Minor")
            n_major  = sum(1 for r in results if r["severity"] == "Major")
            n_crit   = sum(1 for r in results if r["severity"] == "Critical")

            # Stats
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("ทั้งหมด",   total)
            c2.metric("✅ Pass",   n_pass)
            c3.metric("🟡 Minor",  n_minor)
            c4.metric("🟠 Major",  n_major)
            c5.metric("🔴 Critical", n_crit)

            st.divider()

            # Filter
            filter_sev = st.multiselect(
                "กรองตามระดับ",
                ["Critical", "Major", "Minor", "Pass"],
                default=["Critical", "Major", "Minor"],
            )
            filtered = [r for r in results if r["severity"] in filter_sev]

            # Export
            ex1, ex2, _ = st.columns([1, 1, 5])
            df_out = pd.DataFrame(filtered)
            with ex1:
                st.download_button(
                    "⬇ Export Excel",
                    data=export_excel(df_out),
                    file_name="qa_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with ex2:
                st.download_button(
                    "⬇ Export CSV",
                    data=export_csv(df_out),
                    file_name="qa_results.csv",
                    mime="text/csv",
                )

            # Table
            SEV_COLOR = {
                "Critical": "🔴",
                "Major":    "🟠",
                "Minor":    "🟡",
                "Pass":     "🟢",
            }
            for r in filtered:
                icon = SEV_COLOR.get(r["severity"], "")
                sev  = r["severity"]
                with st.container():
                    cols = st.columns([0.4, 2, 2, 1.2, 1.5, 2.5])
                    cols[0].write(f"**{r['row']+1}**")
                    cols[1].write(r.get("source", ""))
                    cols[2].write(r.get("target", "") or "_ว่าง_")
                    cols[3].write(r.get("rule", ""))
                    cols[4].markdown(f"{icon} **{sev}**")
                    cols[5].write(r.get("message", ""))
                st.markdown("<hr style='margin:4px 0; border-color:#eee;'>", unsafe_allow_html=True)

        elif not uploaded:
            st.info("อัปโหลดไฟล์งานแปลทางซ้าย แล้วกด **รัน QA** เพื่อเริ่มตรวจสอบ")

# ════════════════════════════════════════════════════════════════════
# TAB 2 — GLOSSARY
# ════════════════════════════════════════════════════════════════════
with tab_glossary:
    st.subheader("จัดการ Glossary")
    st.caption("คำศัพท์เหล่านี้จะถูกนำไปใช้ใน QA rule 'Glossary' อัตโนมัติ")

    # Import CSV
    gfile = st.file_uploader("Import Glossary (.csv)", type=["csv"], key="gcsv")
    if gfile:
        gdf = pd.read_csv(gfile)
        if {"source", "target"}.issubset(gdf.columns):
            if "severity" not in gdf.columns:
                gdf["severity"] = "Major"
            st.session_state.glossary = gdf[["source", "target", "severity"]].to_dict("records")
            st.success(f"นำเข้า {len(st.session_state.glossary)} รายการสำเร็จ")
        else:
            st.error("CSV ต้องมีคอลัมน์ 'source' และ 'target'")

    # Table
    gdf_display = pd.DataFrame(st.session_state.glossary)
    edited = st.data_editor(
        gdf_display,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "source":   st.column_config.TextColumn("Source term"),
            "target":   st.column_config.TextColumn("Target term"),
            "severity": st.column_config.SelectboxColumn(
                "ระดับ", options=["Critical", "Major", "Minor"]
            ),
        },
        key="glossary_editor",
    )
    if st.button("💾 บันทึก Glossary"):
        st.session_state.glossary = edited.to_dict("records")
        st.success("บันทึกแล้ว")

    # Export
    if st.session_state.glossary:
        gcsv = pd.DataFrame(st.session_state.glossary).to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Export Glossary CSV", data=gcsv, file_name="glossary.csv", mime="text/csv")

# ════════════════════════════════════════════════════════════════════
# TAB 3 — STYLE GUIDE
# ════════════════════════════════════════════════════════════════════
with tab_style:
    st.subheader("Style Guide Settings")
    sg = st.session_state.style_guide

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Punctuation**")
        sg["exclamation_mark"] = st.toggle("อนุญาต ! ในภาษาไทย", value=sg["exclamation_mark"])
        sg["ellipsis"]         = st.toggle("อนุญาต ... ในภาษาไทย", value=sg["ellipsis"])

        st.markdown("**Tone / ระดับภาษา**")
        sg["tone"] = st.selectbox("ระดับภาษา", ["ทางการ", "กึ่งทางการ", "ไม่เป็นทางการ"],
                                  index=["ทางการ", "กึ่งทางการ", "ไม่เป็นทางการ"].index(sg["tone"]))

    with col_b:
        st.markdown("**Font & Encoding**")
        sg["encoding"]   = st.selectbox("Encoding", ["UTF-8", "TIS-620", "UTF-16"],
                                        index=["UTF-8", "TIS-620", "UTF-16"].index(sg["encoding"]))
        sg["thai_font"]  = st.text_input("Thai font (ชื่อ font ที่กำหนด)", value=sg["thai_font"])

        st.markdown("**Length Check**")
        sg["max_length_ratio"] = st.slider(
            "อัตราส่วนความยาว target/source สูงสุด",
            min_value=1.0, max_value=10.0, value=float(sg["max_length_ratio"]), step=0.5
        )

    if st.button("💾 บันทึก Style Guide"):
        st.session_state.style_guide = sg
        st.success("บันทึก Style Guide แล้ว")

# ════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ════════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("ประวัติการตรวจสอบ")
    if st.session_state.results:
        results = st.session_state.results
        n_crit  = sum(1 for r in results if r["severity"] == "Critical")
        n_major = sum(1 for r in results if r["severity"] == "Major")
        n_minor = sum(1 for r in results if r["severity"] == "Minor")
        n_pass  = sum(1 for r in results if r["severity"] == "Pass")
        st.info(f"รัน QA ล่าสุด: {len(results)} segments — Critical {n_crit} | Major {n_major} | Minor {n_minor} | Pass {n_pass}")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.info("ยังไม่มีประวัติการตรวจสอบ — รัน QA ก่อนในแท็บ 'QA Check'")
