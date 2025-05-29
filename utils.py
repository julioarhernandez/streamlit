# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\utils.py
import streamlit as st
import pandas as pd
from config import db # Assuming db is your Firebase Realtime Database reference from config.py
import datetime # Added for type hinting and date operations

def load_students():
    """Load students data from Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        data = db.child("students").child(user_email).get().val()
        if data and 'data' in data:
            df = pd.DataFrame(data['data'])
            # Normalize column names
            df.columns = df.columns.str.lower().str.strip() # Added strip here too
            # Ensure 'id' column is string and other required columns are present and stripped
            if 'nombre' in df.columns: # Assuming 'nombre' is the primary identifier now
                df['nombre'] = df['nombre'].astype(str).str.strip()
            # Add similar cleaning for other columns if they become critical again
            return df, data.get('filename', 'students.xlsx')
        return None, None
    except Exception as e:
        st.error(f"Error loading students: {str(e)}")
        return None, None

def save_students(students_df):
    """Save students data to Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        # Ensure column names are strings before saving to_dict('records')
        students_df.columns = students_df.columns.astype(str)
        data = {
            'filename': 'students.xlsx', # Or derive from an uploaded filename if relevant
            'data': students_df.to_dict('records'),
            'timestamp': pd.Timestamp.now(tz='UTC').isoformat() # Use timezone-aware timestamp
        }
        db.child("students").child(user_email).set(data)
        return True
    except Exception as e:
        st.error(f"Error saving students: {str(e)}")
        return False

# --- Functions moved from 2_Attendance.py ---
def save_attendance(date: datetime.date, attendance_data: dict):
    """Save attendance data to Firebase for a specific date."""
    try:
        user_email = st.session_state.email.replace('.', ',')
        date_str = date.strftime('%Y-%m-%d')
        # Ensure student names (keys in attendance_data) are safe for Firebase paths if necessary
        # For now, assuming they are simple strings.
        db.child("attendance").child(user_email).child(date_str).set(attendance_data)
        return True
    except Exception as e:
        st.error(f"Error saving attendance for {date_str}: {str(e)}")
        return False

def load_attendance(date: datetime.date) -> dict:
    """Load attendance data from Firebase for a specific date."""
    try:
        user_email = st.session_state.email.replace('.', ',')
        date_str = date.strftime('%Y-%m-%d')
        raw_data = db.child("attendance").child(user_email).child(date_str).get().val()
        
        if isinstance(raw_data, list):
            # Convert list of records to a dictionary keyed by student name
            processed_data = {}
            for record in raw_data:
                if isinstance(record, dict) and 'Nombre' in record:
                    # Ensure we don't overwrite if names aren't unique, though they should be per day
                    processed_data[record['Nombre']] = record 
                # else: st.warning(f"Skipping invalid record in list for {date_str}: {record}") # Optional: log bad records
            return processed_data
        elif isinstance(raw_data, dict):
            # If it's already a dict (e.g., older data or different save format), return as is
            return raw_data
        else:
            # No data or unexpected type
            return {}
            
    except Exception as e:
        st.error(f"Error loading attendance for {date_str}: {str(e)}")
        return {}

# --- Module Management Functions ---
def delete_student(student_nombre_to_delete: str) -> bool:
    """Delete a student from the Firebase list by their 'nombre'."""
    try:
        current_students_df, _ = load_students() # We don't need the filename here
        if current_students_df is None:
            st.error("No students found to delete from.")
            return False

        # Normalize the name to delete for comparison, similar to how names are stored/loaded
        normalized_name_to_delete = str(student_nombre_to_delete).lower().strip()

        # Create a boolean series for rows to keep
        # Ensure 'nombre' column exists and is string type for comparison
        if 'nombre' not in current_students_df.columns:
            st.error("Student data is missing 'nombre' column. Cannot delete.")
            return False
        
        # Filter out the student to delete
        # Compare normalized versions
        students_to_keep_df = current_students_df[
            current_students_df['nombre'].astype(str).str.lower().str.strip() != normalized_name_to_delete
        ]

        if len(students_to_keep_df) == len(current_students_df):
            st.warning(f"Student '{student_nombre_to_delete}' not found in the list.")
            return False # Or True, if not finding is not an error

        # Save the modified DataFrame (which overwrites the old list)
        if save_students(students_to_keep_df):
            st.success(f"Student '{student_nombre_to_delete}' deleted successfully.")
            return True
        else:
            # save_students would have shown an error
            return False
            
    except Exception as e:
        st.error(f"Error deleting student '{student_nombre_to_delete}': {str(e)}")
        return False

def save_attendance(date: datetime.date, attendance_data: list):
    """Save attendance data to Firebase for a specific date."""
    try:
        user_email = st.session_state.email.replace('.', ',')
        date_str = date.strftime('%Y-%m-%d')
        # Ensure student names (keys in attendance_data) are safe for Firebase paths if necessary
        # For now, assuming they are simple strings.
        db.child("attendance").child(user_email).child(date_str).set(attendance_data)
        return True
    except Exception as e:
        st.error(f"Error saving attendance for {date_str}: {str(e)}")
        return False