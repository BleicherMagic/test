import io
import os
import zipfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any, Tuple, Optional

import pandas as pd
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================
# DB CONNECTION & INIT
# ==========================

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

@st.cache_resource
def init_connection_pool() -> SimpleConnectionPool:
    # Prefer Streamlit secrets, else env var
    if "database_url" in st.secrets:
        db_url = st.secrets["database_url"]
    else:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

    # Most managed Postgres providers (Neon/Supabase) require SSL
    # SimpleConnectionPool forwards kwargs to psycopg2.connect
    return SimpleConnectionPool(
        minconn=1,
        maxconn=6,
        dsn=db_url,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )

_pool = init_connection_pool()

@contextmanager
def pooled_cursor(commit: bool = True):
    """
    Usage:
        with pooled_cursor() as cur:
            cur.execute("...")
            rows = cur.fetchall()
    Automatically commits on success (unless commit=False) and returns
    the connection to the pool.
    """
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            yield cur
            if commit:
                conn.commit()
    except Exception:
        # If something goes wrong, rollback this connection to keep it clean
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)

# ==========================
# DB INIT & SEED
# ==========================

def init_db():
    ddl = """
    CREATE TABLE IF NOT EXISTS faculties (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        max_course_age_years INT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS faculty_table_fields (
        faculty_id TEXT REFERENCES faculties(id) ON DELETE CASCADE,
        field_id TEXT NOT NULL,
        label TEXT NOT NULL,
        position INT NOT NULL,
        PRIMARY KEY (faculty_id, field_id)
    );

    CREATE TABLE IF NOT EXISTS core_areas (
        name TEXT PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS syllabi (
        id SERIAL PRIMARY KEY,
        institution TEXT NOT NULL,
        year INT NOT NULL,
        course_code TEXT,
        course_name TEXT NOT NULL,
        core_area TEXT NOT NULL REFERENCES core_areas(name) ON DELETE RESTRICT,
        file_url TEXT
    );

    CREATE TABLE IF NOT EXISTS stats (
        id BIGSERIAL PRIMARY KEY,
        institution TEXT,
        year INT,
        core_area TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    with pooled_cursor() as cur:
        cur.execute(ddl)

def seed_if_empty():
    with pooled_cursor() as cur:
        # faculties
        cur.execute("SELECT COUNT(*) AS c FROM faculties;")
        if cur.fetchone()["c"] == 0:
            cur.execute("""
                INSERT INTO faculties (id, name, email, max_course_age_years) VALUES
                ('huji', 'האוניברסיטה העברית – פקולטה לרפואה', 'corecourses@huji.ac.il', 10),
                ('bgu',  'אוניברסיטת בן-גוריון – פקולטה למדעי הבריאות', 'corecourses@bgu.ac.il', 11),
                ('tau',  'אוניברסיטת תל-אביב – הפקולטה לרפואה', 'corecourses@tau.ac.il', 10);
            """)

            fields = [
                # HUJI
                ("huji","applicant_full_name","שם מלא",1),
                ("huji","id_or_passport","ת.ז/דרכון",2),
                ("huji","institution","מוסד לימוד",3),
                ("huji","year","שנה",4),
                ("huji","course_name","שם הקורס",5),
                ("huji","core_area","תחום ליבה",6),
                ("huji","grade","ציון",7),
                # BGU
                ("bgu","applicant_full_name","שם מלא",1),
                ("bgu","id_or_passport","ת.ז/דרכון",2),
                ("bgu","institution","מוסד לימוד",3),
                ("bgu","year","שנה",4),
                ("bgu","course_code","מס' קורס",5),
                ("bgu","course_name","שם הקורס",6),
                ("bgu","core_area","תחום ליבה",7),
                ("bgu","grade","ציון",8),
                # TAU
                ("tau","applicant_full_name","שם מלא",1),
                ("tau","id_or_passport","ת.ז/דרכון",2),
                ("tau","institution","מוסד לימוד",3),
                ("tau","year","שנה",4),
                ("tau","course_name","שם הקורס",5),
                ("tau","core_area","תחום ליבה",6),
                ("tau","grade","ציון",7),
            ]
            cur.executemany("""
                INSERT INTO faculty_table_fields (faculty_id, field_id, label, position)
                VALUES (%s, %s, %s, %s)
            """, fields)

        # core_areas
        cur.execute("SELECT COUNT(*) AS c FROM core_areas;")
        if cur.fetchone()["c"] == 0:
            core_areas = [
                ("כימיה כללית",), ("כימיה אורגנית",), ("ביוכימיה",),
                ("ביולוגיה של התא",), ("מיקרוביולוגיה",), ("פיזיקה",), ("סטטיסטיקה",)
            ]
            cur.executemany("INSERT INTO core_areas (name) VALUES (%s)", core_areas)

        # syllabi
        cur.execute("SELECT COUNT(*) AS c FROM syllabi;")
        if cur.fetchone()["c"] == 0:
            syllabi_rows = [
                ("מכללת הדסה", 2022, "HAD-CH101", "כימיה כללית א'", "כימיה כללית", "https://example.com/had/2022/chem101.pdf"),
                ("מכללת הדסה", 2022, "HAD-CH202", "כימיה אורגנית", "כימיה אורגנית", "https://example.com/had/2022/orgchem.pdf"),
                ("מכינת אונ' אריאל", 2021, "ARL-BIO110", "ביולוגיה של התא", "ביולוגיה של התא", "https://example.com/ariel/2021/cellbio.pdf"),
                ("מכינת אונ' בר-אילן", 2019, "BIU-PHY070", "פיזיקה למכינה", "פיזיקה", "https://example.com/biu/2019/physics.pdf"),
            ]
            cur.executemany("""
                INSERT INTO syllabi (institution, year, course_code, course_name, core_area, file_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, syllabi_rows)

