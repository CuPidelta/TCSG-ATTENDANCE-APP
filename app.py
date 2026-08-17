import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io
import base64
from pathlib import Path
import textwrap

st.set_page_config(
    page_title="TCSG Scholar Attendance",
    page_icon="assets/tcsg_logo.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)


LOGO_PATH = Path(__file__).parent / "assets" / "tcsg_logo.jpg"

@st.cache_data
def get_logo_b64():
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return ""

logo_b64 = get_logo_b64()
logo_src = f"data:image/jpeg;base64,{logo_b64}" if logo_b64 else ""

NAVY = "#1e3a72"
NAVY_DARK = "#142a56"
GOLD = "#f5a623"
GOLD_LIGHT = "#fdf3e0"
SLATE = "#64748b"
INK = "#0f172a"
BG = "#f7f8fb"
GREEN = "#16a34a"
GREEN_LIGHT = "#dcfce7"
AMBER_TEXT = "#92400e"

# ---------------------------------------------------------
# GLOBAL CSS
# ---------------------------------------------------------
CSS_PATH = Path(__file__).parent / "assets" / "style.css"

def load_css(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

st.markdown(f"""<style>
{load_css(CSS_PATH)}

/* Base text color for sidebar text/labels only (not inputs) */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div:not([data-baseweb="select"]) {{
    color: #e8edf7;
}}

/* Sidebar Selectbox Container (Navy Blue) */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
    background-color: #1e3a72 !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 8px !important;
}}

/* FIX: Force Text inside Selectbox Input to be Crisp Bold White */
section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="button"],
section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] input {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 600 !important;
}}

/* Arrow dropdown icon color */
section[data-testid="stSidebar"] div[data-baseweb="select"] svg {{
    fill: #ffffff !important;
}}

/* Sidebar Textarea & Text Input */
section[data-testid="stSidebar"] .stTextArea textarea,
section[data-testid="stSidebar"] .stTextInput input {{
    background-color: #22366b !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}}

/* Expander Header styling in Sidebar */
section[data-testid="stSidebar"] div[data-testid="stExpander"] details summary span {{
    color: #ffffff !important;
}}

section[data-testid="stSidebar"] div[data-testid="stExpander"] details summary svg {{
    fill: #ffffff !important;
}}

/* Dropdown Popup Menu List Options */
ul[data-baseweb="menu"] {{
    background-color: #1e3a72 !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 8px !important;
}}

ul[data-baseweb="menu"] li,
ul[data-baseweb="menu"] li * {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    background-color: transparent !important;
    font-weight: 500 !important;
}}

/* Hover state on dropdown options */
ul[data-baseweb="menu"] li:hover,
ul[data-baseweb="menu"] li:hover * {{
    background-color: #142a56 !important;
    color: #f5a623 !important;
    -webkit-text-fill-color: #f5a623 !important;
}}
</style>""", unsafe_allow_html=True)

def icon(name, size="1em", color="inherit"):
    return f'<i class="bi bi-{name}" style="font-size:{size}; color:{color};"></i>'

def empty_state(icon_name, title, subtitle=""):
    st.markdown(textwrap.dedent(f"""
        <div class="empty-state">
            {icon(icon_name, "2rem")}
            <div style="font-weight:700; color:{INK};">{title}</div>
            <div style="font-size:0.85rem;">{subtitle}</div>
        </div>
    """).strip(), unsafe_allow_html=True)


DB_FILE = "scholars_attendance.db"
INITIAL_REQUIRED_HOURS = 32.0

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scholars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT UNIQUE NOT NULL,
            cluster TEXT DEFAULT 'Cluster 1',
            total_rendered REAL DEFAULT 0.0,
            remaining_hours REAL DEFAULT 32.0,
            status TEXT DEFAULT 'In Progress',
            is_deleted INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT NOT NULL,
            student_name TEXT NOT NULL,
            rendered_hours REAL NOT NULL,
            activity_name TEXT,
            logged_at TEXT NOT NULL
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE scholars ADD COLUMN cluster TEXT DEFAULT 'Cluster 1'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE scholars ADD COLUMN is_deleted INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

def load_scholars():
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT id, student_name, cluster, total_rendered, remaining_hours, status FROM scholars WHERE is_deleted = 0 ORDER BY student_name ASC", 
        conn
    )
    conn.close()
    return df

def load_logs():
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT event_date, student_name, rendered_hours, activity_name, logged_at FROM attendance_logs ORDER BY id DESC", 
        conn
    )
    conn.close()
    return df

