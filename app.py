import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import plotly.express as px

from datetime import datetime, date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib.styles import getSampleStyleSheet


# ================= PAGE CONFIG =================

st.set_page_config(
    page_title="Blood Donors Management System",
    page_icon="🩸",
    layout="wide"
)


# ================= DATABASE =================

def get_connection():
    conn = sqlite3.connect("blood_donors.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row["name"] for row in cursor.fetchall()]

    user_required = {
        "username": "TEXT",
        "email": "TEXT",
        "password": "TEXT"
    }

    for column, datatype in user_required.items():

        if column not in user_columns:
            cursor.execute(
                f"ALTER TABLE users ADD COLUMN {column} {datatype}"
            )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            blood_group TEXT,
            phone TEXT,
            city TEXT,
            last_donation TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(donors)")
    donor_columns = [row["name"] for row in cursor.fetchall()]

    donor_required = {
        "name": "TEXT",
        "age": "INTEGER",
        "gender": "TEXT",
        "blood_group": "TEXT",
        "phone": "TEXT",
        "city": "TEXT",
        "last_donation": "TEXT",
        "availability": "TEXT DEFAULT 'Available'",
        "username": "TEXT"
    }

    for column, datatype in donor_required.items():

        if column not in donor_columns:
            cursor.execute(
                f"ALTER TABLE donors ADD COLUMN {column} {datatype}"
            )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blood_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            requester_username TEXT NOT NULL DEFAULT '',
            patient_name TEXT NOT NULL DEFAULT '',
            blood_group TEXT NOT NULL,
            units INTEGER NOT NULL,
            hospital TEXT NOT NULL,
            city TEXT NOT NULL,
            required_date TEXT NOT NULL,
            urgency TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Keep compatibility with older blood_requests table versions.
    cursor.execute("PRAGMA table_info(blood_requests)")
    request_columns = {row[1] for row in cursor.fetchall()}
    request_migrations = {
        "username": "TEXT DEFAULT ''",
        "requester_username": "TEXT NOT NULL DEFAULT ''",
        "patient_name": "TEXT NOT NULL DEFAULT ''",
        "blood_group": "TEXT DEFAULT ''",
        "units": "INTEGER NOT NULL DEFAULT 1",
        "hospital": "TEXT NOT NULL DEFAULT ''",
        "city": "TEXT NOT NULL DEFAULT ''",
        "required_date": "TEXT NOT NULL DEFAULT ''",
        "urgency": "TEXT NOT NULL DEFAULT 'Normal'",
        "notes": "TEXT DEFAULT ''",
        "status": "TEXT DEFAULT 'Pending'",
        "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP"
    }
    for column, definition in request_migrations.items():
        if column not in request_columns:
            cursor.execute(
                f"ALTER TABLE blood_requests ADD COLUMN {column} {definition}"
            )

    # Backfill both username fields for records created by older versions.
    request_columns.update(request_migrations.keys())
    if "requester_username" in request_columns and "username" in request_columns:
        cursor.execute("""
            UPDATE blood_requests
            SET requester_username = COALESCE(NULLIF(requester_username, ''), username, '')
            WHERE requester_username IS NULL OR requester_username = ''
        """)
        cursor.execute("""
            UPDATE blood_requests
            SET username = COALESCE(NULLIF(username, ''), requester_username, '')
            WHERE username IS NULL OR username = ''
        """)

    conn.commit()
    conn.close()


create_tables()


# ================= PASSWORD HASH =================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ================= SESSION STATE =================

defaults = {
    "user_logged_in": False,
    "admin_logged_in": False,
    "username": ""
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ================= CSS DESIGN =================

st.markdown("""
<style>

.stApp {
    background-color: #f5f7fb;
}

.main-title {
    background: linear-gradient(120deg, #8b0000, #e63946);
    padding: 30px;
    border-radius: 18px;
    color: white;
    text-align: center;
    margin-bottom: 25px;
}

.main-title h1 {
    font-size: 35px;
    font-weight: 800;
}

.section-title {
    color: #a00020;
    font-size: 27px;
    font-weight: 800;
}

div[data-testid="stMetric"] {
    background: white;
    padding: 20px;
    border-radius: 14px;
    border-left: 5px solid #c1121f;
    box-shadow: 0 3px 12px rgba(0,0,0,0.05);
}

div.stButton > button {
    background: #b00020;
    color: white;
    border-radius: 9px;
    border: none;
    font-weight: bold;
    width: 100%;
}

div.stButton > button:hover {
    background: #800018;
    color: white;
}

.footer {
    text-align: center;
    padding: 20px;
    color: gray;
}

</style>
""", unsafe_allow_html=True)


# ================= HEADER =================

st.markdown("""
<div class="main-title">
    <h1>🩸 Blood Donors Management System</h1>
    <h3>Donate Blood - Save Lives</h3>
    <p>A Smart Platform for Blood Donor Management</p>
</div>
""", unsafe_allow_html=True)


# ================= SIDEBAR =================

st.sidebar.markdown("## 🩸 Blood Bank")
st.sidebar.markdown("---")

if st.session_state.user_logged_in:

    st.sidebar.success(
        f"Welcome, {st.session_state.username}"
    )

if st.session_state.admin_logged_in:

    st.sidebar.success("Administrator Logged In")


menu = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "User Registration",
        "User Login",
        "Donor Registration",
        "Donor Availability",
        "Emergency Blood Request",
        "My Blood Requests",
        "Admin Manage Requests",
        "Search Donors",
        "Donor Reports",
        "All Donors",
        "Admin Login",
        "Admin Dashboard",
        "Update Donor",
        "Delete Donor",
        "Logout"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Blood Donors Management System")
st.sidebar.caption("Python | Streamlit | SQLite")


# ================= HOME =================

if menu == "Home":

    st.markdown(
        '<p class="section-title">📊 Dashboard Overview</p>',
        unsafe_allow_html=True
    )

    conn = get_connection()

    total_donors = conn.execute(
        "SELECT COUNT(*) FROM donors"
    ).fetchone()[0]

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    total_groups = conn.execute("""
        SELECT COUNT(DISTINCT blood_group)
        FROM donors
        WHERE blood_group IS NOT NULL
    """).fetchone()[0]

    total_cities = conn.execute("""
        SELECT COUNT(DISTINCT city)
        FROM donors
        WHERE city IS NOT NULL AND city != ''
    """).fetchone()[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("🩸 Total Donors", total_donors)
    c2.metric("👥 Registered Users", total_users)
    c3.metric("❤️ Blood Groups", total_groups)
    c4.metric("📍 Cities Covered", total_cities)

    st.markdown("---")

    left, right = st.columns(2)

    blood_df = pd.read_sql_query("""
        SELECT blood_group, COUNT(*) AS total
        FROM donors
        WHERE blood_group IS NOT NULL
        GROUP BY blood_group
    """, conn)

    city_df = pd.read_sql_query("""
        SELECT city, COUNT(*) AS total
        FROM donors
        WHERE city IS NOT NULL AND city != ''
        GROUP BY city
        ORDER BY total DESC
        LIMIT 10
    """, conn)

    with left:

        st.subheader("🩸 Blood Group Distribution")

        if not blood_df.empty:

            fig = px.pie(
                blood_df,
                names="blood_group",
                values="total",
                hole=0.45,
                title="Donors by Blood Group"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:
            st.info("No donor data available.")

    with right:

        st.subheader("📍 City-wise Donors")

        if not city_df.empty:

            fig = px.bar(
                city_df,
                x="city",
                y="total",
                color="city",
                title="Top 10 Cities"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:
            st.info("No city data available.")

    st.markdown("---")

    st.subheader("🕒 Recent Donors")

    recent_df = pd.read_sql_query("""
        SELECT name, blood_group, city, last_donation
        FROM donors
        ORDER BY id DESC
        LIMIT 5
    """, conn)

    conn.close()

    if not recent_df.empty:

        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No donors registered yet.")

    st.markdown("---")

    a, b, c = st.columns(3)

    a.info("❤️ Save Lives\n\nHelp people find blood donors.")
    b.info("🔍 Quick Search\n\nFind donors by blood group and city.")
    c.info("📊 Smart Reports\n\nDownload donor reports.")


# ================= USER REGISTRATION =================

elif menu == "User Registration":

    st.markdown(
        '<p class="section-title">📝 Create Your Account</p>',
        unsafe_allow_html=True
    )

    with st.form("registration_form"):

        username = st.text_input("Username")
        email = st.text_input("Email Address")

        show_password = st.checkbox("Show Password")

        password = st.text_input(
            "Password",
            type="default" if show_password else "password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="default" if show_password else "password"
        )

        submit = st.form_submit_button("Register")

        if submit:

            if not username or not email or not password or not confirm_password:

                st.warning("Please fill all fields.")

            elif "@" not in email or "." not in email:

                st.warning("Enter a valid email address.")

            elif password != confirm_password:

                st.error("Passwords do not match.")

            elif len(password) < 6:

                st.warning("Password must be at least 6 characters.")

            else:

                conn = get_connection()

                try:

                    conn.execute("""
                        INSERT INTO users (username, email, password)
                        VALUES (?, ?, ?)
                    """, (
                        username,
                        email,
                        hash_password(password)
                    ))

                    conn.commit()

                    st.success("Account Created Successfully!")

                except sqlite3.IntegrityError:

                    st.error("Username already exists.")

                finally:
                    conn.close()


# ================= USER LOGIN =================

elif menu == "User Login":

    st.markdown(
        '<p class="section-title">🔐 User Login</p>',
        unsafe_allow_html=True
    )

    if st.session_state.user_logged_in:

        st.success(
            f"Welcome back, {st.session_state.username}!"
        )

    else:

        with st.form("user_login_form"):

            username = st.text_input("Username")

            show_login = st.checkbox("Show Password")

            password = st.text_input(
                "Password",
                type="default" if show_login else "password"
            )

            submit = st.form_submit_button("Login")

            if submit:

                if not username or not password:

                    st.warning("Enter username and password.")

                else:

                    conn = get_connection()

                    user = conn.execute("""
                        SELECT id, username, password
                        FROM users
                        WHERE username=?
                    """, (username,)).fetchone()

                    if user:

                        entered_hash = hash_password(password)

                        if user["password"] == entered_hash or user["password"] == password:

                            if user["password"] == password:

                                conn.execute("""
                                    UPDATE users
                                    SET password=?
                                    WHERE id=?
                                """, (
                                    entered_hash,
                                    user["id"]
                                ))

                                conn.commit()

                            st.session_state.user_logged_in = True
                            st.session_state.username = username

                            conn.close()

                            st.success("Login Successful!")
                            st.rerun()

                        else:

                            conn.close()
                            st.error("Incorrect Password.")

                    else:

                        conn.close()
                        st.error("Username not found. Please register first.")


# ================= DONOR REGISTRATION =================

elif menu == "Donor Registration":

    st.markdown(
        '<p class="section-title">🩸 Donor Registration</p>',
        unsafe_allow_html=True
    )

    if not st.session_state.user_logged_in:

        st.warning("Please login first.")

    else:

        st.success(
            f"Welcome {st.session_state.username}"
        )

        with st.form("donor_registration_form"):

            name = st.text_input("Full Name")

            col1, col2 = st.columns(2)

            with col1:

                age = st.number_input(
                    "Age",
                    min_value=18,
                    max_value=100,
                    value=18
                )

                gender = st.selectbox(
                    "Gender",
                    ["Male", "Female", "Other"]
                )

                blood_group = st.selectbox(
                    "Blood Group",
                    [
                        "A+", "A-", "B+", "B-",
                        "AB+", "AB-", "O+", "O-"
                    ]
                )

            with col2:

                phone = st.text_input("Phone Number")
                city = st.text_input("City")

                last_donation = st.date_input(
                    "Last Donation Date",
                    value=date.today()
                )

            st.info("New donor profile is marked Available by default. You can change it later.")
            submit = st.form_submit_button("Register Donor")

            if submit:

                if not name or not phone or not city:

                    st.warning("Please fill all fields.")

                elif not phone.isdigit() or len(phone) != 10:

                    st.warning("Enter a valid 10-digit phone number.")

                else:

                    conn = get_connection()

                    conn.execute("""
                        INSERT INTO donors
                        (name, age, gender, blood_group, phone, city, last_donation, availability, username)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'Available', ?)
                    """, (
                        name,
                        age,
                        gender,
                        blood_group,
                        phone,
                        city,
                        str(last_donation),
                        st.session_state.username
                    ))

                    conn.commit()
                    conn.close()

                    st.success("Donor Registered Successfully!")


# ================= SEARCH DONORS =================

elif menu == "Search Donors":

    st.markdown(
        '<p class="section-title">🔍 Find Blood Donors</p>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        search_group = st.selectbox(
            "Blood Group",
            [
                "All",
                "A+", "A-", "B+", "B-",
                "AB+", "AB-", "O+", "O-"
            ]
        )

    with col2:

        search_city = st.text_input("City")

    search_name = st.text_input("Donor Name")

    if st.button("Search Donors"):

        conn = get_connection()

        query = """
            SELECT name, blood_group, city
            FROM donors
            WHERE COALESCE(availability, 'Available')='Available'
        """

        params = []

        if search_group != "All":

            query += " AND blood_group=?"
            params.append(search_group)

        if search_city:

            query += " AND city LIKE ?"
            params.append("%" + search_city + "%")

        if search_name:

            query += " AND name LIKE ?"
            params.append("%" + search_name + "%")

        df = pd.read_sql_query(
            query,
            conn,
            params=params
        )

        conn.close()

        if not df.empty:

            st.success(f"{len(df)} donor(s) found.")

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.warning("No donors found.")



# ================= DONOR AVAILABILITY =================

elif menu == "Donor Availability":

    st.markdown('<p class="section-title">🟢 Donor Availability</p>', unsafe_allow_html=True)

    if not st.session_state.user_logged_in:
        st.warning("Please login first.")
    else:
        conn = get_connection()
        mine = conn.execute("SELECT id, name, blood_group, city, COALESCE(availability,'Available') AS availability FROM donors WHERE username=? ORDER BY id DESC", (st.session_state.username,)).fetchall()
        if not mine:
            st.info("Aapka donor profile nahi mila. Pehle Donor Registration complete karein.")
        else:
            selected = st.selectbox("Choose your donor profile", [r["id"] for r in mine], format_func=lambda did: next(f'{r["name"]} | {r["blood_group"]} | {r["city"]}' for r in mine if r["id"] == did))
            current = next(r["availability"] for r in mine if r["id"] == selected)
            new_status = st.radio("Availability status", ["Available", "Unavailable"], index=0 if current == "Available" else 1, horizontal=True)
            if st.button("Update Availability", key="update_my_availability"):
                conn.execute("UPDATE donors SET availability=? WHERE id=? AND username=?", (new_status, selected, st.session_state.username))
                conn.commit()
                st.success("Availability updated successfully!")
                st.rerun()
        conn.close()


# ================= EMERGENCY BLOOD REQUEST =================

elif menu == "Emergency Blood Request":

    st.markdown('<p class="section-title">🚨 Emergency Blood Request</p>', unsafe_allow_html=True)
    st.warning("Submit only genuine requests. The system does not medically verify requests or guarantee blood availability.")
    if not st.session_state.user_logged_in:
        st.warning("Please login first to submit a request.")
    else:
        with st.form("emergency_request_form"):
            patient_name = st.text_input("Patient Name")
            group = st.selectbox("Required Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
            units = st.number_input("Units required", min_value=1, max_value=10, value=1)
            hospital = st.text_input("Hospital / Blood Bank Name")
            city = st.text_input("City")
            required_date = st.date_input("Required date", min_value=date.today())
            urgency = st.selectbox("Urgency", ["Normal", "Urgent", "Emergency"])
            notes = st.text_area("Additional details (optional; do not enter sensitive medical details)")
            submit_request = st.form_submit_button("Submit Blood Request")
        if submit_request:
            if not patient_name.strip() or not hospital.strip() or not city.strip():
                st.error("Patient name, hospital name and city are required.")
            else:
                conn = get_connection()
                try:
                    # Some older databases require requester_username instead of username.
                    schema_cursor = conn.execute("PRAGMA table_info(blood_requests)")
                    available_columns = {row[1] for row in schema_cursor.fetchall()}
                    request_values = {
                        "username": st.session_state.username,
                        "requester_username": st.session_state.username,
                        "patient_name": patient_name.strip(),
                        "blood_group": group,
                        "units": int(units),
                        "hospital": hospital.strip(),
                        "city": city.strip(),
                        "required_date": str(required_date),
                        "urgency": urgency,
                        "notes": notes.strip(),
                        "status": "Pending"
                    }
                    insert_columns = [
                        column for column in request_values
                        if column in available_columns
                    ]
                    placeholders = ",".join(["?"] * len(insert_columns))
                    column_sql = ",".join(insert_columns)
                    # Fill any legacy NOT NULL columns that this app version does not use.
                    # This keeps older SQLite table layouts compatible without deleting data.
                    table_info = conn.execute("PRAGMA table_info(blood_requests)").fetchall()
                    for column_info in table_info:
                        col_name = column_info[1]
                        not_null = bool(column_info[3])
                        default_value = column_info[4]
                        is_primary_key = bool(column_info[5])
                        if not_null and default_value is None and not is_primary_key and col_name not in request_values:
                            if col_name in ("username", "requester_username"):
                                request_values[col_name] = st.session_state.username
                            elif col_name in ("patient_name", "name"):
                                request_values[col_name] = patient_name.strip()
                            elif col_name in ("contact_phone", "phone"):
                                request_values[col_name] = "Not provided"
                            elif col_name in ("required_date", "needed_by"):
                                request_values[col_name] = str(required_date)
                            elif col_name in ("notes", "additional_details"):
                                request_values[col_name] = notes.strip()
                            elif col_name in ("created_at", "request_date"):
                                request_values[col_name] = datetime.now().isoformat(timespec="seconds")
                            elif col_name in ("status",):
                                request_values[col_name] = "Pending"
                            else:
                                request_values[col_name] = "Not provided"
                    insert_columns = [column for column in request_values if column in available_columns]
                    placeholders = ",".join(["?"] * len(insert_columns))
                    column_sql = ",".join(insert_columns)
                    values = [request_values[column] for column in insert_columns]
                    conn.execute(
                        f"INSERT INTO blood_requests ({column_sql}) VALUES ({placeholders})",
                        values
                    )
                    conn.commit()
                    st.success("Blood request submitted. Status: Pending admin review.")
                except sqlite3.Error as error:
                    conn.rollback()
                    st.error(f"Database error while saving request: {error}")
                finally:
                    conn.close()


# ================= MY BLOOD REQUESTS =================

elif menu == "My Blood Requests":

    st.markdown('<p class="section-title">📨 My Blood Requests</p>', unsafe_allow_html=True)
    if not st.session_state.user_logged_in:
        st.warning("Please login first.")
    else:
        conn = get_connection()
        requests_df = pd.read_sql_query("SELECT id,blood_group,units,hospital,city,required_date,urgency,status,created_at FROM blood_requests WHERE username=? ORDER BY id DESC", conn, params=(st.session_state.username,))
        conn.close()
        if requests_df.empty:
            st.info("You have not submitted any blood requests.")
        else:
            st.dataframe(requests_df, use_container_width=True, hide_index=True)


# ================= ADMIN REQUEST APPROVAL =================

elif menu == "Admin Manage Requests":

    st.markdown('<p class="section-title">🛡️ Admin - Manage Blood Requests</p>', unsafe_allow_html=True)
    if not st.session_state.admin_logged_in:
        st.warning("Admin login required.")
    else:
        conn = get_connection()
        req_df = pd.read_sql_query("SELECT id,username,blood_group,units,hospital,city,required_date,urgency,status,created_at FROM blood_requests ORDER BY id DESC", conn)
        if req_df.empty:
            st.info("No blood requests submitted yet.")
        else:
            st.dataframe(req_df, use_container_width=True, hide_index=True)
            request_id = st.selectbox("Select request ID", req_df["id"].tolist())
            new_status = st.selectbox("Set request status", ["Pending", "Approved", "Rejected", "Completed"])
            if st.button("Save Request Status", key="save_request_status"):
                conn.execute("UPDATE blood_requests SET status=? WHERE id=?", (new_status, request_id))
                conn.commit()
                st.success("Request status updated.")
                st.rerun()
            st.markdown("#### Download Request Report")
            req_csv = req_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Requests CSV", req_csv, "Blood_Requests_Report.csv", "text/csv", key="requests_csv")
            # Generate a simple PDF request report using already-installed ReportLab.
            pdf_buffer = BytesIO()
            pdf_doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
            pdf_styles = getSampleStyleSheet()
            pdf_elements = [Paragraph("Blood Request Report", pdf_styles["Title"]), Spacer(1, 12)]
            pdf_rows = [["ID", "Group", "Units", "City", "Date", "Urgency", "Status"]]
            for _, row in req_df.iterrows():
                pdf_rows.append([str(row["id"]), str(row["blood_group"]), str(row["units"]), str(row["city"]), str(row["required_date"]), str(row["urgency"]), str(row["status"])])
            pdf_table = Table(pdf_rows, repeatRows=1)
            pdf_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.darkred), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("ALIGN", (0,0), (-1,-1), "CENTER"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.lightgrey])]))
            pdf_elements.append(pdf_table)
            pdf_doc.build(pdf_elements)
            st.download_button("Download Requests PDF", pdf_buffer.getvalue(), "Blood_Requests_Report.pdf", "application/pdf", key="requests_pdf")
        conn.close()


# ================= DONOR REPORTS PDF + CSV =================

elif menu == "Donor Reports":

    st.markdown(
        '<p class="section-title">📄 Donor Reports</p>',
        unsafe_allow_html=True
    )

    if not st.session_state.admin_logged_in:

        st.warning("Admin login required to download reports.")

    else:

        conn = get_connection()

        df = pd.read_sql_query("""
            SELECT
                id,
                name,
                age,
                gender,
                blood_group,
                city,
                last_donation
            FROM donors
            ORDER BY id DESC
        """, conn)

        conn.close()

        st.metric("Total Donors", len(df))

        if not df.empty:

            st.subheader("Donor Records")

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            # CSV DOWNLOAD

            csv_data = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Download CSV Report",
                data=csv_data,
                file_name="Blood_Donors_Report.csv",
                mime="text/csv"
            )

            st.markdown("---")

            # PDF GENERATION

            st.subheader("📄 PDF Report")

            if st.button("Generate PDF Report"):

                buffer = BytesIO()

                document = SimpleDocTemplate(
                    buffer,
                    pagesize=landscape(A4)
                )

                styles = getSampleStyleSheet()

                elements = []

                elements.append(
                    Paragraph(
                        "Blood Donors Management System",
                        styles["Title"]
                    )
                )

                elements.append(Spacer(1, 15))

                elements.append(
                    Paragraph(
                        f"Total Registered Donors: {len(df)}",
                        styles["Heading2"]
                    )
                )

                elements.append(Spacer(1, 15))

                data = [[
                    "ID",
                    "Name",
                    "Age",
                    "Gender",
                    "Blood Group",
                    "City",
                    "Last Donation"
                ]]

                for _, row in df.iterrows():

                    data.append([
                        str(row["id"]),
                        str(row["name"] or ""),
                        str(row["age"] or ""),
                        str(row["gender"] or ""),
                        str(row["blood_group"] or ""),
                        str(row["city"] or ""),
                        str(row["last_donation"] or "")
                    ])

                table = Table(
                    data,
                    repeatRows=1
                )

                table.setStyle(TableStyle([
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.darkred
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),
                    (
                        "PADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.lightgrey]
                    )
                ]))

                elements.append(table)

                elements.append(Spacer(1, 20))

                elements.append(
                    Paragraph(
                        "Donate Blood - Save Lives",
                        styles["Italic"]
                    )
                )

                document.build(elements)

                pdf_data = buffer.getvalue()

                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_data,
                    file_name="Blood_Donors_Report.pdf",
                    mime="application/pdf",
                    key="download_pdf_report"
                )

        else:

            st.info("No donor records available.")