# ==========================
# FETCHERS (using pool)
# ==========================

def fetch_faculties() -> Tuple[list, dict]:
    with pooled_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM faculties ORDER BY id;")
        facs = cur.fetchall()

        cur.execute("""
            SELECT faculty_id, field_id, label, position
            FROM faculty_table_fields
            ORDER BY faculty_id, position
        """)
        fields = cur.fetchall()

    fields_by_fac = {}
    for f in fields:
        fields_by_fac.setdefault(f["faculty_id"], []).append({"id": f["field_id"], "label": f["label"]})

    faculties = []
    for f in facs:
        faculties.append({
            "id": f["id"],
            "name": f["name"],
            "email": f["email"],
            "max_course_age_years": f["max_course_age_years"],
            "table_fields": fields_by_fac.get(f["id"], [])
        })
    lookup = {f["id"]: f for f in faculties}
    return faculties, lookup

def fetch_core_areas() -> list:
    with pooled_cursor(commit=False) as cur:
        cur.execute("SELECT name FROM core_areas ORDER BY name;")
        return [r["name"] for r in cur.fetchall()]

def fetch_syllabi_df() -> pd.DataFrame:
    with pooled_cursor(commit=False) as cur:
        cur.execute("""
            SELECT id, institution, year, course_code, course_name, core_area, file_url
            FROM syllabi
            ORDER BY institution, year DESC, course_name
        """)
        rows = cur.fetchall()
    return pd.DataFrame(rows)

def insert_stat_rows(rows: list):
    if not rows:
        return
    with pooled_cursor() as cur:
        cur.executemany("""
            INSERT INTO stats (institution, year, core_area)
            VALUES (%s, %s, %s)
        """, rows)

def fetch_stats_agg_df() -> pd.DataFrame:
    with pooled_cursor(commit=False) as cur:
        cur.execute("""
            SELECT institution, year, core_area, COUNT(*) AS count
            FROM stats
            GROUP BY institution, year, core_area
            ORDER BY count DESC, institution, year, core_area
        """)
        rows = cur.fetchall()
    return pd.DataFrame(rows)

# ==========================
# Utilities
# ==========================

