import streamlit as st
import pandas as pd
from datetime import timedelta, datetime, timezone
import io
from typing import List, Optional, Tuple
import pyrebase

firebaseConfig = {
    "apiKey": "AIzaSyCjB9UI5Soj6dHlbzCnrbBuzIfeWKEPMvw",
    "databaseURL": "https://attendance-bfa78-default-rtdb.firebaseio.com",
    "authDomain": "attendance-bfa78.firebaseapp.com",
    "projectId": "attendance-bfa78",
    "storageBucket": "attendance-bfa78.firebasestorage.app",
    "messagingSenderId": "13347487257",
    "appId": "1:13347487257:web:eadf04fb63d40086d4f488",
    "measurementId": "G-K8KWGGWRX4"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()  # Initialize Firebase Database

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = None

# Sidebar for logged in users
if st.session_state.logged_in:
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.email}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.email = None
            st.rerun()

# Login form (only show if not logged in)
if not st.session_state.logged_in:
    st.title("Login")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.logged_in = True
            st.session_state.email = email
            st.rerun()  # Rerun to update the UI
        except Exception as e:
            error_str = str(e)
            if "INVALID_EMAIL" in error_str or "INVALID_PASSWORD" in error_str or "INVALID_LOGIN_CREDENTIALS" in error_str:
                st.error("Invalid email or password. Please try again.")
            else:
                st.error(f"Error: {e}")

# Initialize session state for resident data
if 'residentes_df' not in st.session_state:
    st.session_state.residentes_df = pd.DataFrame()
    st.session_state.residentes_filename = None

def format_date(fecha, separator='-'):
    """
    Format a date object as 'MM-DD-YY' or 'MM/DD/YY'.
    
    Args:
        fecha: datetime.date object
        separator: Either '-' or '/' to separate date components
        
    Returns:
        str: Formatted date string
    """
    if separator not in ('-', '/'):
        raise ValueError("Separator must be either '-' or '/'")
    return f"{fecha.month}{separator}{fecha.day}{separator}{fecha.year % 100}"

