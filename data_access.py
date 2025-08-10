# data_access.py
import pandas as pd
from typing import List, Dict, Any, Tuple
from db import pooled_cursor

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

    faculties = [{
        "id": f["id"], "name": f["name"], "email": f["email"],
        "max_course_age_years": f["max_course_age_years"],
        "table_fields": fields_by_fac.get(f["id"], [])
    } for f in facs]
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

def course_is_fresh(year: int, faculty_id: str) -> bool:
    with pooled_cursor(commit=False) as cur:
        cur.execute("SELECT max_course_age_years FROM faculties WHERE id=%s", (faculty_id,))
        row = cur.fetchone()
    if not row:
        return True
    cutoff_year = datetime_now_year_minus(row["max_course_age_years"])
    return year >= cutoff_year

def datetime_now_year_minus(years: int) -> int:
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    return (datetime.now() - relativedelta(years=years)).year