# ================= ALL DONORS =================

elif menu == "All Donors":

    st.markdown(
        '<p class="section-title">📋 All Registered Donors</p>',
        unsafe_allow_html=True
    )

    if not st.session_state.admin_logged_in:

        st.warning("Admin login required.")

    else:

        conn = get_connection()

        df = pd.read_sql_query(
            "SELECT * FROM donors ORDER BY id DESC",
            conn
        )

        conn.close()

        if not df.empty:

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info("No donors available.")


# ================= ADMIN LOGIN =================

elif menu == "Admin Login":

    st.markdown(
        '<p class="section-title">🔑 Administrator Login</p>',
        unsafe_allow_html=True
    )

    if st.session_state.admin_logged_in:

        st.success("Admin already logged in.")

    else:

        with st.form("admin_login_form"):

            admin_username = st.text_input("Admin Username")

            show_admin = st.checkbox("Show Admin Password")

            admin_password = st.text_input(
                "Admin Password",
                type="default" if show_admin else "password"
            )

            submit = st.form_submit_button("Admin Login")

            if submit:

                if admin_username == "admin" and admin_password == "admin123":

                    st.session_state.admin_logged_in = True

                    st.success("Admin Login Successful!")
                    st.rerun()

                else:

                    st.error("Invalid Admin Username or Password.")


