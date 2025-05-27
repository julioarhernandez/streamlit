import streamlit as st
import pandas as pd
import datetime
import io
from config import setup_page, db
from utils import load_students

# Setup page
setup_page("Attendance Management")

def save_attendance(date, attendance_data):
    """Save attendance data to Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        date_str = date.strftime('%Y-%m-%d')
        db.child("attendance").child(user_email).child(date_str).set(attendance_data)
        return True
    except Exception as e:
        st.error(f"Error saving attendance: {str(e)}")
        return False

def load_attendance(date):
    """Load attendance data from Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        date_str = date.strftime('%Y-%m-%d')
        data = db.child("attendance").child(user_email).child(date_str).get().val()
        return data or {}
    except Exception as e:
        st.error(f"Error loading attendance: {str(e)}")
        return {}

def parse_attendance_report(file_content_str):
    lines = file_content_str.splitlines()
    participants_section_lines = []
    in_participants_section = False

    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("2. Participants"):
            in_participants_section = True
            continue  # Skip the "2. Participants" line itself
        if line_stripped.startswith("3. In-Meeting Activities"):
            in_participants_section = False
            break  # End of section
        
        if in_participants_section and line_stripped:  # Collect non-empty lines within the section
            participants_section_lines.append(line)
            
    if not participants_section_lines:
        print("Warning: '2. Participants' section is empty or not found in report.")
        return []

    csv_like_data = "\n".join(participants_section_lines)
    
    try:
        df = pd.read_csv(io.StringIO(csv_like_data), sep='\t')
        if "Name" in df.columns:
            return df["Name"].astype(str).str.strip().unique().tolist()
        else:
            print("Warning: Could not find 'Name' column in '2. Participants' section of report.")
            return []
    except pd.errors.EmptyDataError:
        print("Warning: No data rows found in '2. Participants' section of report after parsing.")
        return []
    except Exception as e:
        print(f"Error parsing '2. Participants' section of report: {e}")
        return []

# Main UI
st.header("Record Attendance")

# Date selector
today = datetime.date.today()
selected_date = st.date_input("Select Date", today)

# Load students to mark attendance
students_df, _ = load_students()

