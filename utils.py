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

def get_attendance_dates():
    """
    Get a list of all dates with saved attendance records.
    Returns a sorted list of date strings in 'YYYY-MM-DD' format.
    """
    try:
        user_email = st.session_state.email.replace('.', ',')
        docs = db.child("attendance").child(user_email).get().val()
        if not docs:
            return []
            
        # Extract dates and filter out any None or invalid dates
        dates = []
        for doc in docs:
            try:
                # Validate date format                    
                datetime.datetime.strptime(doc, '%Y-%m-%d')
                dates.append(doc)
            except (ValueError, TypeError):
                continue
        # Sort dates chronologically
        return sorted(dates)
    except Exception as e:
        st.error(f"Error loading attendance dates: {str(e)}")
        return []

def delete_attendance_dates(dates_to_delete):
    """
    Delete attendance records for the specified dates
    
    Args:
        dates_to_delete (list): List of date strings in 'YYYY-MM-DD' format
        
    Returns:
        bool: True if all deletions were successful, False otherwise
    """
    if not dates_to_delete:
        return False
        
    try:
        user_email = st.session_state.email.replace('.', ',')
        attendance_ref = db.child("attendance").child(user_email)
        
        for date_str in dates_to_delete:
            try:
                attendance_ref.child(date_str).remove()
            except Exception as e:
                st.error(f"Error deleting attendance for {date_str}: {str(e)}")
                continue
                
        return True
    except Exception as e:
        st.error(f"Error deleting attendance records: {str(e)}")
        return False

def format_date_for_display(date_value):
    """
    Convert date to MM/DD/YYYY format for display.
    Handles various input formats and edge cases.
    """
    if not date_value or pd.isna(date_value):
        return 'No especificada'
    
    try:
        # Handle different input types
        if isinstance(date_value, str):
            if date_value.strip().lower() in ['', 'no especificada', 'none']:
                return 'No especificada'
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    date_obj = datetime.datetime.strptime(str(date_value).strip(), fmt)
                    return date_obj.strftime('%m/%d/%Y')
                except ValueError:
                    continue
        elif hasattr(date_value, 'strftime'):
            # Already a datetime object
            return date_value.strftime('%m/%d/%Y')
        else:
            # Try converting to string first
            return format_date_for_display(str(date_value))
    except (ValueError, TypeError, AttributeError):
        pass
    
    return 'No especificada'

def get_student_start_date(all_students_df, student_name):
    """
    Get start date for a specific student.
    Returns formatted date string or 'No especificada'.
    """
    if all_students_df.empty:
        return 'No especificada'
    
    # Find student record (case-insensitive matching)
    student_mask = all_students_df['nombre'].str.strip().str.lower() == student_name.strip().lower()
    matching_students = all_students_df[student_mask]
    
    if matching_students.empty:
        return 'No especificada'
    
    student_data = matching_students.iloc[0]
    start_date = student_data.get('fecha_inicio', 'No especificada')
    
    return format_date_for_display(start_date)

def create_filename_date_range(start_date, end_date):
    """
    Create a date range string for filename from start and end dates.
    Returns formatted string or None if dates are invalid.
    """
    try:
        # Handle different input types
        if hasattr(start_date, 'strftime'):
            start_str = start_date.strftime('%Y%m%d')
        else:
            start_obj = datetime.datetime.strptime(str(start_date), '%m/%d/%Y')
            start_str = start_obj.strftime('%Y%m%d')
        
        if hasattr(end_date, 'strftime'):
            end_str = end_date.strftime('%Y%m%d')
        else:
            end_obj = datetime.datetime.strptime(str(end_date), '%m/%d/%Y')
            end_str = end_obj.strftime('%Y%m%d')
        
        return f"_{start_str}_a_{end_str}"
    except (ValueError, AttributeError, TypeError):
        return ""

def date_format(date_value, from_format, to_format='%m/%d/%Y'):
    """
    Convert date from one format to another.
    
    Args:
        date_value (str/datetime): The date to convert
        from_format (str): The format of the input date (e.g., '%Y/%m/%d')
        to_format (str): The desired output format (default: '%m/%d/%Y')
    
    Returns:
        str: Formatted date string or 'No especificada' if conversion fails
    
    Examples:
        date_format("2025/10/31", "%Y/%m/%d") -> "10/31/2025"
        date_format("31-10-2025", "%d-%m-%Y") -> "10/31/2025"
        date_format("2025-10-31", "%Y-%m-%d", "%d/%m/%Y") -> "31/10/2025"
    """
    if not date_value or pd.isna(date_value):
        return 'No especificada'
    
    try:
        # Handle datetime objects
        if hasattr(date_value, 'strftime'):
            return date_value.strftime(to_format)
        
        # Handle string dates
        if isinstance(date_value, str):
            date_str = str(date_value).strip()
            if date_str.lower() in ['', 'no especificada', 'none']:
                return 'No especificada'
            
            # Parse with the specified format
            date_obj = datetime.datetime.strptime(date_str, from_format)
            return date_obj.strftime(to_format)
        
        # Try converting other types to string first
        date_str = str(date_value).strip()
        date_obj = datetime.datetime.strptime(date_str, from_format)
        return date_obj.strftime(to_format)
        
    except (ValueError, TypeError, AttributeError):
        return 'No especificada'