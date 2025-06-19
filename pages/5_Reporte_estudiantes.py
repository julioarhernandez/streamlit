import streamlit as st
import pandas as pd
import datetime
from config import setup_page
from utils import (
    load_students,
    get_module_on_date, get_highest_module_credit, get_last_updated,
    get_module_name_by_id
)

# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()
# --- End Login Check ---

setup_page("Reporte de Estudiantes")

students_last_updated = get_last_updated('students')
df_loaded, _ = load_students(students_last_updated)

if df_loaded is None or df_loaded.empty:
    st.info("No hay estudiantes registrados.")
else:
    # Clean and format the data
    if 'ciclo' in df_loaded.columns:
        df_loaded = df_loaded.drop(columns=['ciclo'])
    
    # Format date columns
    date_columns = ['fecha_inicio', 'fecha_fin']
    for col in date_columns:
        if col in df_loaded.columns:
            df_loaded[col] = pd.to_datetime(df_loaded[col], errors='coerce').dt.strftime('%m/%d/%Y')
    
    # Select and order columns to display
    display_columns = ['nombre', 'email', 'telefono', 'modulo', 'fecha_inicio', 'fecha_fin']
    display_columns = [col for col in display_columns if col in df_loaded.columns]
    
    # Get module names if modulo column exists
    if 'modulo' in df_loaded.columns:
        user_email = st.session_state.get('email', '').replace('.', ',')
        df_loaded['modulo_nombre'] = df_loaded['modulo'].apply(
            lambda x: get_module_name_by_id(user_email, str(x)) if pd.notna(x) else 'Sin módulo'
        )
    
    # Rename columns for display
    column_names = {
        'nombre': 'Nombre',
        'email': 'Correo Electrónico',
        'telefono': 'Teléfono',
        'modulo': 'Módulo (ID)',
        'modulo_nombre': 'Módulo',
        'fecha_inicio': 'Fecha de Inicio',
        'fecha_fin': 'Fecha de Finalización'
    }
    
    # Display the dataframe
    st.dataframe(
        df_loaded[display_columns].rename(columns=column_names),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Nombre": "Estudiante",
            "Correo Electrónico": "Email",
            "Teléfono": "Teléfono",
            "Módulo (ID)": "Módulo (Inicio)",
            "Fecha de Inicio": "Inicio",
            "Fecha de Finalización": "Fin"
        }
    )