# app.py
import pandas as pd
import streamlit as st
st.set_page_config(page_title="אישור קורסי ליבה – MVP", page_icon="🧪", layout="wide")

from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any

from schema import ensure_db_ready
from data_access import (
    fetch_faculties, fetch_core_areas, fetch_syllabi_df,
    insert_stat_rows, course_is_fresh
)
from utils.rtl import inject_rtl_css
from utils.export import export_faculty_packages

# MUST be first Streamlit call:

inject_rtl_css()

st.title("🧪 מערכת אישור קורסי ליבה – MVP")

# Init DB (DDL + seed) once per process
@st.cache_resource
def _boot():
    ensure_db_ready()
    return True
_boot()

# Load reference data
FACULTIES, FACULTY_LOOKUP = fetch_faculties()
CORE_AREAS = fetch_core_areas()
SYLLABI_INDEX = fetch_syllabi_df()

with st.expander("אודות המערכת (MVP)", expanded=False):
    st.markdown("""
    מטרת הכלי: לאסוף בקלות את נתוני המועמד/ת, לבחור סילבוסים לקורסי הליבה, למפות אותם לדרישות,
    לבצע בדיקת תוקף, ולהפיק חבילות לכל פקולטה (XLSX + קבצים נלווים + טיוטת מייל).
    **פרטיות**: איסוף הנתונים האישיים הוא לצורך יצוא הטפסים בלבד. הסטטיסטיקות בתחתית אנונימיות.
    """)

# שלב 1 – מידע אישי כללי
st.header("שלב 1 – מידע אישי כללי")
col1, col2, col3 = st.columns(3)
with col1:
    full_name = st.text_input("שם מלא")
    id_or_passport = st.text_input("ת.ז/דרכון")
with col2:
    email = st.text_input("דוא\"ל")
    phone = st.text_input("טלפון")
with col3:
    consent_stats = st.checkbox("אני מסכים/ה לשימוש אנונימי לסטטיסטיקות מצטברות", value=True)

applicant = {
    "full_name": (full_name or "").strip(),
    "id_or_passport": (id_or_passport or "").strip(),
    "email": (email or "").strip(),
    "phone": (phone or "").strip(),
}

st.divider()

# שלב 2 – בחירת מוסד/שנה/קורסים + העלאת סילבוס מותאם אישית
st.header("שלב 2 – בחירת קורסי ליבה והוספת סילבוסים")
institutions = sorted(SYLLABI_INDEX["institution"].unique()) if not SYLLABI_INDEX.empty else []
inst = st.selectbox("בחר/י מוסד", options=["—"] + institutions)

selected_rows: List[Dict[str, Any]] = []
user_added_items: List[Dict[str, Any]] = []
uploaded_files_store: Dict[str, bytes] = {}

if inst != "—":
    years = sorted(SYLLABI_INDEX[SYLLABI_INDEX["institution"] == inst]["year"].unique(), reverse=True)
    year_sel = st.selectbox("בחר/י שנה", options=years)
    inst_df = SYLLABI_INDEX[(SYLLABI_INDEX["institution"] == inst) & (SYLLABI_INDEX["year"] == year_sel)]

    st.subheader("סילבוסים זמינים מהמוסד והשנה שנבחרו")
    st.dataframe(inst_df.drop(columns=["id"], errors="ignore"), use_container_width=True)

    choose = st.multiselect(
        "בחר/י קורסים להוספה",
        options=inst_df.index.tolist(),
        format_func=lambda idx: f"{inst_df.loc[idx, 'course_name']} ({inst_df.loc[idx, 'core_area']})",
    )
    for idx in choose:
        row = inst_df.loc[idx].to_dict()
        row.update({"grade": ""})
        selected_rows.append(row)

st.markdown("**או הוספה ידנית של סילבוס/ים ממוסדות אחרים**")
with st.popover("הוספת סילבוס ידני"):
    colu1, colu2 = st.columns(2)
    with colu1:
        u_institution = st.text_input("מוסד")
        u_course_name = st.text_input("שם הקורס")
        u_core_area = st.selectbox("תחום ליבה", CORE_AREAS)
    with colu2:
        u_year = st.number_input("שנת לימוד", min_value=2000, max_value=datetime.now().year, value=datetime.now().year)
        u_course_code = st.text_input("מס' קורס (אופציונלי)")
        u_grade = st.text_input("ציון (אם יש)")
    uf = st.file_uploader("העלאת סילבוס (PDF)", type=["pdf"], accept_multiple_files=False)
    if st.button("הוסף/י לרשימה"):
        item = {
            "institution": (u_institution or "").strip() or "—",
            "year": int(u_year),
            "course_code": (u_course_code or "").strip(),
            "course_name": (u_course_name or "").strip(),
            "core_area": u_core_area,
            "grade": (u_grade or "").strip(),
        }
        if uf is not None:
            key = f"user_pdf_{uf.name}_{datetime.now().timestamp()}"
            uploaded_files_store[key] = uf.getvalue()
            item["uploaded_file_key"] = key
        user_added_items.append(item)
        st.success("נוסף לרשימה הזמנית למטה. סגרו את ה-popover כדי לראות.")

