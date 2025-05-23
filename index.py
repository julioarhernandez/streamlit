import streamlit as st
import pandas as pd
import sys
import os

# Print environment information
# print("Python version:", sys.version, file=sys.stderr)
# print("Streamlit version:", st.__version__, file=sys.stderr)
# print("Current working directory:", os.getcwd(), file=sys.stderr)
# print("Files in directory:", os.listdir('.'), file=sys.stderr)
import os
import glob
from datetime import datetime, timedelta
import io
from copy import deepcopy
from typing import List, Tuple, Optional, Dict, Any, Union
import tempfile
import uuid
import json
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import json
from firebase_config import save_user_session, get_user_last_session, save_user_files, get_user_sessions

# print("Starting app...", file=sys.stderr)

# Load credentials from YAML file
try:
    with open('credentials.yaml') as file:
        credentials = yaml.load(file, Loader=SafeLoader)
    
    # Debug credentials structure (without showing sensitive data)
    print("\nCredentials structure:")
    if isinstance(credentials, dict):
        print(f"Top-level keys: {list(credentials.keys())}")
        if 'credentials' in credentials:
            print("'credentials' key exists")
            if 'usernames' in credentials['credentials']:
                print("'usernames' key exists under 'credentials'")
                print(f"Number of users: {len(credentials['credentials']['usernames'])}")
            else:
                print("WARNING: 'usernames' key missing under 'credentials'")
        else:
            print("WARNING: 'credentials' key missing")
        
        if 'cookie' in credentials:
            print("'cookie' key exists with these subkeys:", list(credentials['cookie'].keys()))
        else:
            print("WARNING: 'cookie' key missing")
    else:
        print(f"WARNING: credentials is not a dictionary, it's {type(credentials)}")
    
    # Validate credentials structure
    if not all(key in credentials for key in ['credentials', 'cookie']):
        st.error("Formato de credenciales inválido. Asegúrate de que el archivo credentials.yaml tenga la estructura correcta.")
        st.stop()
    
    # Ensure the credentials structure is correct for streamlit-authenticator 0.4.2
    if 'credentials' in credentials and 'usernames' not in credentials['credentials']:
        # Create the expected structure
        credentials = {
            'credentials': {
                'usernames': credentials.get('credentials', {})
            },
            'cookie': credentials.get('cookie', {
                'name': 'attendance_cookie',
                'key': 'attendance_signature_key',
                'expiry_days': 30
            })
        }
        
except FileNotFoundError:
    st.error("Error: No se encontró el archivo de credenciales (credentials.yaml)")
    st.stop()
except Exception as e:
    st.error(f"Error al cargar las credenciales: {str(e)}")
    st.stop()

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

def cargar_lista_residentes(uploaded_file=None):
    """Carga la lista de residentes desde el archivo subido o desde la sesión"""
    if uploaded_file is not None:
        try:
            # First, check if the file has content
            file_content = uploaded_file.getvalue()
            if len(file_content) == 0:
                st.error("El archivo está vacío. Por favor, sube un archivo con datos.")
                return pd.DataFrame()
            
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            
            # Try reading as CSV with different encodings
            encodings_to_try = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings_to_try:
                try:
                    uploaded_file.seek(0)  # Reset file pointer for each attempt
                    df = pd.read_csv(uploaded_file, encoding=encoding)
                    break  # If successful, exit the loop
                except UnicodeDecodeError:
                    continue  # Try next encoding
                except pd.errors.EmptyDataError:
                    st.error("El archivo CSV no contiene columnas o datos. Por favor, verifica el formato.")
                    return pd.DataFrame()
                except Exception as e:
                    # If it's not an encoding issue, break and report the error
                    st.error(f"Error al leer el archivo CSV: {str(e)}")
                    return pd.DataFrame()
            
            # If all encodings failed
            if df is None:
                st.error("No se pudo leer el archivo con ninguna codificación compatible. Por favor, verifica el formato.")
                return pd.DataFrame()
            
            # Validate that the dataframe has data
            if df.empty:
                st.error("El archivo no contiene datos. Por favor, sube un archivo con datos.")
                return pd.DataFrame()
                
            # Validate that the dataframe has at least one column
            if len(df.columns) == 0:
                st.error("El archivo no contiene columnas. Por favor, verifica el formato.")
                return pd.DataFrame()
                
            # Update session state
            st.session_state.residentes_df = df
            st.session_state.residentes_filename = uploaded_file.name
            return df
            
        except Exception as e:
            st.error(f"Error al cargar el archivo de residentes: {str(e)}")
            st.error("Asegúrate de que el archivo sea un CSV válido con la codificación correcta.")
            return pd.DataFrame()
    
    # Return from session state if available
    if 'residentes_df' in st.session_state and not st.session_state.residentes_df.empty:
        return st.session_state.residentes_df
    
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


# --- Authentication ---

# Set page config
st.set_page_config(
    page_title="Sistema de Asistencia",
    page_icon="📋",
    layout="wide"
)

# Main container
main_container = st.container()
with main_container:
    st.title("Sistema de Asistencia")

