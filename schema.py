# schema.py
from db import pooled_cursor

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
    CREATE TABLE IF NOT EXISTS core_areas (name TEXT PRIMARY KEY);
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
        institution TEXT, year INT, core_area TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    with pooled_cursor() as cur:
        cur.execute(ddl)

def seed_if_empty():
    with pooled_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM faculties;")
        if cur.fetchone()["c"] == 0:
            cur.execute("""
                INSERT INTO faculties (id, name, email, max_course_age_years) VALUES
                ('huji','האוניברסיטה העברית – פקולטה לרפואה','corecourses@huji.ac.il',10),
                ('bgu','אוניברסיטת בן-גוריון – פקולטה למדעי הבריאות','corecourses@bgu.ac.il',11),
                ('tau','אוניברסיטת תל-אביב – הפקולטה לרפואה','corecourses@tau.ac.il',10);
            """)
            cur.executemany("""
                INSERT INTO faculty_table_fields (faculty_id, field_id, label, position)
                VALUES (%s,%s,%s,%s)
            """, [
                ("huji","applicant_full_name","שם מלא",1),
                ("huji","id_or_passport","ת.ז/דרכון",2),
                ("huji","institution","מוסד לימוד",3),
                ("huji","year","שנה",4),
                ("huji","course_name","שם הקורס",5),
                ("huji","core_area","תחום ליבה",6),
                ("huji","grade","ציון",7),
                ("bgu","applicant_full_name","שם מלא",1),
                ("bgu","id_or_passport","ת.ז/דרכון",2),
                ("bgu","institution","מוסד לימוד",3),
                ("bgu","year","שנה",4),
                ("bgu","course_code","מס' קורס",5),
                ("bgu","course_name","שם הקורס",6),
                ("bgu","core_area","תחום ליבה",7),
                ("bgu","grade","ציון",8),
                ("tau","applicant_full_name","שם מלא",1),
                ("tau","id_or_passport","ת.ז/דרכון",2),
                ("tau","institution","מוסד לימוד",3),
                ("tau","year","שנה",4),
                ("tau","course_name","שם הקורס",5),
                ("tau","core_area","תחום ליבה",6),
                ("tau","grade","ציון",7),
            ])
        cur.execute("SELECT COUNT(*) AS c FROM core_areas;")
        if cur.fetchone()["c"] == 0:
            cur.executemany("INSERT INTO core_areas (name) VALUES (%s)", [
                ("כימיה כללית",), ("כימיה אורגנית",), ("ביוכימיה",),
                ("ביולוגיה של התא",), ("מיקרוביולוגיה",), ("פיזיקה",), ("סטטיסטיקה",)
            ])
        cur.execute("SELECT COUNT(*) AS c FROM syllabi;")
        if cur.fetchone()["c"] == 0:
            cur.executemany("""
                INSERT INTO syllabi (institution, year, course_code, course_name, core_area, file_url)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, [
                ("מכללת הדסה", 2022, "HAD-CH101", "כימיה כללית א'", "כימיה כללית", "https://example.com/had/2022/chem101.pdf"),
                ("מכללת הדסה", 2022, "HAD-CH202", "כימיה אורגנית", "כימיה אורגנית", "https://example.com/had/2022/orgchem.pdf"),
                ("מכינת אונ' אריאל", 2021, "ARL-BIO110", "ביולוגיה של התא", "ביולוגיה של התא", "https://example.com/ariel/2021/cellbio.pdf"),
                ("מכינת אונ' בר-אילן", 2019, "BIU-PHY070", "פיזיקה למכינה", "פיזיקה", "https://example.com/biu/2019/physics.pdf"),
            ])

def ensure_db_ready():
    init_db()
    seed_if_empty()
