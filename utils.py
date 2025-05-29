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
        # Create a copy of the dataframe to avoid modifying the original
        df = students_df.copy()
        
        # Ensure all data is JSON-serializable
        for col in df.columns:
            # Convert any numpy types to native Python types
            if df[col].dtype.kind in ['i', 'u', 'f', 'b']:  # numeric types
                df[col] = df[col].astype('object').where(df[col].notna(), None)
            # Convert datetime to string
            elif df[col].dtype.kind == 'M':  # datetime
                df[col] = df[col].dt.strftime('%Y-%m-%d')
        
        # Convert to dictionary with records orientation
        records = df.to_dict('records')
        
        # Ensure all values in records are JSON-serializable
        for record in records:
            for key, value in record.items():
                if pd.isna(value) or value is None:
                    record[key] = None
                elif isinstance(value, (int, float, bool, str)):
                    continue  # These are already JSON-serializable
                else:
                    record[key] = str(value)  # Convert any remaining types to string
        
        data = {
            'filename': 'students.xlsx',
            'data': records,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'  # ISO format with timezone
        }
        
        # Save to Firebase
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


def delete_attendance_dates(dates_to_delete=None, delete_all=False):
    """
    Delete attendance records for the specified dates or all records if delete_all=True.
    
    Args:
        dates_to_delete (list, optional): List of date strings in 'YYYY-MM-DD' format.
        delete_all (bool, optional): If True, deletes all attendance records for the user.
        
    Returns:
        bool: True if at least one deletion was successful, False otherwise.
    """
    print(f"Intentando eliminar fechas: {dates_to_delete}, delete_all={delete_all} DESDE utils")
    success = False

    try:
        user_email_key = st.session_state.email.replace('.', ',')
        user_base_attendance_path = f"attendance/{user_email_key}"

        if delete_all:
            # This case is for explicitly deleting ALL records for the user
            all_user_records_ref = db.child(user_base_attendance_path)
            print(f"WARNING: Attempting to delete ALL attendance records at path: {all_user_records_ref.path}")
            
            if not all_user_records_ref.path or all_user_records_ref.path == '/' or not all_user_records_ref.path.startswith('attendance/'):
                st.error(f"CRITICAL SAFETY HALT: Unsafe path for full deletion: '{all_user_records_ref.path}'. Aborting.")
                print(f"CRITICAL SAFETY HALT: Unsafe full deletion path: {all_user_records_ref.path}")
                return False

            try:
                all_user_records_ref.remove()
                print(f"SUCCESS: All attendance records removed at path: {all_user_records_ref.path}")
                return True
            except Exception as e:
                print(f"ERROR: Failed to remove all records: {str(e)}")
                st.error(f"Error al eliminar todos los registros: {str(e)}")
                return False

        # If no dates provided, we don’t do anything
        if not dates_to_delete:
            st.warning("No dates provided for deletion.")
            print("INFO: No dates provided, skipping deletion.")
            return False

        # Validate and clean dates
        valid_dates = []
        for date_str in dates_to_delete:
            try:
                datetime.datetime.strptime(date_str, '%Y-%m-%d')
                valid_dates.append(date_str.strip())
            except ValueError:
                st.warning(f"Formato de fecha inválido: {date_str}. Se omitirá.")
                print(f"WARNING: Invalid date format '{date_str}' ignored.")

        if not valid_dates:
            st.error("No hay fechas válidas para eliminar después de la validación.")
            print("ERROR: No valid dates to process after validation.")
            return False

        # Delete each valid date
        for date_str in valid_dates:
            full_path = f"{user_base_attendance_path}/{date_str}"
            ref_for_get = db.child(full_path)
            data_snapshot = ref_for_get.get()

            if data_snapshot.val() is not None:
                print(f"INFO: Removing data at path: {full_path}")
                try:
                    db.child(full_path).remove()
                    success = True
                except Exception as e:
                    print(f"ERROR: Failed to remove date {date_str}: {str(e)}")
                    st.error(f"Error al eliminar la fecha {date_str}: {str(e)}")
            else:
                print(f"INFO: No data found for date {date_str}, skipping.")

        return success

    except Exception as e:
        st.error(f"Error deleting attendance records: {str(e)}")
        print(f"EXCEPTION: {str(e)}")
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


def get_available_modules(user_email: str) -> list:
    """
    Retrieve and process available modules for a user.
    
    Args:
        user_email: The user's email (with . replaced with ,)
        
    Returns:
        list: List of module options with their details, sorted by proximity to current date
    """
    try:
        # Create a fresh Firebase reference for this operation
        modules_ref = db.child("modules").child(user_email).get()
        if not modules_ref.val():
            return []
            
        module_options = []
        today = datetime.datetime.today()
        cutoff_date = today - datetime.timedelta(days=15)
        
        # Process each module
        for module_id, module_data in modules_ref.val().items():
            if not module_data:
                continue
                
            module_name = module_data.get('name', 'Módulo sin nombre')
            
            # Process ciclo 1 if it exists
            if 'ciclo1_inicio' in module_data and module_data['ciclo1_inicio']:
                start_date = module_data['ciclo1_inicio']
                if isinstance(start_date, str):
                    try:
                        start_date_dt = datetime.datetime.fromisoformat(start_date)
                        if start_date_dt >= cutoff_date:
                            module_options.append({
                                'label': f"{module_name} (Ciclo 1 - Inicia: {start_date_dt.strftime('%m/%d/%Y')})",
                                'module_id': module_id,
                                'ciclo': 1,
                                'start_date': module_data['ciclo1_inicio'],
                                'module_name': module_name
                            })
                    except (ValueError, TypeError):
                        continue
            
            # Process ciclo 2 if it exists
            if 'ciclo2_inicio' in module_data and module_data['ciclo2_inicio']:
                start_date = module_data['ciclo2_inicio']
                if isinstance(start_date, str):
                    try:
                        start_date_dt = datetime.datetime.fromisoformat(start_date)
                        if start_date_dt >= cutoff_date:
                            module_options.append({
                                'label': f"{module_name} (Ciclo 2 - Inicia: {start_date_dt.strftime('%m/%d/%Y')})",
                                'module_id': module_id,
                                'ciclo': 2,
                                'start_date': module_data['ciclo2_inicio'],
                                'module_name': module_name
                            })
                    except (ValueError, TypeError):
                        continue
        
        # Sort by proximity to today's date
        module_options.sort(
            key=lambda x: abs((datetime.datetime.fromisoformat(x['start_date']) - today).days)
        )
        
        return module_options
        
    except Exception as e:
        st.error(f"Error al cargar los módulos: {str(e)}")
        return []