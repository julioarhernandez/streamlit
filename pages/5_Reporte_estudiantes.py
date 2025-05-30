import streamlit as st
import pandas as pd
import datetime
from config import setup_page # Assuming db is implicitly used by load_attendance via utils
from utils import (
    load_students,
    get_module_on_date, get_highest_module_credit
)

# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()
# --- End Login Check ---

setup_page("Reporte de Estudiantes")
df_loaded, _ = load_students()

# Remove 'ciclo' column if it exists
if df_loaded is not None and not df_loaded.empty and 'ciclo' in df_loaded.columns:
    df_loaded = df_loaded.drop(columns=['ciclo'])

# Manual Spanish day name mapping to avoid locale/encoding issues
SPANISH_DAY_NAMES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

# Main UI

# Date selectors for range
today = datetime.date.today()
# Default start date to the first day of the current month for a more common report view
default_start_date = today.replace(day=1) 

# Format date inputs with MM/DD/YYYY format
# col1, col2 = st.columns(2)



# --- Helper Functions ---
def calculate_remaining_modules(row):
    try:
        student_name = row.get('nombre', 'desconocido')
        user_email = st.session_state.get('email', '').replace('.', ',')
        
        # Get the student's start date
        start_date_str = row.get('fecha_inicio')
        if not start_date_str or pd.isna(start_date_str):
            return 'Sin fecha de inicio'
            
        # Get the module for the student's start date
        start_date = pd.to_datetime(start_date_str).date()
        student_module = get_module_on_date(user_email, start_date)
        
        if not student_module:
            return 'Módulo no encontrado'
            
        # Get the student's starting module credit
        student_credit = int(student_module['credits'])
        max_credit = get_highest_module_credit(user_email)
        
        print(f"Crédito del estudiante: {student_credit}, Máximo crédito: {max_credit}")
        
        if max_credit <= 1:
            return '0'  # Only one module exists
            
        # Calculate remaining modules in circular sequence
        if student_credit == 1:
            # If starting at module 1, they've completed all modules
            return '0'
        else:
            # Calculate modules from current to max, then from 1 to current-1
            remaining = (max_credit - student_credit) + (student_credit - 1)
            # Since we want to include the current module in the count
            remaining = max_credit - 1 if remaining > max_credit else remaining
            return str(remaining)
            
    except Exception as e:
        print(f"Error inesperado para {student_name}: {str(e)}")
        return 'Error'

def calculate_status(row):
    remaining_str = str(row.get('Módulos Restantes', '')).strip()
    today = datetime.date.today()
    
    try:
        # Check if start date is in the future
        if 'fecha_inicio' in row and pd.notna(row['fecha_inicio']):
            try:
                start_date = pd.to_datetime(row['fecha_inicio']).date()
                if today < start_date:
                    return "No iniciado"
            except (ValueError, TypeError):
                pass  # If date conversion fails, continue with normal status check
        
        # Check if student has graduated
        if 'fecha_fin_modulo' in row and pd.notna(row['fecha_fin_modulo']):
            try:
                module_end_date = pd.to_datetime(row['fecha_fin_modulo']).date()
                if today > module_end_date and remaining_str == '0':
                    return "Graduado"
            except (ValueError, TypeError):
                pass  # If date conversion fails, continue with normal status check
        
        # If not graduated and has started, check remaining modules
        if remaining_str == '0':
            return "Último"
        elif remaining_str.isdigit() and int(remaining_str) > 0:
            return "En curso"
        elif remaining_str == 'Sin fecha de inicio':
            return "Sin fecha"
        elif remaining_str == 'Módulo no encontrado':
            return "Módulo no encontrado"
        else:
            return "Error"
            
    except Exception as e:
        print(f"Error calculando estado para {row.get('nombre', 'desconocido')}: {str(e)}")
        return "Error"

def get_module_end_date(row):
    try:
        if pd.isna(row.get('fecha_inicio')) or not row['fecha_inicio']:
            return None
            
        start_date = pd.to_datetime(row['fecha_inicio']).date()
        user_email = st.session_state.get('email', '').replace('.', ',')
        student_module = get_module_on_date(user_email, start_date)
        
        if student_module and 'end_date' in student_module:
            return student_module['end_date']
        return None
    except Exception as e:
        print(f"Error obteniendo fecha de fin para {row.get('nombre', 'desconocido')}: {str(e)}")
        return None

