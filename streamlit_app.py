"""
מערכת אישור קורסי ליבה – MVP ב‑Streamlit
=================================================

הערה: זהו MVP יחיד בקובץ אחד (streamlit_app.py) כדי שיהיה קל להרצה ב‑Streamlit Cloud.
בהמשך ניתן לפרק לקבצים (utils/, config/, templates/), לחבר DB, OAuth לדוא"ל, ועוד.

איך להריץ מקומית
-----------------
1) התקנה: pip install -r requirements.txt
2) הפעלה:  streamlit run streamlit_app.py

requirements.txt המינימלי:
---------------------------
streamlit==1.37.1
pandas==2.2.2
openpyxl==3.1.5
python-dateutil==2.9.0.post0

פרטי MVP
---------
- איסוף מידע אישי כללי למועמד/ת (ללא מידע מזהה לשימוש סטטיסטי)
- בחירת מוסד/שנה וקורסי ליבה מתוך אינדקס סילבוסים לדוגמה + העלאת סילבוס מותאם אישית
- העלאת גיליונות ציונים (אופציונלי)
- מיפוי קורסים → דרישות ליבה (Core Areas)
- ולידציה של "התיישנות" קורסים (10 שנים ברירת מחדל, 11 לב"ג)
- סקירה סופית, יצוא חבילות XLSX + ZIP לפי פקולטה
- יצירת טיוטת מייל פר‑פקולטה (העתק/הדבק; שליחה אמיתית תתווסף בהמשך)
- לוח סטטיסטיקות מצטברות (אנונימי) בזמן ריצה

קובץ זה מכיל גם "דאטה לדוגמה" (FAKE DATA) כדי לראות את הזרימה.

"""

import io
import os
import zipfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

# ==========================
# FAKE CONFIG/DATA EXAMPLES
# ==========================

# פקולטות רלוונטיות + הגדרות אימות (שדות לטבלאות, מייל יעד, שנות תוקף)
FACULTIES = [
    {
        "id": "huji",
        "name": "האוניברסיטה העברית – פקולטה לרפואה",
        "email": "corecourses@huji.ac.il",
        "max_course_age_years": 10,
        "table_fields": [
            {"id": "applicant_full_name", "label": "שם מלא"},
            {"id": "id_or_passport", "label": "ת.ז/דרכון"},
            {"id": "institution", "label": "מוסד לימוד"},
            {"id": "year", "label": "שנה"},
            {"id": "course_name", "label": "שם הקורס"},
            {"id": "core_area", "label": "תחום ליבה"},
            {"id": "grade", "label": "ציון"},
        ],
    },
    {
        "id": "bgu",
        "name": "אוניברסיטת בן‑גוריון – פקולטה למדעי הבריאות",
        "email": "corecourses@bgu.ac.il",
        "max_course_age_years": 11,  # חריג: 11 שנים
        "table_fields": [
            {"id": "applicant_full_name", "label": "שם מלא"},
            {"id": "id_or_passport", "label": "ת.ז/דרכון"},
            {"id": "institution", "label": "מוסד לימוד"},
            {"id": "year", "label": "שנה"},
            {"id": "course_code", "label": "מס' קורס"},
            {"id": "course_name", "label": "שם הקורס"},
            {"id": "core_area", "label": "תחום ליבה"},
            {"id": "grade", "label": "ציון"},
        ],
    },
    {
        "id": "tau",
        "name": "אוניברסיטת תל‑אביב – הפקולטה לרפואה",
        "email": "corecourses@tau.ac.il",
        "max_course_age_years": 10,
        "table_fields": [
            {"id": "applicant_full_name", "label": "שם מלא"},
            {"id": "id_or_passport", "label": "ת.ז/דרכון"},
            {"id": "institution", "label": "מוסד לימוד"},
            {"id": "year", "label": "שנה"},
            {"id": "course_name", "label": "שם הקורס"},
            {"id": "core_area", "label": "תחום ליבה"},
            {"id": "grade", "label": "ציון"},
        ],
    },
]

FACULTY_LOOKUP = {f["id"]: f for f in FACULTIES}

# 7 תחומי ליבה לדוגמה – ניתן להתאים במציאות
CORE_AREAS = [
    "כימיה כללית", "כימיה אורגנית", "ביוכימיה",
    "ביולוגיה של התא", "מיקרוביולוגיה", "פיזיקה", "סטטיסטיקה"
]