# Initialize session state variables for authentication
if 'authentication_status' not in st.session_state:
    st.session_state.authentication_status = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'name' not in st.session_state:
    st.session_state.name = None
if 'user_session_id' not in st.session_state:
    st.session_state.user_session_id = str(uuid.uuid4())

# Simple login/logout functions
def login(username, password):
    """Simple login function that checks credentials"""
    if (
        'credentials' in credentials
        and 'usernames' in credentials['credentials']
        and username in credentials['credentials']['usernames']
    ):
        user_creds = credentials['credentials']['usernames'][username]
        if password == user_creds.get('password'):
            return True, user_creds.get('name', username)
    return False, None

def logout():
    """Clear session state to log out"""
    st.session_state.authentication_status = False
    st.session_state.username = None
    st.session_state.name = None
    # Keep other session state values that are not related to authentication
    if 'residentes_df' in st.session_state:
        st.session_state.residentes_df = pd.DataFrame()
    if 'residentes_filename' in st.session_state:
        st.session_state.residentes_filename = None
    if 'residentes_uploaded' in st.session_state:
        st.session_state.residentes_uploaded = False
    if 'residentes_file' in st.session_state:
        st.session_state.residentes_file = None

# Display login form if not authenticated
if not st.session_state.authentication_status:
    with main_container:
        st.subheader("Iniciar sesión")
        
        # Simple login form
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        login_button = st.button("Iniciar sesión")
        
        if login_button and username and password:
            auth_success, name = login(username, password)
            if auth_success:
                st.session_state.authentication_status = True
                st.session_state.username = username
                st.session_state.name = name
                
                # Save session to Firebase
                try:
                    session_data = {
                        'username': username,
                        'name': name,
                        'login_time': datetime.now().isoformat(),
                        'session_id': st.session_state.user_session_id,
                        'user_agent': st.query_params.get('user_agent', [''])[0] if hasattr(st, 'query_params') else ''
                    }
                    
                    save_user_session(username, session_data)
                    st.success(f"Bienvenido, {name}!")
                    st.rerun()
                except Exception as e:
                    st.warning(f"Sesión iniciada, pero no se pudo guardar la información: {str(e)}")
            else:
                st.error("Usuario o contraseña incorrectos")

# Show logout button in sidebar if authenticated
if st.session_state.authentication_status:
    with st.sidebar:
        st.success(f'Conectado como: {st.session_state["name"]}')
        if st.button("Cerrar sesión"):
            logout()
            st.rerun()
# If we get here, authentication is required
if not st.session_state.authentication_status:
    st.warning("Por favor inicia sesión para continuar")
    st.stop()


# After authentication block
if 'username' in st.session_state and st.session_state['authentication_status']:
    username = st.session_state['username']
    name = st.session_state['name']
    
    session_data = {
        'login_time': datetime.now().isoformat(),
        'user_agent': st.query_params.get('user_agent', [''])[0] if hasattr(st, 'query_params') else '',
        'session_id': str(uuid.uuid4())
    }
    
    # Check for existing session data
    last_session = get_user_last_session(username)
    
    # If we have a previous session with files, load them
    if last_session:
        if last_session.get('last_residentes'):
            residentes_data = last_session['last_residentes']
            st.session_state.residentes_df = pd.DataFrame(residentes_data.get('content', []))
            st.session_state.residentes_filename = residentes_data.get('filename', 'residentes.csv')
            st.session_state.residentes_uploaded = True
            
        if last_session.get('last_asistencia'):
            asistencia_data = last_session['last_asistencia']
            st.session_state.asistencia_files = asistencia_data.get('content', [])
            st.session_state.asistencia_uploaded = True
    
    # Save the current session
    save_user_session(username, session_data)

    # Add a button to view session history
    if st.sidebar.button("Ver historial de sesiones"):
        sessions = get_user_sessions(username)
        if sessions:
            st.sidebar.subheader("Tus sesiones anteriores:")
            for i, session in enumerate(sessions, 1):
                st.sidebar.write(f"Sesión {i}: {session.get('login_time')}")
        else:
            st.sidebar.info("No hay sesiones anteriores registradas")
    
    # Add logout button
    if 'authenticator' in locals() and authenticator is not None:
        authenticator.logout('Cerrar sesión', 'sidebar', key='unique_logout')
else:
    st.error("Debes iniciar sesión para acceder a esta aplicación.")
    st.stop()

# Initialize session state for resident data
if 'residentes_df' not in st.session_state:
    st.session_state.residentes_df = pd.DataFrame()
    st.session_state.residentes_filename = None

# Initialize session state for file uploads
if 'residentes_uploaded' not in st.session_state:
    st.session_state.residentes_uploaded = False
if 'asistencia_uploaded' not in st.session_state:
    st.session_state.asistencia_uploaded = False
if 'residentes_file' not in st.session_state:
    st.session_state.residentes_file = None
if 'asistencia_files' not in st.session_state:
    st.session_state.asistencia_files = []