# --- Display and Manage Current Students ---
if df_loaded is not None and not df_loaded.empty:
    # First, calculate all the necessary columns
    df_loaded['Módulos Restantes'] = df_loaded.apply(calculate_remaining_modules, axis=1)
    df_loaded['fecha_fin_modulo'] = df_loaded.apply(get_module_end_date, axis=1)
    df_loaded['Estado'] = df_loaded.apply(calculate_status, axis=1)
    
    # Format date columns
    if 'fecha_inicio' in df_loaded.columns:
        df_loaded['fecha_inicio'] = pd.to_datetime(df_loaded['fecha_inicio']).dt.strftime('%Y-%m-%d')
    if 'fecha_fin_modulo' in df_loaded.columns:
        df_loaded['fecha_fin_modulo'] = pd.to_datetime(df_loaded['fecha_fin_modulo']).dt.strftime('%Y-%m-%d')
    
    # Now calculate statistics
    total_students = len(df_loaded)
    graduated = len(df_loaded[df_loaded['Estado'] == 'Graduado']) if 'Estado' in df_loaded.columns else 0
    in_progress = len(df_loaded[df_loaded['Estado'] == 'En curso']) if 'Estado' in df_loaded.columns else 0
    last_module = len(df_loaded[df_loaded['Estado'] == 'Último']) if 'Estado' in df_loaded.columns else 0
    

    a, b, c, d, e = st.columns([2,2,2,2,2])

    a.metric("Total", total_students, border=True)
    b.metric("En Curso", in_progress, border=True)

    c.metric("Último Módulo", last_module, border=True)
    d.metric("Graduados", graduated, border=True)
    e.metric("No comenzado", total_students - in_progress - last_module - graduated, border=True)
else:
    st.subheader("Estudiantes Actuales (Total: 0)")

if df_loaded is not None and not df_loaded.empty:
    # Get highest module credit for the user
    user_email = st.session_state.get('email', '').replace('.', ',')
    max_credit = get_highest_module_credit(user_email)
    print(f"Max Credit: {max_credit}")

    # Get current module info (optional, but keeping it)
    current_module = get_module_on_date(user_email)
    print(  f"Current Module: {current_module}")
    current_credit = int(current_module.get('credits', 0)) if current_module and 'credits' in current_module else 0
    print(f"Current Credit: {current_credit}")

    # Calculate remaining modules for each student in circular sequence
    # The 'calculate_remaining_modules' and 'calculate_status' functions are already defined at the top of the file
    # We'll use those functions to calculate the remaining modules and status for each student

    # The 'Estado' column is now calculated at the beginning of the file
    if 'nombre' not in df_loaded.columns:
        st.error("Los datos de los estudiantes no tienen la columna 'nombre', que es obligatoria.")
    else:
        df_display = df_loaded.copy()
        
        # st.info("Puede editar los nombres de los estudiantes directamente en la tabla. Los cambios se guardarán cuando haga clic en 'Guardar Cambios'.")
        
        # Define the column order
        column_order = ["nombre", "modulo", "fecha_inicio", "fecha_fin_modulo", "Módulos Restantes", "Estado"]
        
        # Make a copy of the dataframe with the desired column order
        editable_df = df_display[column_order].copy()
        
        # Display the editable table
        edited_df = st.data_editor(
            editable_df, 
            disabled=True,
            hide_index=True,
            column_config={
                "nombre": st.column_config.TextColumn(
                    "Nombre del Estudiante",
                    help="Edite el nombre del estudiante",
                    width="medium",
                    required=True
                ),
                "modulo": st.column_config.TextColumn(
                    "Módulo de Inicio",
                    help="Módulo del estudiante",
                    width="small"
                ),
                "fecha_inicio": st.column_config.TextColumn(
                    "Fecha de Inicio",
                    help="Fecha de inicio del estudiante",
                    width="small"
                ),
                "fecha_fin_modulo": st.column_config.TextColumn(
                    "Fecha de Fin",
                    help="Fecha de finalización del módulo actual",
                    width="small"
                ),
                "Módulos Restantes": st.column_config.TextColumn(
                    "Restantes",
                    help="Módulos restantes para completar el curso",
                    width="small"
                ),
                "Estado": st.column_config.TextColumn(
                    "Estado",
                    help="Estado del estudiante",
                    width="small"
                )
            },
            key="students_editor"
        )
    

elif df_loaded is not None and df_loaded.empty:
    st.info("La lista de estudiantes está actualmente vacía. Suba un archivo para agregar estudiantes.")
else:
    st.info("No se encontraron datos de estudiantes o falló la carga. Por favor, suba un archivo para comenzar.")