# אינדקס סילבוסים לדוגמה – בעתיד יגיע מקבצים/DB; כאן רק הדגמה.
# במציאות ה-"file_url" יהיה קישור לקובץ סילבוס (PDF) המאוחסן ב‑Cloud (או קובץ שהועלה).
SYLLABI_INDEX = pd.DataFrame([
    {"institution": "מכללת הדסה", "year": 2022, "course_code": "HAD-CH101",
     "course_name": "כימיה כללית א'", "core_area": "כימיה כללית",
     "file_url": "https://example.com/had/2022/chem101.pdf"},
    {"institution": "מכללת הדסה", "year": 2022, "course_code": "HAD-CH202",
     "course_name": "כימיה אורגנית", "core_area": "כימיה אורגנית",
     "file_url": "https://example.com/had/2022/orgchem.pdf"},
    {"institution": "מכינת אונ' אריאל", "year": 2021, "course_code": "ARL-BIO110",
     "course_name": "ביולוגיה של התא", "core_area": "ביולוגיה של התא",
     "file_url": "https://example.com/ariel/2021/cellbio.pdf"},
    {"institution": "מכינת אונ' בר‑אילן", "year": 2019, "course_code": "BIU-PHY070",
     "course_name": "פיזיקה למכינה", "core_area": "פיזיקה", "file_url": "https://example.com/biu/2019/physics.pdf"},
])

# שמירה אנונימית בזמן ריצה לסטטיסטיקות (בדפדפן/Session בלבד במודל הדגמה)
if "STATS" not in st.session_state:
    st.session_state["STATS"] = []  # כל רשומה: {institution, year, core_area}


# ==========================
# Utilities
# ==========================

def course_is_fresh(year: int, faculty_id: str) -> bool:
    """בודק תוקף קורס לפי שנת לימוד והכלל של הפקולטה."""
    faculty = FACULTY_LOOKUP[faculty_id]
    max_age = faculty["max_course_age_years"]
    cutoff_year = (datetime.now() - relativedelta(years=max_age)).year
    return year >= cutoff_year


def make_faculty_table_rows(applicant, selections: List[Dict[str, Any]]):
    """מכין רשומות לטבלת ה‑XLSX לפי הפקולטה."""
    rows = []
    for s in selections:
        rows.append({
            "applicant_full_name": applicant.get("full_name", ""),
            "id_or_passport": applicant.get("id_or_passport", ""),
            "institution": s["institution"],
            "year": s["year"],
            "course_code": s.get("course_code", ""),
            "course_name": s["course_name"],
            "core_area": s["core_area"],
            "grade": s.get("grade", ""),
        })
    return rows