st.markdown(textwrap.dedent(f"""
    <div class="tcsg-banner">
        <img src="{logo_src}" alt="TCSG Logo" />
        <div class="tcsg-banner-text">
            <h1>TCSG Scholar Attendance & Hours Tracker</h1>
            <p>Tagum City Scholars Guild &middot; Systematic tracking and automated deduction of community service hours</p>
        </div>
    </div>
""").strip(), unsafe_allow_html=True)


with st.sidebar:
    if logo_src:
        st.markdown(textwrap.dedent(f"""
            <div class="sidebar-logo-wrap">
                <img src="{logo_src}" alt="TCSG Logo" />
            </div>
        """).strip(), unsafe_allow_html=True)

    st.markdown(f'<div class="sidebar-heading">{icon("gear-fill", "1.05rem", GOLD)} Administration</div>', unsafe_allow_html=True)

    # ADD SCHOLAR
    with st.expander("Add New Scholars", icon=":material/person_add:", expanded=False):
        selected_cluster = st.selectbox(
            "Select Cluster:",
            [f"Cluster {i}" for i in range(1, 6)],
            key="add_cluster_select"
        )
        new_names_input = st.text_area(
            "Names (one per line):", height=100,
            placeholder=""
        )
        if st.button("Register Scholars", use_container_width=True):
            if new_names_input.strip():
                names = [name.strip() for name in new_names_input.split("\n") if name.strip()]
                conn = get_db_connection()
                cursor = conn.cursor()
                added, skipped = 0, 0
                for name in names:
                    try:
                        cursor.execute(
                            "INSERT INTO scholars (student_name, cluster, total_rendered, remaining_hours, status, is_deleted) VALUES (?, ?, 0.0, ?, 'In Progress', 0)",
                            (name, selected_cluster, INITIAL_REQUIRED_HOURS)
                        )
                        added += 1
                    except sqlite3.IntegrityError:
                        cursor.execute(
                            "UPDATE scholars SET cluster = ?, is_deleted = 0 WHERE student_name = ?",
                            (selected_cluster, name)
                        )
                        if cursor.rowcount > 0:
                            added += 1
                        else:
                            skipped += 1
                conn.commit()
                conn.close()
                if added:
                    st.success(f"Added/Restored {added} scholar(s) to {selected_cluster}.")
                if skipped:
                    st.warning(f"Skipped {skipped} duplicate(s).")
                st.rerun()
            else:
                st.error("Enter at least one name first.")

    # EDIT SCHOLAR
    with st.expander("Edit Scholar Info", icon=":material/edit:", expanded=True):
        scholars_df = load_scholars()
        if not scholars_df.empty:
            scholar_list = scholars_df["student_name"].tolist()
            selected_scholar_to_edit = st.selectbox("Select Scholar to Edit:", scholar_list, key="edit_scholar_select")
            
            current_row = scholars_df[scholars_df["student_name"] == selected_scholar_to_edit].iloc[0]
            current_cluster = current_row["cluster"]
            
            cluster_options = [f"Cluster {i}" for i in range(1, 6)]
            default_cluster_idx = cluster_options.index(current_cluster) if current_cluster in cluster_options else 0
            
            edited_name = st.text_input("Scholar Name:", value=selected_scholar_to_edit)
            edited_cluster = st.selectbox("Scholar Cluster:", cluster_options, index=default_cluster_idx, key="edit_cluster_select")
            
            if st.button("Save Changes", use_container_width=True, type="primary"):
                if edited_name.strip():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "UPDATE scholars SET student_name = ?, cluster = ? WHERE id = ?",
                            (edited_name.strip(), edited_cluster, current_row["id"])
                        )
                        cursor.execute(
                            "UPDATE attendance_logs SET student_name = ? WHERE student_name = ?",
                            (edited_name.strip(), selected_scholar_to_edit)
                        )
                        conn.commit()
                        st.success("Scholar information updated successfully!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Scholar name already exists.")
                    finally:
                        conn.close()
                else:
                    st.error("Name cannot be empty.")
        else:
            empty_state("inbox", "No scholars yet", "Add scholars to enable editing.")

    # DELETE SCHOLAR (Soft Delete)
    with st.expander("Delete Scholar", icon=":material/person_remove:", expanded=False):
        if not scholars_df.empty:
            scholar_to_delete = st.selectbox("Select Scholar to Remove:", scholars_df["student_name"].tolist(), key="delete_scholar_select")
            confirm_delete = st.checkbox("Confirm deletion")
            if st.button("Delete Scholar Record", type="primary", use_container_width=True, disabled=not confirm_delete):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE scholars SET is_deleted = 1 WHERE student_name = ?", (scholar_to_delete,))
                conn.commit()
                conn.close()
                st.success(f"Removed {scholar_to_delete}.")
                st.rerun()
        else:
            empty_state("inbox", "No scholars yet", "Add your first scholar above.")