# ================= ADMIN DASHBOARD =================

elif menu == "Admin Dashboard":

    st.markdown(
        '<p class="section-title">⚙️ Admin Dashboard</p>',
        unsafe_allow_html=True
    )

    if not st.session_state.admin_logged_in:

        st.warning("Please login as Admin.")

    else:

        conn = get_connection()

        total_donors = conn.execute(
            "SELECT COUNT(*) FROM donors"
        ).fetchone()[0]

        total_users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_cities = conn.execute(
            "SELECT COUNT(DISTINCT city) FROM donors"
        ).fetchone()[0]

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Donors", total_donors)
        c2.metric("Total Users", total_users)
        c3.metric("Total Cities", total_cities)

        st.markdown("---")

        st.subheader("Recent Donor Activity")

        recent = pd.read_sql_query("""
            SELECT
                id,
                name,
                blood_group,
                city,
                last_donation
            FROM donors
            ORDER BY id DESC
            LIMIT 10
        """, conn)

        conn.close()

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True
        )


# ================= UPDATE DONOR =================

elif menu == "Update Donor":

    st.markdown(
        '<p class="section-title">✏️ Update Donor Details</p>',
        unsafe_allow_html=True
    )

    if not st.session_state.admin_logged_in:

        st.warning("Admin login required.")

    else:

        conn = get_connection()

        donors = pd.read_sql_query(
            "SELECT * FROM donors",
            conn
        )

        if donors.empty:

            st.info("No donor records available.")

        else:

            donor_id = st.selectbox(
                "Select Donor ID",
                donors["id"].tolist()
            )

            donor = donors[
                donors["id"] == donor_id
            ].iloc[0]

            with st.form("update_donor_form"):

                name = st.text_input(
                    "Name",
                    value=str(donor["name"] or "")
                )

                try:
                    current_age = int(donor["age"] or 18)
                except (ValueError, TypeError):
                    current_age = 18

                age = st.number_input(
                    "Age",
                    min_value=18,
                    max_value=100,
                    value=max(18, min(100, current_age))
                )

                genders = ["Male", "Female", "Other"]

                gender = st.selectbox(
                    "Gender",
                    genders,
                    index=genders.index(donor["gender"])
                    if donor["gender"] in genders else 0
                )

                groups = [
                    "A+", "A-", "B+", "B-",
                    "AB+", "AB-", "O+", "O-"
                ]

                blood_group = st.selectbox(
                    "Blood Group",
                    groups,
                    index=groups.index(donor["blood_group"])
                    if donor["blood_group"] in groups else 0
                )

                phone = st.text_input(
                    "Phone",
                    value=str(donor["phone"] or "")
                )

                city = st.text_input(
                    "City",
                    value=str(donor["city"] or "")
                )

                last_donation = st.text_input(
                    "Last Donation",
                    value=str(donor["last_donation"] or "")
                )
                availability_options = ["Available", "Unavailable"]
                current_availability = str(donor.get("availability", "Available") or "Available")
                availability = st.selectbox("Availability", availability_options, index=0 if current_availability == "Available" else 1)

                submit = st.form_submit_button("Save Changes")

                if submit:

                    if not name or not phone or not city:

                        st.warning("Please fill all fields.")

                    elif not phone.isdigit() or len(phone) != 10:

                        st.warning("Enter a valid 10-digit phone number.")

                    else:

                        conn.execute("""
                            UPDATE donors
                            SET name=?, age=?, gender=?, blood_group=?,
                                phone=?, city=?, last_donation=?, availability=?
                            WHERE id=?
                        """, (
                            name,
                            age,
                            gender,
                            blood_group,
                            phone,
                            city,
                            last_donation,
                            availability,
                            donor_id
                        ))

                        conn.commit()

                        st.success("Donor Updated Successfully!")

        conn.close()


