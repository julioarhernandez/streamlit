import streamlit as st
import pandas as pd
import datetime
import time
import math
import uuid
from config import setup_page, db
from utils import set_last_updated, get_last_updated, get_available_modules  
from utils_admin import admin_get_student_group_emails

# --- Page Setup and Login Check ---
setup_page("Gestión de Módulos por Administrador")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

# --- Initialize session state variables at the very top ---
# This ensures they exist before any part of the script tries to access them.
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0
if 'modules_df_by_course' not in st.session_state:
    st.session_state.modules_df_by_course = {} # This will store DataFrames per course
# --- End Initialize session state variables ---

# --- Select Course ---
st.subheader("1. Seleccionar Curso")

# Get available courses (emails)
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

    modules_selected_course = st.selectbox(
        "Seleccione un Curso para agregar a los nuevos módulos:",
        options=full_emails_for_options,
        format_func=lambda x: course_options[x]['label'],
        index=0,
        key="course_selector" # Added key for consistency
    )

else:
    st.warning("No se encontraron cursos disponibles.")
    modules_selected_course = None # Ensure it's explicitly None if no courses


# --- Load current students based on modules_selected_course ---
# This block uses the cached function and stores the result in session state.
# This ensures the database is read only once per course per session.

# if modules_selected_course:
#     if modules_selected_course not in st.session_state.modules_df_by_course:
#         df_loaded, _ = get_current_students_data(modules_selected_course) # Use the cached function
#         if df_loaded is not None:
#             st.session_state.modules_df_by_course[modules_selected_course] = df_loaded
#         else:
#             st.session_state.modules_df_by_course[modules_selected_course] = pd.DataFrame() # Store an empty DataFrame on failure
#             st.warning(f"No se pudieron cargar estudiantes para el curso: {modules_selected_course}. Iniciando con una lista vacía.")
#     else:
#         df_loaded = st.session_state.modules_df_by_course[modules_selected_course]
# else:
#     df_loaded = pd.DataFrame() # Provide an empty DataFrame if no course is selected
#     st.info("Por favor, seleccione un curso para cargar los estudiantes.")

# print("\nLoaded df_loaded (from DB/Session State):\n", df_loaded)
# print("\nSession State (modules_df_by_course):\n", st.session_state.modules_df_by_course)

# --- Select Module ---
if modules_selected_course: # Only show module selection if a course is selected
    st.divider()
    st.subheader("2. Seleccionar Módulo")

    try:
        modules_last_updated = get_last_updated('modules', modules_selected_course)
        module_options = get_available_modules(modules_selected_course, modules_last_updated)

        if module_options:
            selected_module = st.selectbox(
                "Seleccione un módulo para agregar a los nuevos estudiantes:",
                options=module_options,
                format_func=lambda x: x['label'],
                index=0,
                key="module_selector" # Added key for consistency
            )

            # Store selected module in session state for later use
            if selected_module: # Ensure a module is actually selected
                st.session_state.modules_selected_module = selected_module
                st.session_state.modules_selected_module_id = selected_module['module_id']
                st.session_state.modules_selected_ciclo = selected_module['ciclo']
        else:
            st.info("No hay módulos disponibles. Por favor, agregue módulos en la sección de Módulos.")

    except Exception as e:
        st.error(f"Error al cargar los módulos: {str(e)}")
