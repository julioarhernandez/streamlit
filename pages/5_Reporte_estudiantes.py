import streamlit as st
import pandas as pd
import datetime
from config import setup_page # Assuming db is implicitly used by load_attendance via utils
from utils import (
    load_attendance, load_students, save_students,
    get_module_on_date, get_highest_module_credit,
    format_date_for_display, create_filename_date_range,
    get_student_start_date, date_format, get_attendance_dates
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
if 'ciclo' in df_loaded.columns:
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



# --- Display and Manage Current Students ---
st.subheader(f"Estudiantes Actuales (Total: {len(df_loaded) if df_loaded is not None else 0})")

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
    def calculate_remaining_modules(row):
        try:
            student_name = row.get('nombre', '').strip()
            
            # Check if start date exists
            if pd.isna(row.get('fecha_inicio')) or not row['fecha_inicio']:
                print(f"Estudiante sin fecha de inicio: {student_name}")
                return 'Sin fecha de inicio'

            # Get the start date and check if it's in the future
            today = datetime.date.today()
            start_date = pd.to_datetime(row['fecha_inicio']).date()
            
            # If start date is in the future, return max credit (hasn't started yet)
            if start_date > today:
                max_credit = get_highest_module_credit(user_email)
                print(f"{student_name} comienza el {start_date} (futuro). Módulos restantes: {max_credit}")
                return str(max_credit)
                
            print(f"Buscando módulo para {student_name} en fecha: {start_date}")
            
            # Use the logged-in user's email for module lookup
            student_module = get_module_on_date(user_email, start_date)
            print(f"Módulo encontrado: {student_module}")

            if not student_module or 'credits' not in student_module:
                print(f"Módulo no encontrado o sin créditos para {student_name}")
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
        if remaining_str == '0':
            return "Graduado"
        elif remaining_str.isdigit() and int(remaining_str) > 0:
            return "En curso"
        elif remaining_str == 'Sin fecha de inicio':
            return "Sin fecha"
        elif remaining_str == 'Módulo no encontrado':
            return "Módulo no encontrado"
        else:
            return "Error"

    # Add remaining modules column
    df_loaded['Módulos Restantes'] = df_loaded.apply(calculate_remaining_modules, axis=1)
    df_loaded['Estado'] = df_loaded.apply(calculate_status, axis=1)
    if 'nombre' not in df_loaded.columns:
        st.error("Los datos de los estudiantes no tienen la columna 'nombre', que es obligatoria.")
    else:
        df_display = df_loaded.copy()
        
        st.info("Puede editar los nombres de los estudiantes directamente en la tabla. Los cambios se guardarán cuando haga clic en 'Guardar Cambios'.")
        
        # Make a copy of the dataframe for editing
        editable_df = df_display.copy()
        
        # Display the editable table
        edited_df = st.data_editor(
            editable_df, 
            disabled=True,  # Make all columns editable
            hide_index=True,
            column_config={
                "nombre": st.column_config.TextColumn(
                    "Nombre del Estudiante",
                    help="Edite el nombre del estudiante",
                    width="medium",
                    required=True
                ),
                "Módulos Restantes": st.column_config.TextColumn(
                    "Módulos Restantes",
                    help="Módulos restantes para completar el curso",
                    width="small"
                ),
                "Estado": st.column_config.TextColumn(
                    "Estado",
                    help="Estado del estudiante",
                    width="small"
                ),
                "fecha_inicio": st.column_config.TextColumn(
                    "Fecha de Inicio",
                    help="Fecha de inicio del estudiante",
                    width="small"
                ),
            },
            key="students_editor"
        )
    

elif df_loaded is not None and df_loaded.empty:
    st.info("La lista de estudiantes está actualmente vacía. Suba un archivo para agregar estudiantes.")
else:
    st.info("No se encontraron datos de estudiantes o falló la carga. Por favor, suba un archivo para comenzar.")