def save_residentes_to_firestore(user_email: str, residentes_data: pd.DataFrame, filename: str) -> bool:
    """Save residentes data to Firebase Realtime Database under user's email"""
    try:
        # Clean the email to use as a key (replace . with , as Firebase doesn't allow . in keys)
        user_key = user_email.replace('.', ',')
        
        # Convert DataFrame to dictionary for storage
        residentes_dict = {
            'filename': filename,
            'data': residentes_data.to_dict('records'),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Get a reference to the location
        ref = db.child("users").child(user_key).child("residentes")
        
        # Try to save the data
        ref.set(residentes_dict)
        
        # Verify the data was saved
        saved_data = ref.get().val()
        if saved_data is None:
            st.error("❌ Failed to save data: No data was saved")
            return False
            
        st.success("✅ Data saved successfully to Firebase Realtime Database")
        return True
    except Exception as e:
        st.error(f"❌ Error saving to Firebase: {str(e)}")
        st.error(f"Database URL: {db.database_url}")
        st.error(f"Trying to save to path: users/{user_key}/residentes")
        return False

def load_residentes_from_firestore(user_email: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Load residentes data from Firebase Realtime Database for the given user"""
    try:
        user_key = user_email.replace('.', ',')
        # Get the reference first
        ref = db.child("users").child(user_key).child("residentes")
        residentes_data = ref.get().val()
        
        if residentes_data and 'data' in residentes_data:
            # Convert the stored data back to DataFrame
            df = pd.DataFrame(residentes_data['data'])
            return df, residentes_data.get('filename', 'archivo_cargado.csv')
        return pd.DataFrame(), None
    except Exception as e:
        # Don't show error if data doesn't exist (first time user)
        if "404" not in str(e):
            st.error(f"Error al cargar de Firestore: {str(e)}")
        return pd.DataFrame(), None

def cargar_lista_residentes(uploaded_file=None) -> pd.DataFrame:
    """Carga la lista de residentes desde el archivo subido o desde Firestore"""
    # Try to load from session state first
    if 'residentes_df' in st.session_state and not st.session_state.residentes_df.empty:
        return st.session_state.residentes_df
    
    # Try to load from Firestore if user is logged in
    if st.session_state.logged_in and 'email' in st.session_state and st.session_state.email:
        df, filename = load_residentes_from_firestore(st.session_state.email)
        if not df.empty:
            st.session_state.residentes_df = df
            st.session_state.residentes_filename = filename
            st.session_state.residentes_uploaded = True
            return df
    
    # Load from uploaded file if provided
    if uploaded_file is not None:
        try:
            # Read the file
            df = pd.read_csv(uploaded_file)
            # Update session state
            st.session_state.residentes_df = df
            st.session_state.residentes_filename = uploaded_file.name
            st.session_state.residentes_uploaded = True
            
            # Save to Firestore if user is logged in
            if st.session_state.logged_in and 'email' in st.session_state and st.session_state.email:
                save_residentes_to_firestore(st.session_state.email, df, uploaded_file.name)
                
            return df
        except Exception as e:
            st.error(f"Error al cargar el archivo de residentes: {str(e)}")
            return pd.DataFrame()
    
    return pd.DataFrame()

def obtener_nombre_archivo_residentes() -> str:
    """Obtiene el nombre del archivo de residentes guardado"""
    return st.session_state.get('residentes_filename', "No se ha cargado ningún archivo")

def procesar_archivo_asistencia(uploaded_file) -> List[str]:
    """Process an uploaded attendance file and return list of participants."""
    try:
        # Read the file content as string
        content = uploaded_file.getvalue().decode('utf-16')
        lines = content.split('\n')
        
        # Find the start and end of the participants section
        start_idx = next((i for i, line in enumerate(lines) 
                         if line.strip().startswith("Name\tFirst Join")), None)
        
        if start_idx is None:
            st.warning("Formato de archivo no reconocido. No se encontró el encabezado de participantes.")
            return []
            
        end_idx = next((i for i, line in enumerate(lines[start_idx:], start_idx)
                      if "3. In-Meeting Activities" in line.strip()), len(lines))
        
        # Get the participants section
        data_lines = lines[start_idx:end_idx]
        
        # Create DataFrame from the specific lines
        df = pd.read_csv(io.StringIO("\n".join(data_lines)), sep="\t")
        
        # Filter out organizers and get unique names
        df_filtered = df[df['Role'] != 'Organizer']
        participantes = df_filtered["Name"].dropna().unique().tolist()
        
        return participantes
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        return []

def asistencia_dia(fecha, uploaded_files=None):
    """Process attendance for a specific date using uploaded files.
    
    Args:
        fecha: Date as datetime or string
        uploaded_files: List of uploaded files
        
    Returns:
        Tuple of (nombres_manana, nombres_tarde) - lists of names
    """
    nombres_manana = set()
    nombres_tarde = set()
    
    if uploaded_files:
        # Convert date to multiple possible string formats for matching
        if not isinstance(fecha, str):
            # Try multiple date formats that might be in filenames
            date_formats = [
                f"{fecha.month}-{fecha.day}-{fecha.year % 100}",  # M-D-YY
                f"{fecha.month:02d}-{fecha.day:02d}-{fecha.year % 100:02d}",  # MM-DD-YY
                f"{fecha.month}/{fecha.day}/{fecha.year % 100}",  # M/D/YY
                f"{fecha.month:02d}/{fecha.day:02d}/{fecha.year % 100:02d}",  # MM/DD/YY
                f"{fecha.year}-{fecha.month:02d}-{fecha.day:02d}"  # YYYY-MM-DD
            ]
        else:
            date_formats = [fecha]
        
        for file in uploaded_files:
            file_name = file.name
            
            # Check if this file is for any of the date formats and session
            for date_fmt in date_formats:
                if str(date_fmt) in file_name:
                    try:
                        if "mañana" in file_name.lower():
                            nombres_manana.update(procesar_archivo_asistencia(file))
                        elif "tarde" in file_name.lower():
                            nombres_tarde.update(procesar_archivo_asistencia(file))
                        break  # Found a matching date format, no need to check others
                    except Exception as e:
                        st.warning(f"Error procesando archivo {file_name}: {str(e)}")
                        break
    
    return list(nombres_manana), list(nombres_tarde)

def asistencia_semana(desde, hasta, uploaded_files=None, skip_weekends=True):
    dias = pd.date_range(desde, hasta)
    if skip_weekends:
        dias = [d for d in dias if d.weekday() < 5]  # Only keep weekdays (0-4 = Monday-Friday)
    
    asistencias = []
    for dia in dias:
        asistencia_manana, asistencia_tarde = asistencia_dia(dia, uploaded_files)
        asistencias.append((asistencia_manana, asistencia_tarde))
    
    return asistencias

def initialize_attendance_for_date(fecha, residentes_df, uploaded_files=None):
    """Initialize attendance state for a specific date if not exists"""
    fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}"
    attendance_key = f"attendance_{fecha_str}"
    
    if attendance_key not in st.session_state:
        # Get automatic attendance from files
        asistentes_manana_auto, asistentes_tarde_auto = asistencia_dia(fecha, uploaded_files)
        
        # Initialize with automatic attendance
        st.session_state[attendance_key] = {}
        
        # Ensure we have residentes data
        if not residentes_df.empty:
            for _, row in residentes_df.iterrows():
                nombre = row["nombre"]
                st.session_state[attendance_key][nombre] = {
                    'mañana': nombre in asistentes_manana_auto,
                    'tarde': nombre in asistentes_tarde_auto
                }
    
    return attendance_key

# --- UI ---
if st.session_state.logged_in:
    st.title("📋 Seguimiento de Asistencia")

    # Initialize session state for file uploads
    if 'residentes_uploaded' not in st.session_state:
        st.session_state.residentes_uploaded = False
    if 'asistencia_uploaded' not in st.session_state:
        st.session_state.asistencia_uploaded = False
    if 'residentes_file' not in st.session_state:
        st.session_state.residentes_file = None
    if 'asistencia_files' not in st.session_state:
        st.session_state.asistencia_files = []

    # Check if both files are uploaded
    files_uploaded = st.session_state.get('residentes_uploaded', False) and st.session_state.get('asistencia_uploaded', False)
    st.session_state.files_uploaded = files_uploaded

    st.header("1. Cargar Archivos")

    # Collapsible file upload section
    with st.expander("📤 Cargar Archivos", expanded=not st.session_state.get("files_uploaded", False)):
        # Upload resident list
        uploaded_residentes = st.file_uploader(
            "📝 Lista de Estudiantes (CSV)",
            type=["csv"],
            help="Sube el archivo CSV con la lista de Estudiantes",
            key="residentes_uploader"
        )

        # Upload attendance files
        uploaded_files = st.file_uploader(
            "📊 Archivos de asistencia",
            type=["csv"],
            accept_multiple_files=True,
            help="Sube los archivos de asistencia exportados de Zoom",
            key="asistencia_uploader"
        )

        # Update session state when files are uploaded
        if uploaded_residentes is not None:
            st.session_state.residentes_uploaded = True
            st.session_state.residentes_file = uploaded_residentes
        else:
            st.session_state.residentes_uploaded = False
            st.session_state.residentes_file = None

        if uploaded_files and len(uploaded_files) > 0:
            st.session_state.asistencia_uploaded = True
            st.session_state.asistencia_files = uploaded_files
        else:
            st.session_state.asistencia_uploaded = False
            st.session_state.asistencia_files = []

        # Show current resident file info
        current_resident_file = obtener_nombre_archivo_residentes()
        if current_resident_file != "No se ha cargado ningún archivo":
            st.success(f"✅ Archivo cargado: {current_resident_file}")
            if st.button("🗑️ Limpiar archivo de Estudiantes"):
                st.session_state.residentes_df = pd.DataFrame()
                st.session_state.residentes_filename = None
                st.session_state.residentes_uploaded = False
                st.rerun()

    # Update overall flag
    st.session_state.files_uploaded = (
        st.session_state.residentes_uploaded and st.session_state.asistencia_uploaded
    )
        

    # Show warning if files are missing
    if not st.session_state.files_uploaded:
        st.warning("Por favor, sube ambos archivos para habilitar la aplicación")
        st.stop()

    # Initialize only if not exists
    if 'rango_fechas' not in st.session_state:
        st.session_state.rango_fechas = True

    st.header("2. Seleccionar Rango de Fechas")

    # Get date range input
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input(
            "Fecha de inicio",
            disabled=not st.session_state.files_uploaded,
            help="Selecciona la fecha de inicio del rango"
        )

    # Only show end date if range is enabled
    with col2:
        if st.session_state.rango_fechas:
            # Set minimum date to be one day after fecha_inicio
            min_date = fecha_inicio + timedelta(days=1)
            fecha_fin = st.date_input(
                "Fecha de fin",
                min_value=min_date,
                value=min_date,
                disabled=not st.session_state.files_uploaded,
                help="La fecha de fin debe ser posterior a la fecha de inicio"
            )
        else:
            fecha_fin = fecha_inicio  # Use start date as end date

    # Date range checkbox
    st.checkbox(
        "Rango de fechas",
        key='rango_fechas',
        disabled=not st.session_state.files_uploaded,
        help="Marcar para seleccionar un rango de fechas, desmarcar para una sola fecha"
    )

    # Checkbox for weekend filtering
    skip_weekends = st.checkbox(
        "Omitir fines de semana", 
        value=True,
        disabled=not st.session_state.files_uploaded,
        help="Si está marcado, no se incluirán sábados ni domingos",
        key="skip_weekends"
    )

    # Load resident data
    residentes = cargar_lista_residentes(uploaded_residentes)

    # Show warning if no resident data is available
    if residentes.empty:
        st.warning("Por favor, sube el archivo con la lista de Estudiantes")
        st.stop()
    
    # If we have a new upload, save it to Firestore
    if uploaded_residentes is not None and st.session_state.logged_in and 'email' in st.session_state:
        if save_residentes_to_firestore(st.session_state.email, residentes, uploaded_residentes.name):
            st.success("✅ Datos de estudiantes guardados en tu cuenta")
    
    # Store in session for faster access
    st.session_state.residentes_df = residentes

    # Get attendance for the selected date range
    asistencias_por_dia = asistencia_semana(fecha_inicio, fecha_fin, uploaded_files, st.session_state.skip_weekends)

    # Create a DataFrame to store daily attendance
    attendance_data = []

    # Generate the actual date range that will be displayed (respecting weekend filtering)
    date_range = []
    current_date = fecha_inicio
    while current_date <= fecha_fin:
        if not (st.session_state.skip_weekends and current_date.weekday() >= 5):
            date_range.append(current_date)
        current_date += timedelta(days=1)

    # Process each date in the filtered range
    for i, fecha in enumerate(date_range):
        fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}"
        
        # Get attendance from the pre-calculated data
        if i < len(asistencias_por_dia):
            asistentes_manana, asistentes_tarde = asistencias_por_dia[i]
            total_manana = len(asistentes_manana)
            total_tarde = len(asistentes_tarde)
        else:
            total_manana = 0
            total_tarde = 0
        
        # Map day names to Spanish
        dias_semana = {
            'Monday': 'Lunes',
            'Tuesday': 'Martes',
            'Wednesday': 'Miércoles',
            'Thursday': 'Jueves',
            'Friday': 'Viernes',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        
        # Add to attendance data
        dia_nombre = dias_semana[fecha.strftime('%A')]
        attendance_data.append({
            'Día': dia_nombre,
            'Fecha': fecha_str,
            'Mañana': total_manana,
            'Tarde': total_tarde
        })

    # Create a DataFrame for the attendance table with all required columns
    attendance_df = pd.DataFrame(attendance_data)
    
    # Ensure all required columns exist with default values if missing
    required_columns = ['Día', 'Fecha', 'Mañana', 'Tarde']
    for col in required_columns:
        if col not in attendance_df.columns:
            attendance_df[col] = 0  # Default value for numeric columns
    
    st.header("3. Reportes")

    # Display the attendance table
    st.subheader("📊 Reporte diario de asistencia")
    
    # Show total attendance metrics only if it's not a range of dates
    if fecha_inicio == fecha_fin and not attendance_df.empty:
        # Add metrics for total attendance (only for single dates)
        with st.container():
            col1, col2, _ = st.columns([2, 2, 6])
            with col1:
                morning_total = attendance_df['Mañana'].sum() if 'Mañana' in attendance_df else 0
                st.metric("Total Mañana", f"{morning_total}")
            with col2:
                afternoon_total = attendance_df['Tarde'].sum() if 'Tarde' in attendance_df else 0
                st.metric("Total Tarde", f"{afternoon_total}")

    # Display the attendance table without index
    st.dataframe(attendance_df, hide_index=True)

    # ATTENDANCE EDITOR - Only for the last date in range
    fecha_actual_str = f"{fecha_fin.month}-{fecha_fin.day}-{fecha_fin.year % 100}"
    fecha_actual_slash = format_date(fecha_fin, '/')

    # Initialize attendance state for this date
    attendance_key = initialize_attendance_for_date(fecha_fin, residentes, uploaded_files)

    # Create DataFrame for the editor using session state - FIXED VERSION
    editor_data = []
    if attendance_key in st.session_state and st.session_state[attendance_key]:
        for nombre in st.session_state[attendance_key]:
            editor_data.append({
                'nombre': nombre,
                'mañana': st.session_state[attendance_key][nombre]['mañana'],
                'tarde': st.session_state[attendance_key][nombre]['tarde']
            })
    else:
        # Fallback: create editor data from residentes if attendance state is empty
        for _, row in residentes.iterrows():
            nombre = row["nombre"]
            editor_data.append({
                'nombre': nombre,
                'mañana': False,
                'tarde': False
            })

    editor_df = pd.DataFrame(editor_data)

    # Display the editor if it is not a range of dates
    if fecha_inicio == fecha_fin:
        with st.container():
            st.subheader(f"✏️ Asistencia para {fecha_actual_slash}")
        
        # Only show editor if we have data
        if not editor_df.empty:
            # Use a unique key that includes date to avoid conflicts
            editor_key = f"editor_{fecha_actual_str}_{hash(str(fecha_fin))}"
            
            edited_df = st.data_editor(
                editor_df,
                column_config={
                    "nombre": st.column_config.TextColumn("Nombre", disabled=True),
                    "mañana": st.column_config.CheckboxColumn("Mañana"),
                    "tarde": st.column_config.CheckboxColumn("Tarde")
                },
                disabled=["nombre"],
                hide_index=True,
                key=editor_key,
                use_container_width=True
            )
            
            # Update session state with changes - FIXED VERSION
            if edited_df is not None and not edited_df.empty:
                # Ensure attendance_key exists in session state
                if attendance_key not in st.session_state:
                    st.session_state[attendance_key] = {}
                
                # Update each row
                for _, row in edited_df.iterrows():
                    nombre = row["nombre"]
                    st.session_state[attendance_key][nombre] = {
                        'mañana': bool(row['mañana']),
                        'tarde': bool(row['tarde'])
                    }
        else:
            st.warning("No hay datos de estudiantes para mostrar. Verifica que el archivo de Estudiantes esté cargado correctamente.")

    # Calculate who attended during the entire range (including manual edits)
    asistencia_total = set()

    # Add from file-based attendance
    for asistencia_manana, asistencia_tarde in asistencias_por_dia:
        asistencia_total.update(asistencia_manana)
        asistencia_total.update(asistencia_tarde)

    # Add from manual attendance for the current date being edited
    if attendance_key in st.session_state and st.session_state[attendance_key]:
        for nombre in st.session_state[attendance_key]:
            if (st.session_state[attendance_key][nombre]['mañana'] or 
                st.session_state[attendance_key][nombre]['tarde']):
                asistencia_total.add(nombre)

    # Create the final attendance status
    residentes_con_asistencia = residentes.copy()
    residentes_con_asistencia["asistió_semana"] = residentes_con_asistencia["nombre"].isin(asistencia_total)

    # Show absent students report
    st.subheader("📉 Estudiantes sin asistencia este rango de fecha")

    # Get the list of absent students
    ausentes = residentes_con_asistencia[~residentes_con_asistencia["asistió_semana"]][["nombre"]]

    # Calculate total absent students
    num_ausentes = len(ausentes)

    # Display total absent students in a metric
    col1 = st.columns(1)[0]
    with col1:
        st.metric("Total ausentes", f"{num_ausentes}")

    # Show the list of absent students
    st.dataframe(ausentes, hide_index=True)

    # Download Excel with absent students
    if st.button("📥 Descargar reporte de ausentes"):
        output = "ausentes_semana.xlsx"
        ausentes.to_excel(output, index=False)
        with open(output, "rb") as f:
            st.download_button("Descargar Excel", f, output)