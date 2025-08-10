st.set_page_config(page_title="אישור קורסי ליבה – MVP", page_icon="🧪", layout="wide")

st.markdown("""
<style>
body, html {
    direction: RTL;
    unicode-bidi: bidi-override;
    text-align: right;
}
p, div, input, label, h1, h2, h3, h4, h5, h6 {
    direction: RTL;
    unicode-bidi: bidi-override;
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

st.title("🧪 מערכת אישור קורסי ליבה – גרסת הדגמה")

with st.expander("אודות המערכת (גרסת הדגמה)", expanded=False):
    st.markdown(
        """
        מטרת הכלי: לאסוף בקלות את נתוני המועמד/ת, לבחור סילבוסים לקורסי הליבה, למפות אותם לדרישות, לבצע בדיקת תוקף, ולהפיק חבילות הגשה לכל פקולטה (קובץ אקסל + קבצים נלווים + טיוטת מייל).

        **פרטיות**: איסוף הנתונים האישיים הוא לצורך יצוא הטפסים בלבד. הסטטיסטיקות בתחתית אנונימיות.
        """
    )

# שלב 1 – מידע אישי כללי
st.header("שלב 1 – מידע אישי כללי")
col1, col2, col3 = st.columns(3)
with col1:
    full_name = st.text_input("שם מלא")
    id_or_passport = st.text_input("תעודת זהות / דרכון")
with col2:
    email = st.text_input("דוא\"ל")
    phone = st.text_input("טלפון")
with col3:
    consent_stats = st.checkbox("אני מסכים/ה לשימוש אנונימי לסטטיסטיקות מצטברות", value=True)

# ...
# בהמשך בקוד – טקסטים שהיו באנגלית שונו לעברית:
# לדוגמה:
st.markdown("**או הוספה ידנית של סילבוס ממוסד אחר**")
with st.popover("הוספת סילבוס ידני"):
    colu1, colu2 = st.columns(2)
    with colu1:
        u_institution = st.text_input("מוסד")
        u_course_name = st.text_input("שם הקורס")
        u_core_area = st.selectbox("תחום ליבה", CORE_AREAS)
    with colu2:
        u_year = st.number_input("שנת לימוד", min_value=2000, max_value=datetime.now().year, value=datetime.now().year)
        u_course_code = st.text_input("מספר קורס (אופציונלי)")
        u_grade = st.text_input("ציון (אם יש)")
    uf = st.file_uploader("העלאת סילבוס (PDF)", type=["pdf"], accept_multiple_files=False)
    if st.button("הוסף לרשימה"):
        # ...

# גם בכפתורים:
if ready_to_export:
    if st.button("צור קובץ ZIP לכל הפקולטות שנבחרו"):
        mem_zip = export_faculty_packages(applicant, selections, chosen_faculties, uploaded_files_store)
