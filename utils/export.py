# utils/export.py
import io, zipfile
import pandas as pd


def make_faculty_table_rows(applicant, selections):
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


def export_faculty_packages(applicant, selections, chosen_faculties, uploaded_files, FACULTY_LOOKUP):
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fid in chosen_faculties:
            faculty = FACULTY_LOOKUP[fid]
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

            link_list = []
            for i, sel in enumerate(selections, start=1):
                if sel.get("uploaded_file_key") and sel["uploaded_file_key"] in uploaded_files:
                    zf.writestr(f"{fid}/syllabi/{i:02d}_{sel['course_name']}.pdf",
                                uploaded_files[sel["uploaded_file_key"]])
                elif sel.get("file_url"):
                    link_list.append(f"- {sel['course_name']}: {sel['file_url']}")
            if link_list:
                zf.writestr(f"{fid}/syllabi/קישורים_לסילבוסים.txt", "\n".join(link_list))

            email_body = (
                f"אל: {faculty['email']}\n"
                f"נושא: אימות קורסי ליבה – {applicant.get('full_name', '')}\n\n"
                f"שלום,\n\nמצורפת טבלת קורסי ליבה בתבנית המבוקשת + סילבוסים וגיליון ציונים (אם קיים).\n"
                f"שם: {applicant.get('full_name', '')} | ת.ז/דרכון: {applicant.get('id_or_passport', '')}\n"
                f"טלפון ליצירת קשר: {applicant.get('phone', '')} | דוא\"ל: {applicant.get('email', '')}\n\n"
                f"בברכה,\n{applicant.get('full_name', '')}\n"
            )
            zf.writestr(f"{fid}/טיוטת_מייל_{fid}.txt", email_body)

    mem_zip.seek(0)
    return mem_zip