# --- Main Application UI ---
st.title("📋 Seguimiento de Asistencia")

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

    # Process resident file upload
    if uploaded_residentes is not None and 'username' in st.session_state:
        try:
            # Try to load the file to validate it using our enhanced function
            df = cargar_lista_residentes(uploaded_residentes)
            
            if not df.empty:
                # Update session state
                st.session_state.residentes_uploaded = True
                st.session_state.residentes_file = uploaded_residentes
                st.session_state.residentes_df = df
                st.session_state.residentes_filename = uploaded_residentes.name
                
                # Show success message
                st.success(f"✅ Archivo de residentes cargado correctamente: {uploaded_residentes.name}")
                
                # Save to Firebase
                try:
                    save_user_files(
                        st.session_state.username,
                        residentes_data={
                            'content': df.to_dict('records'),
                            'filename': uploaded_residentes.name
                        }
                    )
                except Exception as e:
                    st.warning(f"El archivo se cargó correctamente pero no se pudo guardar en Firebase: {str(e)}")
            else:
                st.error("El archivo está vacío o no tiene el formato esperado.")
        except Exception as e:
            st.error(f"Error al procesar el archivo de residentes: {str(e)}")
    else:
        # If no file is uploaded, ensure the session state is properly set
        if 'residentes_uploaded' not in st.session_state:
            st.session_state.residentes_uploaded = False
            st.session_state.residentes_file = None

    # Process attendance files
    if uploaded_files and len(uploaded_files) > 0 and 'username' in st.session_state:
        try:
            asistencia_data = []
            processed_files = []
            
            for file in uploaded_files:
                try:
                    # Try to decode with utf-16 first (Zoom's default export format)
                    try:
                        content = file.getvalue().decode('utf-16')
                    except UnicodeDecodeError:
                        # If that fails, try other encodings
                        try:
                            content = file.getvalue().decode('utf-8')
                        except UnicodeDecodeError:
                            content = file.getvalue().decode('latin1')
                    
                    asistencia_data.append({
                        'filename': file.name,
                        'content': content
                    })
                    processed_files.append(file.name)
                except Exception as file_error:
                    st.error(f"Error al procesar el archivo {file.name}: {str(file_error)}")
            
            if processed_files:
                # Update session state
                st.session_state.asistencia_files = uploaded_files
                st.session_state.asistencia_uploaded = True
                st.write("[DEBUG] asistencia_uploaded set to True")
                
                # Show success message
                st.success(f"✅ Archivos de asistencia cargados correctamente: {', '.join(processed_files)}")
                
                # Save to Firebase
                try:
                    save_user_files(
                        st.session_state.username,
                        asistencia_data=asistencia_data
                    )
                except Exception as firebase_error:
                    st.warning(f"Los archivos se cargaron correctamente pero no se pudieron guardar en Firebase: {str(firebase_error)}")
        except Exception as e:
            st.error(f"Error al cargar los archivos de asistencia: {str(e)}")
    else:
        # If no files are uploaded, ensure the session state is properly set
        if 'asistencia_files' not in st.session_state:
            st.session_state.asistencia_files = []

# Show current resident file info
if 'residentes_filename' in st.session_state and st.session_state.residentes_filename:
    st.success(f"✅ Archivo cargado: {st.session_state.residentes_filename}")
    if st.button("🗑️ Limpiar archivo de Estudiantes"):
        st.session_state.residentes_df = pd.DataFrame()
        st.session_state.residentes_filename = None
        st.session_state.residentes_uploaded = False
        st.session_state.residentes_file = None
        st.rerun()
else:
    st.info("ℹ️ No se ha cargado ningún archivo de residentes.")

# Update overall flag
st.session_state.files_uploaded = (
    st.session_state.residentes_uploaded and st.session_state.asistencia_uploaded
)
    

# Debug output for troubleshooting file upload logic
st.write("residentes_uploaded:", st.session_state.get('residentes_uploaded'))
st.write("asistencia_uploaded:", st.session_state.get('asistencia_uploaded'))
st.write("files_uploaded:", st.session_state.get('files_uploaded'))

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

# Store in session for faster access
st.session_state.residentes_df = residentes

# Get attendance for the selected date range
asistencias_por_dia = asistencia_semana(fecha_inicio, fecha_fin, uploaded_files, st.session_state.skip_weekends)

# Create a DataFrame to store daily attendance
attendance_data = []

# Get attendance for each date in the range
for i, fecha in enumerate(pd.date_range(fecha_inicio, fecha_fin)):
    # Skip weekends if the checkbox is checked
    if st.session_state.skip_weekends and fecha.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        continue
        
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

# Create a DataFrame for the attendance table
attendance_df = pd.DataFrame(attendance_data)

st.header("3. Reportes")


# Display the attendance table
st.subheader("📊 Reporte diario de asistencia")

# Show total attendance metrics only if it not a range of dates
if fecha_inicio == fecha_fin:
    # Add a metric for total attendance only for single dates
    with st.container():
        col1, col2, _ = st.columns([2, 2, 6])
        with col1:
            st.metric("Total Mañana", f"{attendance_df['Mañana'].sum()}")
        with col2:
            st.metric("Total Tarde", f"{attendance_df['Tarde'].sum()}")

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