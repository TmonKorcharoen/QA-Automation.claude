import streamlit as st
import pandas as pd
from pathlib import Path

from readers.excel_reader import read_excel
from readers.xliff_reader import read_xliff
from readers.tmx_reader import read_tmx
from readers.glossary_reader import read_glossary_file
from readers.column_detector import detect_columns, apply_column_map
from rules.placeholder import check_placeholders
from rules.glossary import check_glossary
from rules.missing import check_missing
from rules.numbers import check_numbers
from rules.spelling import check_spelling
from rules.encoding import check_encoding
from rules.style_guide import check_style_guide, get_default_punct_rules
from rules.length import check_length
from exporters.export import export_excel, export_csv

st.set_page_config(page_title="Translation QA Tool", page_icon="🔍", layout="wide")
st.markdown("""
<style>
div[data-testid="stMetric"] { background:#f8f9fa; border-radius:10px; padding:10px 16px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────
if "glossary" not in st.session_state:
    st.session_state.glossary = [
        {"source": "Submit",    "target": "ส่ง",      "severity": "Critical"},
        {"source": "Cancel",    "target": "ยกเลิก",   "severity": "Major"},
        {"source": "Dashboard", "target": "แดชบอร์ด", "severity": "Minor"},
    ]
if "style_guide" not in st.session_state:
    st.session_state.style_guide = {
        "punctuation_rules": get_default_punct_rules(),
        "encoding":          "UTF-8",
        "thai_font":         "Sarabun",
        "tone":              "ทางการ",
        "max_length_ratio":  3.0,
    }
if "results"     not in st.session_state: st.session_state.results     = []
if "raw_df"      not in st.session_state: st.session_state.raw_df      = None
if "col_mapping" not in st.session_state: st.session_state.col_mapping = {}

# ── Header ───────────────────────────────────────────────────────────
st.title("🔍 Translation QA Tool")
st.caption("รองรับ .xlsx · .xliff · .tmx | ตรวจสอบคุณภาพงานแปลอัตโนมัติ")
st.divider()

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

        # ── Column picker (shown after upload) ───────────────────────
        if uploaded:
            st.success(f"✅ {uploaded.name}")
            ext = Path(uploaded.name).suffix.lower()

            # Load raw df only once per file
            if (st.session_state.raw_df is None or
                    st.session_state.get("last_file") != uploaded.name):
                with st.spinner("กำลังอ่านไฟล์..."):
                    if ext == ".xlsx":
                        raw_df, auto_map = read_excel(uploaded)
                    elif ext in (".xliff", ".xlf"):
                        raw_df, auto_map = read_xliff(uploaded)
                    elif ext == ".tmx":
                        raw_df, auto_map = read_tmx(uploaded)
                    else:
                        st.error("ไม่รองรับประเภทไฟล์นี้")
                        st.stop()
                st.session_state.raw_df      = raw_df
                st.session_state.col_mapping = auto_map
                st.session_state.last_file   = uploaded.name

            raw_df  = st.session_state.raw_df
            mapping = st.session_state.col_mapping

            if raw_df is not None and not raw_df.empty:
                all_cols = list(raw_df.columns)

                st.subheader("คอลัมน์")
                st.caption(f"ตรวจพบโดย: **{mapping.get('method','—')}**")

                # Score bar per column
                scores = mapping.get("all_scores", {})
                if scores:
                    score_df = pd.DataFrame([
                        {"คอลัมน์": c,
                         "Thai ratio": f"{v*100:.0f}%",
                         "ภาษา": "Thai" if v>0.5 else ("English" if v<0.1 else "Mixed")}
                        for c, v in scores.items()
                    ])
                    st.dataframe(score_df, hide_index=True, use_container_width=True)

                auto_src = mapping.get("source_col") or all_cols[0]
                auto_tgt = mapping.get("target_col") or (all_cols[1] if len(all_cols)>1 else all_cols[0])

                sel_src = st.selectbox(
                    "คอลัมน์ต้นฉบับ (Source)",
                    all_cols,
                    index=all_cols.index(auto_src) if auto_src in all_cols else 0,
                )
                sel_tgt = st.selectbox(
                    "คอลัมน์บทแปล (Target)",
                    all_cols,
                    index=all_cols.index(auto_tgt) if auto_tgt in all_cols else min(1, len(all_cols)-1),
                )

        st.subheader("QA Rules")
        rule_missing     = st.toggle("Missing translation",        value=True)
        rule_placeholder = st.toggle("Placeholder  {x} %s <tag>", value=True)
        rule_numbers     = st.toggle("ตัวเลข / ข้อมูลเฉพาะ",      value=True)
        rule_glossary    = st.toggle("Glossary",                   value=True)
        rule_spelling    = st.toggle("Spelling",                   value=True)
        rule_encoding    = st.toggle("Font & Encoding",            value=True)
        rule_style       = st.toggle("Style guide",                value=True)
        rule_length      = st.toggle("Length check",               value=False)

        st.subheader("ระดับความรุนแรง")
        st.markdown("""
- 🔴 **Critical** — ห้ามผ่านเด็ดขาด
- 🟠 **Major** — ต้องแก้ไขก่อน deliver
- 🟡 **Minor** — ควรแก้ไข
- 🟢 **Pass** — ผ่าน
        """)
        run = st.button("▶ รัน QA", type="primary", use_container_width=True)

    # ── Right panel ──────────────────────────────────────────────────
    with col_right:
        if run and uploaded and st.session_state.raw_df is not None:
            raw_df = st.session_state.raw_df

            # Build working df from user-selected columns
            df = pd.DataFrame({
                "source": raw_df[sel_src].astype(str).fillna(""),
                "target": raw_df[sel_tgt].astype(str).fillna(""),
            })

            st.info(
                f"ใช้คอลัมน์: **{sel_src}** (ต้นฉบับ)  →  **{sel_tgt}** (บทแปล) "
                f"| {len(df)} segments"
            )

            all_issues = []
            with st.spinner("กำลังตรวจสอบ..."):
                if rule_missing:     all_issues += check_missing(df)
                if rule_placeholder: all_issues += check_placeholders(df)
                if rule_numbers:     all_issues += check_numbers(df)
                if rule_glossary:    all_issues += check_glossary(df, st.session_state.glossary)
                if rule_spelling:    all_issues += check_spelling(df)
                if rule_encoding:    all_issues += check_encoding(df, st.session_state.style_guide)
                if rule_style:       all_issues += check_style_guide(df, st.session_state.style_guide)
                if rule_length:      all_issues += check_length(df, st.session_state.style_guide)

            flagged = {i["row"] for i in all_issues}
            for idx in range(len(df)):
                if idx not in flagged:
                    all_issues.append({
                        "row": idx,
                        "source": df.iloc[idx]["source"],
                        "target": df.iloc[idx]["target"],
                        "rule": "—", "severity": "Pass", "message": "—",
                    })

            all_issues.sort(key=lambda x: (
                {"Critical":0,"Major":1,"Minor":2,"Pass":3}.get(x["severity"],4),
                x["row"]
            ))
            st.session_state.results = all_issues

        if st.session_state.results:
            results = st.session_state.results
            total   = len(results)
            n_pass  = sum(1 for r in results if r["severity"]=="Pass")
            n_minor = sum(1 for r in results if r["severity"]=="Minor")
            n_major = sum(1 for r in results if r["severity"]=="Major")
            n_crit  = sum(1 for r in results if r["severity"]=="Critical")

            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("ทั้งหมด",      total)
            c2.metric("✅ Pass",      n_pass)
            c3.metric("🟡 Minor",     n_minor)
            c4.metric("🟠 Major",     n_major)
            c5.metric("🔴 Critical",  n_crit)
            st.divider()

            filter_sev = st.multiselect(
                "กรองตามระดับ",
                ["Critical","Major","Minor","Pass"],
                default=["Critical","Major","Minor"],
            )
            filtered = [r for r in results if r["severity"] in filter_sev]

            ex1, ex2, _ = st.columns([1,1,5])
            df_out = pd.DataFrame(filtered)
            with ex1:
                st.download_button("⬇ Export Excel", data=export_excel(df_out),
                    file_name="qa_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with ex2:
                st.download_button("⬇ Export CSV", data=export_csv(df_out),
                    file_name="qa_results.csv", mime="text/csv")

            SEV = {"Critical":"🔴","Major":"🟠","Minor":"🟡","Pass":"🟢"}
            for r in filtered:
                with st.container():
                    c = st.columns([0.4,2,2,1.2,1.4,2.8])
                    c[0].write(f"**{r['row']+1}**")
                    c[1].write(r.get("source",""))
                    c[2].write(r.get("target","") or "_ว่าง_")
                    c[3].write(r.get("rule",""))
                    c[4].markdown(f"{SEV.get(r['severity'],'')} **{r['severity']}**")
                    c[5].write(r.get("message",""))
                st.markdown("<hr style='margin:4px 0;border-color:#eee;'>", unsafe_allow_html=True)

        elif not uploaded:
            st.info("อัปโหลดไฟล์งานแปลทางซ้าย แล้วกด **รัน QA** เพื่อเริ่มตรวจสอบ")

# ════════════════════════════════════════════════════════════════════
# TAB 2 — GLOSSARY
# ════════════════════════════════════════════════════════════════════
with tab_glossary:
    st.subheader("จัดการ Glossary")
    st.caption("รองรับ .xlsx · .xliff · .tmx · .csv")

    gfile = st.file_uploader(
        "Import Glossary",
        type=["xlsx","xls","csv","xliff","xlf","tmx"],
        key="gfile",
    )
    if gfile:
        entries, err = read_glossary_file(gfile)
        if err:       st.error(err)
        elif entries:
            st.session_state.glossary = entries
            st.success(f"นำเข้า {len(entries)} รายการจาก {gfile.name} สำเร็จ")
        else:         st.warning("ไม่พบรายการใน Glossary")

    edited = st.data_editor(
        pd.DataFrame(st.session_state.glossary),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "source":   st.column_config.TextColumn("Source term"),
            "target":   st.column_config.TextColumn("Target term"),
            "severity": st.column_config.SelectboxColumn(
                "ระดับ", options=["Critical","Major","Minor"]),
        },
        key="glossary_editor",
    )
    if st.button("💾 บันทึก Glossary"):
        st.session_state.glossary = edited.to_dict("records")
        st.success("บันทึกแล้ว")

    if st.session_state.glossary:
        gcsv = pd.DataFrame(st.session_state.glossary).to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ Export Glossary CSV", data=gcsv,
                           file_name="glossary.csv", mime="text/csv")

# ════════════════════════════════════════════════════════════════════
# TAB 3 — STYLE GUIDE
# ════════════════════════════════════════════════════════════════════
with tab_style:
    st.subheader("Style Guide Settings")
    sg = st.session_state.style_guide

    st.markdown("### เครื่องหมายวรรคตอน (Punctuation)")
    st.caption("เลือกว่าจะ อนุญาต หรือ ห้าม แต่ละเครื่องหมายในคำแปลภาษาไทย")

    punct_rules  = sg.get("punctuation_rules", get_default_punct_rules())
    updated_rules = []
    h1,h2,h3 = st.columns([2.5,1.2,1.5])
    h1.markdown("**เครื่องหมาย**")
    h2.markdown("**อนุญาต**")
    h3.markdown("**ระดับถ้าผิด**")

    for i, rule in enumerate(punct_rules):
        c1,c2,c3 = st.columns([2.5,1.2,1.5])
        label = c1.text_input(f"l{i}", value=rule["label"],
                              label_visibility="collapsed", key=f"plabel_{i}")
        allow = c2.checkbox("", value=rule["allow"], key=f"pallow_{i}")
        opts  = ["Minor","Major","Critical"]
        sev   = c3.selectbox("", opts,
                             index=opts.index(rule.get("severity","Minor")),
                             label_visibility="collapsed", key=f"psev_{i}")
        updated_rules.append({"char":rule["char"],"label":label,"allow":allow,"severity":sev})

    with st.expander("➕ เพิ่มเครื่องหมายใหม่"):
        nc1,nc2,nc3,nc4 = st.columns([1,2,1,1.5])
        new_char  = nc1.text_input("ตัวอักษร", placeholder="เช่น /", key="new_char")
        new_label = nc2.text_input("ชื่อ", placeholder="เช่น ทับ (/)", key="new_label")
        new_allow = nc3.checkbox("อนุญาต", value=False, key="new_allow")
        new_sev   = nc4.selectbox("ระดับ", ["Minor","Major","Critical"], key="new_sev")
        if st.button("เพิ่ม") and new_char:
            updated_rules.append({"char":new_char,"label":new_label or new_char,
                                   "allow":new_allow,"severity":new_sev})
            st.success(f"เพิ่ม '{new_char}' แล้ว")

    st.divider()
    ca, cb = st.columns(2)
    with ca:
        st.markdown("### Tone / ระดับภาษา")
        sg["tone"] = st.selectbox("ระดับภาษา",
            ["ทางการ","กึ่งทางการ","ไม่เป็นทางการ"],
            index=["ทางการ","กึ่งทางการ","ไม่เป็นทางการ"].index(sg.get("tone","ทางการ")))
    with cb:
        st.markdown("### Font & Encoding")
        sg["encoding"] = st.selectbox("Encoding",
            ["UTF-8","TIS-620","UTF-16"],
            index=["UTF-8","TIS-620","UTF-16"].index(sg.get("encoding","UTF-8")))
        sg["thai_font"] = st.text_input("Thai font", value=sg.get("thai_font","Sarabun"))

    st.markdown("### Length Check")
    sg["max_length_ratio"] = st.slider(
        "อัตราส่วนความยาว target/source สูงสุด",
        min_value=1.0, max_value=10.0,
        value=float(sg.get("max_length_ratio",3.0)), step=0.5)

    if st.button("💾 บันทึก Style Guide", type="primary"):
        sg["punctuation_rules"] = updated_rules
        st.session_state.style_guide = sg
        st.success("บันทึก Style Guide แล้ว")

# ════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ════════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("ประวัติการตรวจสอบ")
    if st.session_state.results:
        results = st.session_state.results
        n_crit  = sum(1 for r in results if r["severity"]=="Critical")
        n_major = sum(1 for r in results if r["severity"]=="Major")
        n_minor = sum(1 for r in results if r["severity"]=="Minor")
        n_pass  = sum(1 for r in results if r["severity"]=="Pass")
        st.info(f"รัน QA ล่าสุด: {len(results)} segments — "
                f"🔴 Critical {n_crit} | 🟠 Major {n_major} | 🟡 Minor {n_minor} | 🟢 Pass {n_pass}")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.info("ยังไม่มีประวัติ — รัน QA ก่อนในแท็บ 'QA Check'")