def course_is_fresh(year: int, faculty_id: str, FACULTY_LOOKUP: dict) -> bool:
    """בודק תוקף קורס לפי שנת לימוד והכלל של הפקולטה."""
    faculty = FACULTY_LOOKUP[faculty_id]
    max_age = faculty["max_course_age_years"]
    cutoff_year = (datetime.now() - relativedelta(years=max_age)).year
    return year >= cutoff_year

def make_faculty_table_rows(applicant, selections: List[Dict[str, Any]]):
    """מכין רשומות לטבלת ה-XLSX לפי הפקולטה."""
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
                            uploaded_files: Dict[str, bytes], FACULTY_LOOKUP: dict):
    """יוצר ZIP אחד שמכיל לכל פקולטה: טבלת XLSX + תיקיית סילבוסים + גיליונות ציונים (אם הועלו)."""
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fid in chosen_faculties:
            faculty = FACULTY_LOOKUP[fid]
            # 1) טבלת XLSX – כותרות בעברית
            rows = make_faculty_table_rows(applicant, selections)
            df = pd.DataFrame(rows)
            cols_order = [fld["id"] for fld in faculty["table_fields"] if fld["id"] in df.columns]
            df = df[cols_order]
            heb_headers = {fld["id"]: fld["label"] for fld in faculty["table_fields"]}
            df.rename(columns=heb_headers, inplace=True)

            xlsx_bytes = io.BytesIO()
            with pd.ExcelWriter(xlsx_bytes, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="קורסי ליבה")
            xlsx_bytes.seek(0)
            zf.writestr(f"{fid}/core_courses_{fid}.xlsx", xlsx_bytes.read())

            # 2) סילבוסים: קבצים שהועלו או קישורים
            link_list = []
            for i, sel in enumerate(selections, start=1):
                if sel.get("uploaded_file_key") and sel["uploaded_file_key"] in uploaded_files:
                    zf.writestr(f"{fid}/syllabi/{i:02d}_{sel['course_name']}.pdf",
                                uploaded_files[sel["uploaded_file_key"]])
                elif sel.get("file_url"):
                    link_list.append(f"- {sel['course_name']}: {sel['file_url']}")
            if link_list:
                zf.writestr(f"{fid}/syllabi/קישורים_לסילבוסים.txt", "\n".join(link_list))

            # 3) גיליונות ציונים (אם הועלו)
            if uploaded_files.get("transcript_pdf"):
                zf.writestr(f"{fid}/transcripts/גיליון_ציונים.pdf", uploaded_files["transcript_pdf"])

            # 4) טיוטת מייל
            email_body = (
                f"אל: {faculty['email']}\n"
                f"נושא: אימות קורסי ליבה – {applicant.get('full_name','')}\n\n"
                f"שלום,\n\nמצורפת טבלת קורסי ליבה בתבנית המבוקשת + סילבוסים וגיליון ציונים (אם קיים).\n"
                f"שם: {applicant.get('full_name','')} | ת.ז/דרכון: {applicant.get('id_or_passport','')}\n"
                f"טלפון ליצירת קשר: {applicant.get('phone','')} | דוא\"ל: {applicant.get('email','')}\n\n"
                f"בברכה,\n{applicant.get('full_name','')}\n"
            )
            zf.writestr(f"{fid}/טיוטת_מייל_{fid}.txt", email_body)

    mem_zip.seek(0)
    return mem_zip

# ==========================
# UI – Streamlit App
# ==========================

st.set_page_config(page_title="אישור קורסי ליבה – MVP", page_icon="🧪", layout="wide")