# ================= DELETE DONOR =================

elif menu == "Delete Donor":

    st.markdown(
        '<p class="section-title">🗑️ Delete Donor</p>',
        unsafe_allow_html=True
    )

    if not st.session_state.admin_logged_in:

        st.warning("Admin login required.")

    else:

        conn = get_connection()

        donors = pd.read_sql_query("""
            SELECT id, name, blood_group, city
            FROM donors
        """, conn)

        if donors.empty:

            st.info("No donors available.")
            conn.close()

        else:

            st.dataframe(
                donors,
                use_container_width=True,
                hide_index=True
            )

            donor_id = st.selectbox(
                "Select Donor ID",
                donors["id"].tolist()
            )

            confirm = st.checkbox(
                "Confirm donor deletion"
            )

            if st.button("Delete Donor"):

                if confirm:

                    conn.execute(
                        "DELETE FROM donors WHERE id=?",
                        (donor_id,)
                    )

                    conn.commit()
                    conn.close()

                    st.success("Donor Deleted Successfully!")
                    st.rerun()

                else:

                    conn.close()
                    st.warning("Please confirm deletion.")

            else:
                conn.close()


# ================= LOGOUT =================

elif menu == "Logout":

    st.session_state.user_logged_in = False
    st.session_state.admin_logged_in = False
    st.session_state.username = ""

    st.success("Logged Out Successfully!")


# ================= FOOTER =================

st.markdown("---")

st.markdown("""
<div class="footer">
    <h3>🩸 Blood Donors Management System</h3>
    <p>Donate Blood | Save Lives | Help Humanity</p>
    <p>Developed with Python, Streamlit, SQLite and Plotly</p>
</div>
""", unsafe_allow_html=True)