tab_entry, tab_dashboard, tab_logs = st.tabs([
    "Batch Hours Entry",
    "Scholar Dashboard",
    "Attendance Logs"
])

with tab_entry:
    st.markdown(f'<div class="section-label">{icon("clock-history", "1.1rem", NAVY)} Log Community Service Hours</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Paste a batch of scholar names and apply hours to all of them at once.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1.2, 1], gap="medium")

    with col1:
        pasted_names = st.text_area(
            "Paste Scholar Names (one per line):",
            height=200,
            placeholder=""
        )

    with col2:
        event_date = st.date_input("Event / Service Date:", value=date.today())
        hours_to_add = st.number_input("Hours Rendered:", min_value=0.5, max_value=32.0, step=0.5, value=1.0)
        activity_name = st.text_input("Activity Title:", value="Community Service")

        st.markdown("<br>", unsafe_allow_html=True)
        submit_btn = st.button("Apply Rendered Hours", type="primary", use_container_width=True, icon=":material/task_alt:")

    if submit_btn:
        if pasted_names.strip():
            input_names = [n.strip().lower() for n in pasted_names.split("\n") if n.strip()]

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id, student_name, total_rendered, remaining_hours FROM scholars WHERE is_deleted = 0")
            all_scholars = cursor.fetchall()

            matched_count = 0
            not_found = []

            db_map = {s["student_name"].lower(): s for s in all_scholars}

            with st.spinner("Applying hours..."):
                for input_name in input_names:
                    if input_name in db_map:
                        scholar = db_map[input_name]
                        new_rendered = scholar["total_rendered"] + hours_to_add
                        new_remaining = max(0.0, INITIAL_REQUIRED_HOURS - new_rendered)
                        new_status = "Completed" if new_remaining == 0 else "In Progress"

                        cursor.execute("""
                            UPDATE scholars
                            SET total_rendered = ?, remaining_hours = ?, status = ?
                            WHERE id = ?
                        """, (new_rendered, new_remaining, new_status, scholar["id"]))

                        cursor.execute("""
                            INSERT INTO attendance_logs (event_date, student_name, rendered_hours, activity_name, logged_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            event_date.strftime("%Y-%m-%d"),
                            scholar["student_name"],
                            hours_to_add,
                            activity_name,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))

                        matched_count += 1
                    else:
                        not_found.append(input_name)

                conn.commit()
                conn.close()

            if matched_count > 0:
                st.success(f"Successfully processed {matched_count} record(s).")
            if not_found:
                st.warning(f"Names not recognized or deleted: {', '.join(not_found)}")

            st.rerun()
        else:
            st.error("Please enter at least one scholar name.")


with tab_dashboard:
    df_scholars = load_scholars()

    if not df_scholars.empty:
        total_scholars = len(df_scholars)
        completed_scholars = len(df_scholars[df_scholars["remaining_hours"] == 0])
        in_progress_scholars = total_scholars - completed_scholars

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(textwrap.dedent(f"""
                <div class="metric-card">
                    <div class="metric-icon">{icon("people-fill")}</div>
                    <div>
                        <div class="metric-title">Total Enrolled</div>
                        <div class="metric-value">{total_scholars}</div>
                    </div>
                </div>
            """).strip(), unsafe_allow_html=True)
        with m2:
            st.markdown(textwrap.dedent(f"""
                <div class="metric-card green">
                    <div class="metric-icon">{icon("check-circle-fill")}</div>
                    <div>
                        <div class="metric-title">Service Completed</div>
                        <div class="metric-value">{completed_scholars}</div>
                    </div>
                </div>
            """).strip(), unsafe_allow_html=True)
        with m3:
            st.markdown(textwrap.dedent(f"""
                <div class="metric-card gold">
                    <div class="metric-icon">{icon("hourglass-split")}</div>
                    <div>
                        <div class="metric-title">In Progress</div>
                        <div class="metric-value">{in_progress_scholars}</div>
                    </div>
                </div>
            """).strip(), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
        with fcol1:
            search_query = st.text_input(
                "Search Scholar Name:", placeholder="Type to filter...",
                label_visibility="collapsed", icon=":material/search:"
            )
        with fcol2:
            cluster_filter = st.selectbox(
                "Filter by Cluster:",
                ["All Clusters"] + [f"Cluster {i}" for i in range(1, 6)],
                label_visibility="collapsed"
            )
        with fcol3:
            status_filter = st.selectbox(
                "Filter by status:",
                ["All Statuses", "In Progress", "Completed"],
                label_visibility="collapsed"
            )

        display_df = df_scholars.copy()
        if search_query:
            display_df = display_df[display_df["student_name"].str.contains(search_query, case=False, na=False)]
        if cluster_filter != "All Clusters":
            display_df = display_df[display_df["cluster"] == cluster_filter]
        if status_filter != "All Statuses":
            display_df = display_df[display_df["status"] == status_filter]

        display_df = display_df.rename(columns={
            "id": "ID",
            "student_name": "Student Name",
            "cluster": "Cluster",
            "total_rendered": "Total Rendered (Hrs)",
            "remaining_hours": "Remaining Hours",
            "status": "Status"
        })

        if display_df.empty:
            empty_state("search", "No matching scholars", "Try a different name or filter.")
        else:
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Total Rendered (Hrs)": st.column_config.ProgressColumn(
                        "Progress", min_value=0, max_value=INITIAL_REQUIRED_HOURS,
                        format="%.1f hrs"
                    ),
                    "Remaining Hours": st.column_config.NumberColumn(format="%.1f hrs"),
                    "Cluster": st.column_config.TextColumn(),
                    "Status": st.column_config.TextColumn(),
                }
            )

        st.markdown("<br>", unsafe_allow_html=True)

        df_logs = load_logs()
        buffer = io.BytesIO()
        
        excel_scholars_df = df_scholars.rename(columns={
            "id": "ID",
            "student_name": "Student Name",
            "cluster": "Cluster",
            "total_rendered": "Total Rendered (Hrs)",
            "remaining_hours": "Remaining Hours",
            "status": "Status"
        })

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            excel_scholars_df.to_excel(writer, sheet_name="Scholars Summary", index=False)
            df_logs.to_excel(writer, sheet_name="Attendance Logs", index=False)

        st.download_button(
            label="Download Master Report (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"Scholar_Attendance_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
            icon=":material/download:"
        )
    else:
        empty_state("people", "No scholar records found", "Add scholars using the Administration panel in the sidebar.")

with tab_logs:
    st.markdown(f'<div class="section-label">{icon("journal-text", "1.1rem", NAVY)} Transaction History</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Full chronological record of every hours-logging transaction.</div>', unsafe_allow_html=True)

    df_logs = load_logs()

    if not df_logs.empty:
        log_search = st.text_input(
            "Search logs:", placeholder="Filter by scholar name...",
            label_visibility="collapsed", icon=":material/search:"
        )
        display_logs = df_logs.copy()
        if log_search:
            display_logs = display_logs[display_logs["student_name"].str.contains(log_search, case=False, na=False)]

        st.dataframe(
            display_logs.rename(columns={
                "event_date": "Service Date",
                "student_name": "Student Name",
                "rendered_hours": "Rendered (Hrs)",
                "activity_name": "Activity Title",
                "logged_at": "Logged Timestamp"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        empty_state("journal-x", "No transaction logs yet", "Logs will appear here once hours are recorded.")