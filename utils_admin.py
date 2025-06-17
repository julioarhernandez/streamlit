# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\utils.py
import streamlit as st
import pandas as pd
from config import db # Assuming db is your Firebase Realtime Database reference from config.py
import datetime # Added for type hinting and date operations

def admin_get_last_updated(table_name, course_email):
    """
    Fetch the last_updated timestamp for a given table from Firebase metadata.
    
    Args:
        table_name (str): The name of the data section ('attendance', 'students', 'modules', etc.)
    
    Returns:
        str or None: The last_updated ISO timestamp, or None if not found.
    """
    if user_email:
        user_email = user_email.replace('.', ',')
        ref = db.child("metadata").child(table_name).child(user_email)
        snapshot = ref.get()
        if snapshot.val() is not None:
            metadata = snapshot.val()
        else:
            return None
    else:
        metadata = db.child("metadata").child(table_name).get().val()
    if metadata and 'last_updated' in metadata:
        return metadata['last_updated']
    else:
        return None
        
def admin_set_last_updated(table_name, course_email):
    """
    Update the last_updated timestamp for a given table in Firebase metadata to current UTC time.
    
    Args:
        table_name (str): The name of the data section ('attendance', 'students', 'modules', etc.)
        course_email (str): The email of the course to update
    
    Returns:
        str: The new last_updated ISO timestamp.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if course_email:
        safe_email = course_email.replace('.', ',')
        db.child("metadata").child(table_name).child(safe_email).update({
            'last_updated': now_iso
        })
    else:
        db.child("metadata").child(table_name).update({
            'last_updated': now_iso
        })
    return now_iso
    
def admin_get_students_by_email(email):
    """
    Retrieves student records from the database based on the provided email.
    This function is designed for a database structure where the email
    is the primary key under 'students', and its value is an object
    containing a 'data' array of student details.

    Args:
        email (str): The email address which is also the key under the 'students' node.

    Returns:
        dict: A dictionary of student records if found, or an empty dictionary
              if no students are found or an error occurs.
    """
    try:
        # Reference to the 'students' node in your database
        students_ref = db.child("students")

        # Directly access the student data using the email as the key.
        # Firebase keys cannot contain '.', '#', '$', '[', or ']'
        # If your email keys literally contain '.' like "cba2@iti.edu",
        # you might need to escape them or store them differently if direct
        # key access doesn't work. However, typically, Firebase handles
        # this if the key was set using a string.
        snapshot = students_ref.child(email.replace('.', ',')).get() # Common workaround for '.' in keys

        # Check if any data was returned for that specific email key
        if not snapshot.val():
            print(f"No student entry found for email key: {email}")
            return {}

        # The data under this email key is an object, and within it,
        # you have a 'data' array.
        student_data_array = snapshot.val().get("data")

        if not student_data_array:
            print(f"No 'data' array found for email key: {email}")
            return {}

        # If you want to return a dictionary where keys are derived (e.g., index)
        # or if you just want the list of student objects:
        found_students = {}
        for i, student_record in enumerate(student_data_array):
            # You might want a unique key for each student record.
            # Using a combination of email and index, or a 'canvas_id' if unique.
            key = f"{email}_{i}" # Example key: "cba2@iti.edu_0"
            found_students[key] = student_record

        print(f"Found {len(student_data_array)} records for email key: {email}")
        print(found_students)
        return found_students

    except Exception as e:
        print(f"Error querying students by email key '{email}': {str(e)}")
        return {}

@st.cache_data
def admin_get_student_group_emails():
    """
    Retrieves the top-level email keys (representing student groups)
    from the 'students' node in the database.

    Returns:
        list: A list of email strings (e.g., "cba2@iti,edu"), or an empty list
              if no student groups are found or an error occurs.
    """
    try:
        students_ref = db.child("students")
        students_snapshot = students_ref.get()
        print('\n\n---------------------------------database readed-------------------------\n\n', {k: v['data'][0] if v and 'data' in v else None for k, v in students_snapshot.val().items()})

        if not students_snapshot.val():
            print("No student entries found in the database")
            return []

        email_keys = []
        for student_key, _ in students_snapshot.val().items():
            email_keys.append(student_key)

        print(f"Found {len(email_keys)} student group emails.")
        print(email_keys)
        return email_keys

    except Exception as e:
        print(f"Error retrieving student group emails: {str(e)}")
        return []
    
@st.cache_data
def admin_load_students(course_email):
    """
    Load students data from Firebase and ensure all required fields are present.
    
    Returns:
        tuple: (DataFrame with student data, filename) or (None, None) if error or no data
    """
    try:
        user_email = course_email
        if 'call_count' not in st.session_state:
            st.session_state.call_count = 0
        data = db.child("students").child(user_email).get().val()
        st.session_state.call_count += 1
        print(f"\n{st.session_state.call_count} ---data from firebase----\n", data)

        if not data or 'data' not in data:
            return None, None
            
        # Create DataFrame from records
        df = pd.DataFrame(data['data'])
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Ensure required columns exist
        if 'nombre' not in df.columns:
            st.error("Error: El archivo debe contener una columna 'nombre'")
            return None, None
            
        # Clean and standardize data
        df['nombre'] = df['nombre'].astype(str).str.strip()
        
        # Initialize optional fields if they don't exist
        optional_fields = {
            'email': '',
            'canvas_id': '',
            'telefono': '',
            'modulo': '',
            'ciclo': '',
            'fecha_inicio': None
        }
        
        for field, default_value in optional_fields.items():
            if field not in df.columns:
                df[field] = default_value
            else:
                # Clean up the data
                if field == 'fecha_inicio' and pd.api.types.is_datetime64_any_dtype(df[field]):
                    # Convert datetime to string for consistency
                    df[field] = pd.to_datetime(df[field]).dt.strftime('%Y-%m-%d')
                else:
                    df[field] = df[field].fillna(default_value if default_value is not None else '').astype(str).str.strip()
        
        # Reorder columns for consistency
        column_order = ['nombre', 'email', 'canvas_id', 'telefono', 'modulo', 'fecha_inicio', 'ciclo']
        df = df[[col for col in column_order if col in df.columns] + 
                [col for col in df.columns if col not in column_order]]
        
        return df, data.get('filename', 'students.xlsx')
        
    except Exception as e:
        st.error(f"Error loading students: {str(e)}")
        return None, None

def admin_save_students(course_email, students_df):
    """
    Save students data to Firebase with proper handling of all fields.
    
    Args:
        course_email (str): Email of the course to save students to
        students_df (DataFrame): DataFrame containing student records
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        if students_df is None or students_df.empty:
            st.warning("No student data to save.")
            return False
            
        # Create a working copy to avoid modifying the original
        df = students_df.copy()
        
        # Ensure required columns exist
        if 'nombre' not in df.columns:
            st.error("Error: Student data must contain a 'nombre' column")
            return False
            
        # Initialize optional fields if they don't exist
        optional_fields = {
            'email': '',
            'canvas_id': '',
            'telefono': '',
            'modulo': '',
            'ciclo': '',
            'fecha_inicio': None
        }
        
        for field, default_value in optional_fields.items():
            if field not in df.columns:
                df[field] = default_value
        
        # Clean and standardize data
        df['nombre'] = df['nombre'].astype(str).str.strip()
        
        # Convert data types and ensure JSON serialization
        for col in df.columns:
            # Handle numeric types
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype('object').where(df[col].notna(), None)
            # Handle datetime types
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
            # Handle string types
            else:
                df[col] = df[col].fillna('').astype(str).str.strip()
        
        # Convert to records and ensure all values are JSON-serializable
        records = []
        for _, row in df.iterrows():
            record = {}
            for key, value in row.items():
                if pd.isna(value) or value is None or value == '':
                    record[key] = None
                else:
                    record[key] = str(value) if not isinstance(value, (int, float, bool, str)) else value
            records.append(record)
        
        # Prepare data for Firebase
        data = {
            'filename': 'students.xlsx',
            'data': records,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'metadata': {
                'version': '1.0',
                'fields': list(df.columns),
                'record_count': len(df)
            }
        }
        
        # Save to Firebase with error handling
        try:
            db.child("students").child(course_email).set(data)
            st.success(f"Successfully saved {len(df)} student records to {course_email}.")
            admin_set_last_updated('students', course_email)
            return True
        except Exception as firebase_error:
            st.error(f"Firebase error: {str(firebase_error)}")
            return False
            
    except Exception as e:
        st.error(f"Error saving students: {str(e)}")
        if 'df' in locals():
            st.error(f"Columns in DataFrame: {', '.join(df.columns)}")
        return False