if students_df is not None and not students_df.empty:
    # Normalize column names (convert to lowercase)
    students_df.columns = students_df.columns.str.lower()
    
    # Check for required columns
    required_columns = {'nombre'}
    missing_columns = required_columns - set(students_df.columns)
    
    if missing_columns:
        st.error(f"Error: Missing required columns in students data: {', '.join(missing_columns)}")
    else:
        attendance_data = load_attendance(selected_date)
        present_from_reports = set()

        st.subheader("Upload Attendance Reports (Optional)")
        uploaded_reports = st.file_uploader(
            "Upload meeting attendance CSV report(s) to auto-fill 'Present'/'Absent'",
            type=['csv'],
            accept_multiple_files=True,
            key=f"report_uploader_{selected_date.strftime('%Y%m%d')}",
            help="Upload CSV files from meetings. The system extracts names from '2. Participants' section."
        )

        if uploaded_reports:
            processed_files_count = 0
            with st.spinner("Processing attendance reports..."):
                for report_file in uploaded_reports:
                    try:
                        file_bytes = report_file.getvalue()
                        file_content = None
                        encodings_to_try = ['utf-16', 'utf-8', 'utf-8-sig', 'latin-1']

                        for encoding in encodings_to_try:
                            try:
                                file_content = file_bytes.decode(encoding)
                                # Optional: st.info(f"Successfully decoded {report_file.name} with {encoding}")
                                break  # Decoded successfully
                            except UnicodeDecodeError:
                                continue # Try next encoding
                        
                        if file_content is None:
                            st.error(f"Failed to decode {report_file.name}. Tried encodings: {', '.join(encodings_to_try)}. Please ensure the file is saved with a compatible text encoding.")
                            continue # Skip to the next file

                        names_from_report = parse_attendance_report(file_content)
                        if names_from_report:
                            present_from_reports.update(names_from_report)
                            processed_files_count += 1
                        else:
                            st.warning(f"Could not extract participant names from {report_file.name}. Check format or content of '2. Participants' section.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred while processing file {report_file.name}: {e}")
            
            if processed_files_count > 0:
                st.success(f"Processed {processed_files_count} report(s). Found {len(present_from_reports)} unique attendees. Form updated.")
            elif uploaded_reports:
                 st.warning("No attendees extracted from uploaded report(s). Check file format/content.")

        # Initialize/update attendance data for all students in the master list
        for _, student in students_df.iterrows():
            student_name_key = str(student['nombre']).strip()

            if student_name_key not in attendance_data:
                attendance_data[student_name_key] = {
                    'name': student_name_key,
                    'status': 'present', 
                    'notes': ''
                }
            else:
                attendance_data[student_name_key]['name'] = student_name_key

            if present_from_reports: # If reports were processed
                if student_name_key in present_from_reports:
                    attendance_data[student_name_key]['status'] = 'present'
                else:
                    attendance_data[student_name_key]['status'] = 'absent'
        
        st.subheader(f"Attendance for {selected_date.strftime('%B %d, %Y')}")
        
        with st.form("attendance_form"):
            cols = st.columns([3, 2, 4])
            cols[0].write("**Student**")
            cols[1].write("**Status**")
            cols[2].write("**Notes**")
            
            sorted_student_names = sorted(attendance_data.keys())
            for student_id in sorted_student_names: # student_id is student_name_key
                data = attendance_data[student_id]
                cols = st.columns([3, 2, 4])
                cols[0].write(data['name'])
                current_status_index = ["Present", "Absent", "Late", "Excused"].index(data.get('status', 'present').title())
                status = cols[1].selectbox(
                    f"Status_{student_id}",
                    ["Present", "Absent", "Late", "Excused"],
                    key=f"status_{student_id}_{selected_date.strftime('%Y%m%d')}", # UPDATED KEY
                    index=current_status_index
                )
                notes = cols[2].text_input(
                    "Notes",
                    value=data.get('notes', ''),
                    key=f"notes_{student_id}_{selected_date.strftime('%Y%m%d')}", # UPDATED KEY
                    label_visibility="collapsed"
                )
                
                attendance_data[student_id] = {
                    'name': data['name'],
                    'status': status.lower(),
                    'notes': notes
                }
            
            submitted = st.form_submit_button("Save Attendance")
            if submitted:
                if save_attendance(selected_date, attendance_data):
                    st.success("Attendance saved successfully!")

else:
    st.warning("Please add students first in the Students page.")

# View attendance records
st.header("View Attendance Records")

start_date = st.date_input("Start Date", today - datetime.timedelta(days=7))
end_date = st.date_input("End Date", today)

if st.button("View Records"):
    records = {}
    current_date = start_date
    
    with st.spinner("Loading attendance records..."):
        while current_date <= end_date:
            date_attendance = load_attendance(current_date)
            if date_attendance:
                records[current_date.strftime('%Y-%m-%d')] = date_attendance
            current_date += datetime.timedelta(days=1)
    
    if records:
        st.subheader(f"Attendance from {start_date} to {end_date}")
        
        # Convert to DataFrame for display
        data = []
        for date, attendance in records.items():
            for student_id, details in attendance.items():
                data.append({
                    'Date': date,
                    'Student ID': student_id,
                    'Name': details['name'],
                    'Status': details['status'].title(),
                    'Notes': details.get('notes', '')
                })
        
        df = pd.DataFrame(data)
        st.dataframe(df)
        
        # Export button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"attendance_{start_date}_to_{end_date}.csv",
            mime='text/csv',
        )
    else:
        st.info("No attendance records found for the selected date range.")
