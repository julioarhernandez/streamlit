import streamlit as st
import pandas as pd
import datetime
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
        # Create attendance form
        attendance_data = load_attendance(selected_date)
        
        # Initialize attendance data if not exists
        for _, student in students_df.iterrows():
            student_id = str(student['nombre'])
            if student_id not in attendance_data:
                attendance_data[student_id] = {
                    'name': f"{student['nombre']}".strip(),
                    'status': 'present',
                    'notes': ''
                }
        
        # Display attendance form
        st.subheader(f"Attendance for {selected_date.strftime('%B %d, %Y')}")
        
        # Create a form for attendance
        with st.form("attendance_form"):
            # Create headers
            cols = st.columns([3, 2, 4])
            cols[0].write("**Student**")
            cols[1].write("**Status**")
            cols[2].write("**Notes**")
            
            # Create form fields for each student
            for student_id, data in attendance_data.items():
                cols = st.columns([3, 2, 4])
                cols[0].write(data['name'])
                status = cols[1].selectbox(
                    f"Status_{student_id}",
                    ["Present", "Absent", "Late", "Excused"],
                    key=f"status_{student_id}_{selected_date}",
                    index=["Present", "Absent", "Late", "Excused"].index(data.get('status', 'Present').title())
                )
                notes = cols[2].text_input(
                    "Notes",
                    value=data.get('notes', ''),
                    key=f"notes_{student_id}_{selected_date}",
                    label_visibility="collapsed"
                )
                
                # Update attendance data
                attendance_data[student_id] = {
                    'name': data['name'],
                    'status': status.lower(),
                    'notes': notes
                }
            
            # Add submit button
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
