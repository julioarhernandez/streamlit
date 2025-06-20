import streamlit as st
import pandas as pd
from config import setup_page
from utils_admin import admin_get_student_group_emails, find_students

# def create_whatsapp_link(phone: str) -> str:
#     if pd.isna(phone) or not str(phone).strip():
#         return ""
#     phone = ''.join(filter(str.isdigit, str(phone)))
#     return f"https://wa.me/{phone}" if phone else ""

# def create_teams_link(email: str) -> str:
#     if pd.isna(email) or not str(email).strip() or '@' not in str(email):
#         return ""
#     return f"https://teams.microsoft.com/l/chat/0/0?users={email}"

# --- Initialize session state variables at the very top ---



# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()
# --- End Login Check ---

# This ensures they exist before any part of the script tries to access them.
# if 'all_students_df' not in st.session_state:
#     st.session_state['all_students_df'] = pd.DataFrame() # Initialize as empty DataFrame

# # Cargar datos de estudiantes desde Firebase y guardalos en session
# if not st.session_state['all_students_df'].empty:
#     # Aquí carga la tabla completa desde Firebase
#     st.session_state['all_students_df'] = find_students(student_name, modules_selected_course)
# else:
#     # Ya está cargada
#     df_students = st.session_state['all_students_df']


# Setup page title (now that config is done and user is logged in)
setup_page("Buscador de Estudiantes por Administrador")

course_emails = admin_get_student_group_emails()

modules_selected_course = None # Initialize modules_selected_course before the if/else block

if course_emails:
    full_emails_for_options = course_emails.copy() # Good practice to copy if you modify original later
    course_options = {
        email: {
            'label': email.capitalize().split('@')[0], # Display part without domain
            'value': email                              # Full email with domain
        }
        for email in full_emails_for_options
    }

else:
    st.warning("No se encontraron cursos disponibles.")
    modules_selected_course = None # Ensure it's explicitly None if no courses


# Usamos un formulario para capturar los datos
with st.form("student_form"):
    # Creamos tres columnas
    col1, col2, col3 = st.columns(3)
    
    # Campos dentro de cada columna
    with col1:
        student_name = st.text_input("Nombre del Estudiante")
    
    with col2:
        modules_selected_course = st.selectbox(
            "Curso",
            options=full_emails_for_options,
            format_func=lambda x: course_options[x]['label'],
            index=0,
            key="course_selector" # Added key for consistency
        )
        
    
    with col3:
        status = st.selectbox(
            "Estatus",
            options=["- No seleccionado -","Graduado", "En curso", "No iniciado"]
        )
    
    # Botón para enviar el formulario
    submitted = st.form_submit_button("Buscar")



if submitted:
    if student_name:
        results = find_students(student_name, modules_selected_course)
        results = results[[
            'nombre', 'email', 'telefono', 'modulo', 'fecha_inicio', 'modulo_fin_name', 'fecha_fin'
        ]]
        results = results.rename(columns={
            'nombre': 'Nombre',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'modulo': 'Módulo (Inicio)',
            'fecha_inicio': 'Fecha de Inicio',
            'modulo_fin_name': 'Módulo (Final)',
            'fecha_fin': 'Fecha de Finalización'
        })
        hide_columns = ['modulo_fin_id', 'id', 'canvas_id', 'modulo_fin_id']
        results = results.loc[:, ~results.columns.isin(hide_columns)]

        if not results.empty:
            st.success(f"✅ Se encontraron {len(results)} estudiante(s) con **{student_name}** en **{modules_selected_course.split('@')[0]}**")
            st.write(results)
        else:
            st.warning("No se encontraron estudiantes que coincidan.")
    else:
        st.warning("⚠️ Por favor, complete todos los campos obligatorios.")