@st.cache_data
def admin_get_available_modules(user_email: str) -> list:
    """
    Retrieve and process available modules for a user.

    Args:
        user_email: The user's email (with . replaced with , for Firebase path)

    Returns:
        list: List of module options with their details, sorted by proximity to current date
    """
    try:
        # Create a fresh Firebase reference for this operation
        # Note: You should ensure 'db' is initialized before this function is called.
        modules_ref = db.child("modules").child(user_email).get()

        if 'call_count' not in st.session_state:
            st.session_state.call_count = 0
        st.session_state.call_count += 1
        print(f"\n{st.session_state.call_count} ---get_available_modules-data from firebase----\n", modules_ref.val())

        if not modules_ref.val():
            return []

        module_options = []
        today = datetime.datetime.today()
        cutoff_date = today - datetime.timedelta(days=180)

        # Process each module
        for module_id, module_data in modules_ref.val().items():
            if not module_data:
                continue

            module_name = module_data.get('name', 'Módulo sin nombre')

            # --- Extract ALL relevant module data fields ---
            # Debug: Print the raw module data
            print(f"\nRaw module data for {module_id}:", module_data)
            
            # Use .get() with a default value to avoid KeyError if a field is missing in Firebase
            start_date_str = module_data.get('fecha_inicio_1')
            end_date_str = module_data.get('fecha_fin_1')  # Check if this field exists in your database
            
            # Try different possible field names for duration and credits
            duration_weeks = 0
            if 'duracion_semanas' in module_data:
                duration_weeks = module_data['duracion_semanas']
            elif 'duration_weeks' in module_data:
                duration_weeks = module_data['duration_weeks']
                
            credits = 0
            if 'creditos' in module_data:
                credits = module_data['creditos']
            elif 'credits' in module_data:
                credits = module_data['credits']
                
            description = module_data.get('description', '')  # Try English version first
            if not description:  # Fall back to Spanish if English version doesn't exist
                description = module_data.get('descripcion', '')
                
            ciclo = module_data.get('ciclo', 1)  # Default to 1 if not specified
            
            # Debug: Print the extracted values
            print(f"Extracted values - duration: {duration_weeks}, credits: {credits}, description: {description}")

            start_date_dt = None
            if isinstance(start_date_str, str):
                try:
                    start_date_dt = datetime.datetime.fromisoformat(start_date_str)
                except (ValueError, TypeError):
                    pass # Keep start_date_dt as None if parsing fails

            # Only add the module if start_date is parsed successfully and is within cutoff
            if start_date_dt and start_date_dt >= cutoff_date:
                module_entry = {
                    'label': f"{module_name} (Ciclo {ciclo} - Inicia: {start_date_dt.strftime('%m/%d/%Y')})",
                    'module_id': module_id,
                    'module_name': module_name, # Original name
                    'ciclo': ciclo,
                    'start_date': start_date_str, # Keep as string for this function's return, conversion happens in UI
                    'end_date': end_date_str,     # Include end_date
                    'duration_weeks': duration_weeks,
                    'credits': credits,           # Add credits
                    'description': description,   # Add description
                    'firebase_key': module_id     # This is often useful, same as module_id
                }
                module_options.append(module_entry)

        # Sort by proximity to today's date
        # Ensure 'start_date' is a string before trying fromisoformat
        module_options.sort(
            key=lambda x: abs((datetime.datetime.fromisoformat(x['start_date']) - today).days)
            if 'start_date' in x and isinstance(x['start_date'], str) and x['start_date'] else float('inf')
        )

        return module_options

    except Exception as e:
        st.error(f"Error al cargar los módulos: {str(e)}")
        return []

def save_modules_to_db(user_email: str, modules_df: pd.DataFrame) -> bool:
    """Save modules to Firebase and update session."""
    try:
        user_email_sanitized = user_email
        db.child("modules").child(user_email_sanitized).set(modules_df.to_dict('records'))
        update_modules_in_session(modules_df)
        return True
    except Exception as e:
        st.error(f"Error saving modules: {str(e)}")
        return False


def load_breaks():
    """
    Loads all 'breaks' data from the Firebase Realtime Database.
    Handles cases where data is empty or not in expected dictionary format.
    """
    try:
        # Create a fresh reference to the 'breaks' child node
        breaks_ref = db.child("breaks")
        breaks_data = breaks_ref.get().val() or {} # Get data, default to empty dict if None
        
        # Ensure the retrieved data is a dictionary
        if not isinstance(breaks_data, dict):
            st.warning(f"Se esperaba un diccionario para 'breaks', pero se obtuvo: {type(breaks_data)}. Retornando diccionario vacío.")
            return {}
        return breaks_data
    except Exception as e:
        st.error(f"Error al cargar las semanas de descanso: {e}")
        return {}