# RTL מינימלי לכל האפליקציה + יישור טבלאות, בלי להפוך אנגלית/מספרים
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], .block-container { direction: rtl; text-align: right; }
[data-testid="stTable"] table, [data-testid="stDataFrame"] table { direction: rtl; }
[data-testid="stTable"] th, [data-testid="stTable"] td,
[data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td { text-align: right !important; unicode-bidi: plaintext; }
[data-baseweb="select"] { direction: rtl; }
input, textarea { direction: rtl; text-align: right; unicode-bidi: plaintext; }
.stNumberInput input[type="number"] { direction: ltr !important; text-align: left !important; }
code, pre, kbd, samp, a { direction: ltr; text-align: left; unicode-bidi: embed; }
.ltr { direction: ltr !important; text-align: left !important; unicode-bidi: embed !important; }
</style>
""", unsafe_allow_html=True)

st.title("🧪 מערכת אישור קורסי ליבה – MVP")

# --- DB init + seed (once per session) ---
@st.cache_resource
def ensure_db_ready():
    init_db()
    seed_if_empty()
    return True

ensure_db_ready()

# --- Load config data from DB ---
FACULTIES, FACULTY_LOOKUP = fetch_faculties()
CORE_AREAS = fetch_core_areas()
SYLLABI_INDEX = fetch_syllabi_df()

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
year_sel = None
selected_rows = []
user_added_items = []  # העלאות ידניות

uploaded_files_store: Dict[str, bytes] = {}

if inst != "—":
    years = sorted(SYLLABI_INDEX[SYLLABI_INDEX["institution"] == inst]["year"].unique(), reverse=True)
    year_sel = st.selectbox("בחר/י שנה", options=years)
    inst_df = SYLLABI_INDEX[(SYLLABI_INDEX["institution"] == inst) & (SYLLABI_INDEX["year"] == year_sel)]

    st.subheader("סילבוסים זמינים מהמוסד והשנה שנבחרו")
    st.dataframe(inst_df.drop(columns=["id"]), use_container_width=True)

    choose = st.multiselect(
        "בחר/י קורסים להוספה",
        options=inst_df.index.tolist(),
        format_func=lambda idx: f"{inst_df.loc[idx, 'course_name']} ({inst_df.loc[idx, 'core_area']})",
    )

    for idx in choose:
        row = inst_df.loc[idx].to_dict()
        row.update({"grade": ""})  # ברירת מחדל: ללא ציון
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
            # הערה: קבצים נשמרים זמנית בזיכרון; שמירה ל-DB/אחסון אובייקטים – בשלב הבא
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
    # סידור עמודות לתצוגה
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
chosen_faculties = []
for i, f in enumerate(FACULTIES):
    with cols[i % 3]:
        chk = st.checkbox(f["name"], value=False)
        if chk:
            chosen_faculties.append(f["id"])

if selections and chosen_faculties:
    st.subheader("בדיקת התיישנות הקורסים לפי כללי כל פקולטה")
    val_tabs = st.tabs([FACULTY_LOOKUP[fid]["name"] for fid in chosen_faculties])
    for tab, fid in zip(val_tabs, chosen_faculties):
        with tab:
            rows = []
            for s in selections:
                y = int(s.get("year", 0) or 0)
                fresh = course_is_fresh(y, fid, FACULTY_LOOKUP)
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
        mem_zip = export_faculty_packages(applicant, selections, chosen_faculties, uploaded_files_store, FACULTY_LOOKUP)
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

# שלב 6 – סטטיסטיקות (אנונימיות, בבסיס הנתונים)
st.header("סטטיסטיקות (אנונימי)")
if consent_stats and selections:
    rows_to_insert = []
    for s in selections:
        rows_to_insert.append((
            s.get("institution", "—"),
            int(s.get("year", 0) or 0),
            s.get("core_area", "—"),
        ))
    insert_stat_rows(rows_to_insert)

# הצגה
try:
    agg = fetch_stats_agg_df()
    if not agg.empty:
        st.dataframe(agg, use_container_width=True)
    else:
        st.write("טרם נאספו נתונים להצגה.")
except Exception as e:
    st.warning(f"לא ניתן להציג סטטיסטיקות כרגע: {e}")

st.caption("\nMVP זה נועד להדגים את הזרימה מקצה לקצה. בשלב הבא נוסיף אחסון קבצים לסילבוסים (Object Storage) ושילוב OAuth לשליחת מיילים.")