def export_faculty_packages(applicant, selections: List[Dict[str, Any]], chosen_faculties: List[str],
                            uploaded_files: Dict[str, bytes]):
    """יוצר ZIP אחד שמכיל לכל פקולטה: טבלת XLSX + תיקיית סילבוסים + גיליונות ציונים (אם הועלו)."""
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fid in chosen_faculties:
            faculty = FACULTY_LOOKUP[fid]
            # 1) טבלת XLSX
            rows = make_faculty_table_rows(applicant, selections)
            df = pd.DataFrame(rows, columns=[f["id"] for f in faculty["table_fields"]])
            xlsx_bytes = io.BytesIO()
            with pd.ExcelWriter(xlsx_bytes, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Core Courses")
            xlsx_bytes.seek(0)
            zf.writestr(f"{fid}/core_courses_{fid}.xlsx", xlsx_bytes.read())

            # 2) סילבוסים (PDF/כל קובץ שהמשתמש העלה או לינק – כאן נשמור קובץ טקסט עם הקישורים)
            # הערה: אם הועלו PDFs אמיתיים דרך העלאת קבצים, נשמור אותם.
            # כאן: אם selection נושא uploaded_file_key – ניקח מהuploaded_files.
            link_list = []
            for i, sel in enumerate(selections, start=1):
                if sel.get("uploaded_file_key") and sel["uploaded_file_key"] in uploaded_files:
                    # נשמור את הקובץ שהועלה בשם עקבי
                    zf.writestr(f"{fid}/syllabi/{i:02d}_{sel['course_name']}.pdf",
                                uploaded_files[sel["uploaded_file_key"]])
                elif sel.get("file_url"):
                    link_list.append(f"- {sel['course_name']}: {sel['file_url']}")
            if link_list:
                zf.writestr(f"{fid}/syllabi/READ_ME_links.txt", "\n".join(link_list))

            # 3) גיליונות ציונים (אם הועלו)
            if uploaded_files.get("transcript_pdf"):
                zf.writestr(f"{fid}/transcripts/transcript.pdf", uploaded_files["transcript_pdf"])

            # 4) טיוטת מייל
            email_body = (
                f"אל: {faculty['email']}\n"
                f"נושא: אימות קורסי ליבה – {applicant.get('full_name', '')}\n\n"
                f"שלום,\n\nמצורפת טבלת קורסי ליבה בתבנית המבוקשת + סילבוסים וגיליון ציונים (אם קיים).\n"
                f"שם: {applicant.get('full_name', '')} | ת.ז/דרכון: {applicant.get('id_or_passport', '')}\n"
                f"טלפון ליצירת קשר: {applicant.get('phone', '')} | דוא""ל: {applicant.get('email','')}\n\n"
                f"בברכה,\n{applicant.get('full_name', '')}\n"
            )
            zf.writestr(f"{fid}/email_draft_{fid}.txt", email_body)

    mem_zip.seek(0)
    return mem_zip


# ==========================
# UI – Streamlit App
# ==========================

st.set_page_config(page_title="אישור קורסי ליבה – MVP", page_icon="🧪", layout="wide")

st.markdown("""
<style>
/* RTL כללי בלי bidi-override */
html, body, [data-testid="stAppViewContainer"], .block-container {
  direction: rtl;
  text-align: right;
}

/* טפסים: שדות יקבלו אוטומטית את הכיוון לפי תו ראשון */
input, textarea {
  direction: rtl;
  text-align: right;
  unicode-bidi: plaintext;  /* אנגלית נשארת LTR, עברית RTL */
}

/* Select / Combobox של Streamlit (BaseWeb) */
[data-baseweb="select"] {
  direction: rtl;
}
[data-baseweb="select"] input {
  unicode-bidi: plaintext;
}

/* מספרים תמיד LTR ונוחים להזנה */
.stNumberInput input[type="number"] {
  direction: ltr !important;
  text-align: left !important;
}

/* טבלאות ו-DataFrame: יישור לימין, אבל בלי להפוך אנגלית/ספרות */
[data-testid="stTable"] table,
[data-testid="stDataFrame"] table {
  direction: rtl;
}
[data-testid="stTable"] th, [data-testid="stTable"] td,
[data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {
  text-align: right !important;
  unicode-bidi: plaintext;  /* מונע “היפוך” של אנגלית/מספרים */
}

/* קוד / Pre / לינקים – תמיד LTR כדי לא להתבלגן */
code, pre, kbd, samp, a {
  direction: ltr;
  text-align: left;
  unicode-bidi: embed;
}

/* מחלקה כללית לשימוש ידני כשצריך טקסט LTR באמצע RTL */
.ltr {
  direction: ltr !important;
  text-align: left !important;
  unicode-bidi: embed !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🧪 מערכת אישור קורסי ליבה – MVP")

with st.expander("אודות המערכת (MVP)", expanded=False):
    st.markdown(
        """
        מטרת הכלי: לאסוף בקלות את נתוני המועמד/ת, לבחור סילבוסים לקורסי הליבה, למפות אותם לדרישות, לבצע בדיקת תוקף, ולהפיק חבילות הגשה לכל פקולטה (XLSX + קבצים נלווים + טיוטת מייל).

        **פרטיות**: איסוף הנתונים האישיים הוא לצורך יצוא הטפסים בלבד. הסטטיסטיקות בתחתית אנונימיות.
        """
    )

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
    consent_stats = st.checkbox("אני מסכים\ת לשימוש אנונימי לסטטיסטיקות מצטברות", value=True)

applicant = {
    "full_name": full_name.strip(),
    "id_or_passport": id_or_passport.strip(),
    "email": email.strip(),
    "phone": phone.strip(),
}

st.divider()

# שלב 2 – בחירת מוסד/שנה/קורסים + העלאת סילבוס מותאם אישית
st.header("שלב 2 – בחירת קורסי ליבה והוספת סילבוסים")

# בחירת מוסד → שנה → סילבוסים זמינים
institutions = sorted(SYLLABI_INDEX["institution"].unique())
inst = st.selectbox("בחר\י מוסד", options=["—"] + institutions)
year_sel = None
selected_rows = []
user_added_items = []  # העלאות ידניות

uploaded_files_store: Dict[str, bytes] = {}

if inst != "—":
    years = sorted(SYLLABI_INDEX[SYLLABI_INDEX["institution"] == inst]["year"].unique(), reverse=True)
    year_sel = st.selectbox("בחר\י שנה", options=years)
    inst_df = SYLLABI_INDEX[(SYLLABI_INDEX["institution"] == inst) & (SYLLABI_INDEX["year"] == year_sel)]

    st.subheader("סילבוסים זמינים מהמוסד והשנה שנבחרו")
    st.dataframe(inst_df, use_container_width=True)

    choose = st.multiselect(
        "בחר\י קורסים להוספה",
        options=inst_df.index.tolist(),
        format_func=lambda idx: f"{inst_df.loc[idx, 'course_name']} ({inst_df.loc[idx, 'core_area']})",
    )

    for idx in choose:
        row = inst_df.loc[idx].to_dict()
        # ברירת מחדל: ללא ציון. המשתמש יוכל לערוך בהמשך.
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
            "institution": u_institution.strip() or "—",
            "year": int(u_year),
            "course_code": u_course_code.strip(),
            "course_name": u_course_name.strip(),
            "core_area": u_core_area,
            "grade": u_grade.strip(),
        }
        if uf is not None:
            key = f"user_pdf_{uf.name}_{datetime.now().timestamp()}"
            uploaded_files_store[key] = uf.getvalue()
            item["uploaded_file_key"] = key
        user_added_items.append(item)
        st.success("נוסף לרשימה הזמנית למטה. סגרו את ה‑popover כדי לראות.")

# מאחדים בחירות ממדד הסילבוסים + העלאות ידניות
all_selections = selected_rows + user_added_items

if all_selections:
    st.subheader("רשימת הקורסים שנבחרו")

    # עריכה ידנית של פרטים (כולל הוספת ציון)
    editable_df = pd.DataFrame(all_selections)
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
        },
        key="editable_df",
    )

    # שמירה חזרה למבנה רשומות
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
chosen_faculties = []
for i, f in enumerate(FACULTIES):
    with cols[i % 3]:
        chk = st.checkbox(f["name"], value=False)
        if chk:
            chosen_faculties.append(f["id"])

# בדיקת תוקף לכל פקולטה
if selections and chosen_faculties:
    st.subheader("בדיקת התיישנות הקורסים לפי כללי כל פקולטה")
    val_tabs = st.tabs([FACULTY_LOOKUP[fid]["name"] for fid in chosen_faculties])
    for tab, fid in zip(val_tabs, chosen_faculties):
        with tab:
            rows = []
            for s in selections:
                fresh = course_is_fresh(int(s.get("year", 0) or 0), fid)
                rows.append({
                    "מוסד": s.get("institution", ""),
                    "שנה": s.get("year", ""),
                    "שם הקורס": s.get("course_name", ""),
                    "תחום ליבה": s.get("core_area", ""),
                    "בתוקף?": "כן" if fresh else "לא",
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
        mem_zip = export_faculty_packages(applicant, selections, chosen_faculties, uploaded_files_store)
        st.download_button(
            label="הורדת הקובץ (ZIP)",
            data=mem_zip,
            file_name="core_courses_packages.zip",
            mime="application/zip",
        )
        st.success("נוצרו חבילות ההגשה + טיוטות מייל. ניתן להוריד כעת.")
else:
    st.info("יש למלא פרטים אישיים בסיסיים, לבחור לפחות קורס אחד ולסמן פקולטה אחת לפחות.")

st.divider()

# שלב 6 – סטטיסטיקות (אנונימיות בזמן ריצה)
st.header("סטטיסטיקות (אנונימי, לזמן ריצה בלבד במודל ההדגמה)")
if consent_stats and selections:
    for s in selections:
        st.session_state["STATS"].append({
            "institution": s.get("institution", "—"),
            "year": s.get("year", "—"),
            "core_area": s.get("core_area", "—"),
        })

if st.session_state["STATS"]:
    stats_df = pd.DataFrame(st.session_state["STATS"])
    agg = stats_df.value_counts(["institution", "year", "core_area"]).reset_index(name="count")
    st.dataframe(agg, use_container_width=True)
else:
    st.write("טרם נאספו נתונים להצגה.")

st.caption(
    "\nMVP זה נועד להדגים את הזרימה מקצה לקצה. בשלב הבא נוסיף DB מתמשך, ניהול אדמין לאינדקס סילבוסים, ושליחה ישירה מהדוא\"ל הפרטי של המועמד/ת (OAuth).")