# מאחדים בחירות ממדד הסילבוסים + העלאות ידניות
all_selections = selected_rows + user_added_items

if all_selections:
    st.subheader("רשימת הקורסים שנבחרו")
    editable_df = pd.DataFrame(all_selections)
    view_cols = [c for c in ["institution","year","course_code","course_name","core_area","grade","file_url","uploaded_file_key"] if c in editable_df.columns]
    if view_cols:
        editable_df = editable_df[view_cols]
    editable_df = st.data_editor(
        editable_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "institution": st.column_config.TextColumn("מוסד לימוד"),
            "year": st.column_config.NumberColumn("שנה"),
            "course_code": st.column_config.TextColumn("מס' קורס"),
            "course_name": st.column_config.TextColumn("שם הקורס"),
            "core_area": st.column_config.SelectboxColumn("תחום ליבה", options=CORE_AREAS),
            "grade": st.column_config.TextColumn("ציון"),
            "file_url": st.column_config.TextColumn("קישור לסילבוס"),
            "uploaded_file_key": st.column_config.TextColumn("מפתח קובץ (זמני)"),
        },
        key="editable_df",
    )
    selections = editable_df.to_dict(orient="records")
else:
    selections = []

st.divider()

# שלב 3 – העלאת גיליונות ציונים (אופציונלי)
st.header("שלב 3 – הוספת גיליון ציונים (אופציונלי)")
transcript = st.file_uploader("העלאת קובץ PDF של גיליון ציונים", type=["pdf"])
if transcript is not None:
    uploaded_files_store["transcript_pdf"] = transcript.getvalue()

st.divider()

# שלב 4 – בחירת פקולטות יעד + ולידציה של התיישנות
st.header("שלב 4 – בחירת פקולטות ובדיקת תוקף")
cols = st.columns(3)
chosen_faculties: List[str] = []
for i, f in enumerate(FACULTIES):
    with cols[i % 3]:
        if st.checkbox(f["name"], value=False):
            chosen_faculties.append(f["id"])

if selections and chosen_faculties:
    st.subheader("בדיקת התיישנות הקורסים לפי כללי כל פקולטה")
    val_tabs = st.tabs([FACULTY_LOOKUP[fid]["name"] for fid in chosen_faculties])
    for tab, fid in zip(val_tabs, chosen_faculties):
        with tab:
            rows = []
            for s in selections:
                y = int(s.get("year", 0) or 0)
                rows.append({
                    "מוסד": s.get("institution", ""),
                    "שנה": s.get("year", ""),
                    "שם הקורס": s.get("course_name", ""),
                    "תחום ליבה": s.get("core_area", ""),
                    "בתוקף?": "כן" if course_is_fresh(y, fid) else "לא",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

st.divider()

# שלב 5 – סקירה ויצוא
st.header("שלב 5 – סקירה ויצוא חבילות")
ready_to_export = (
    bool(applicant.get("full_name")) and
    bool(applicant.get("id_or_passport")) and
    bool(applicant.get("email")) and
    selections and
    chosen_faculties
)
if ready_to_export:
    if st.button("יצירת ZIP לכל הפקולטות שנבחרו"):
        mem_zip = export_faculty_packages(applicant, selections, chosen_faculties, uploaded_files_store, FACULTY_LOOKUP)
        st.download_button("הורדת הקובץ (ZIP)", data=mem_zip, file_name="core_courses_packages.zip", mime="application/zip")
        st.success("נוצרו חבילות ההגשה + טיוטות מייל. ניתן להוריד כעת.")
else:
    st.info("יש למלא פרטים אישיים בסיסיים, לבחור לפחות קורס אחד ולסמן פקולטה אחת לפחות.")

st.divider()

# שלב 6 – סטטיסטיקות (אנונימיות)
st.header("סטטיסטיקות (אנונימי)")
if consent_stats and selections:
    rows_to_insert = [(s.get("institution", "—"), int(s.get("year", 0) or 0), s.get("core_area", "—")) for s in selections]
    from data_access import insert_stat_rows  # lazy import to avoid circulars
    insert_stat_rows(rows_to_insert)

try:
    from data_access import fetch_stats_agg_df
    agg = fetch_stats_agg_df()
    st.dataframe(agg, use_container_width=True) if not agg.empty else st.write("טרם נאספו נתונים להצגה.")
except Exception as e:
    st.warning(f"לא ניתן להציג סטטיסטיקות כרגע: {e}")

st.caption("\nמבנה מודולרי: DB מאוחסן בקבצים נפרדים, הקוד קריא וקל לתחזוקה.")
