import streamlit as st
import pandas as pd
from config import setup_page
from utils_admin import admin_get_student_group_emails, save_modules_to_db, admin_get_available_modules

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

# --- Select Module ---
if modules_selected_course: # Only show module selection if a course is selected
    st.divider()
    st.subheader("2. Seleccionar Módulo")

try:
    
    module_options = admin_get_available_modules(modules_selected_course)
    print("\n\nmodule_options\n\n ----- ", module_options)
    if module_options:
        df = pd.DataFrame(module_options)
        print("\n\nAvailable columns in module data:", df.columns.tolist())

        # Define your primary column mapping for known columns
        column_mapping = {
            'module_name': 'Nombre Módulo',
            'module_id': 'ID Módulo',
            'ciclo': 'Ciclo',
            'start_date': 'Fecha Inicio',
            'end_date': 'Fecha Fin',
            'duration_weeks': 'Duración',
            'credits': 'Orden',
            'description': 'Descripción',
            'firebase_key': 'Firebase Key'
        }

        # Dynamically create display_columns to include ALL columns present in the DataFrame
        # and create display names for them.
        display_columns = []
        reverse_display_names = {} # To map display names back to original for saving

        for col in df.columns:
            # Use the mapped name if available, otherwise use the original column name
            display_name = column_mapping.get(col, col)
            display_columns.append(display_name)
            reverse_display_names[display_name] = col # Store reverse mapping

        if not display_columns:
            st.warning("No se encontraron columnas válidas para mostrar.")
            st.json(module_options[0] if module_options else {})  # Show raw data for debugging
            st.stop()

        # Create a copy for display, renaming columns
        # Ensure only columns that exist in df are selected, and then rename them
        display_df = df.rename(columns=column_mapping)[display_columns].copy()
        
        # Hide specific columns from display
        columns_to_hide = ["Ciclo", "Firebase Key", "label", "ID Módulo"]  # Add any other columns you want to hide here
        display_df = display_df.drop(columns=[col for col in columns_to_hide if col in display_df.columns])
        
        # Convert date columns from string to datetime
        date_columns = ["Fecha Inicio", "Fecha Fin"]
        for date_col in date_columns:
            if date_col in display_df.columns:
                display_df[date_col] = pd.to_datetime(display_df[date_col], errors='coerce')

        # Define column configurations for st.data_editor
        editor_column_config = {
            "ID Módulo": st.column_config.TextColumn(disabled=True),
            "Fecha Inicio": st.column_config.DateColumn(format="MM/DD/YYYY"),
            "Fecha Fin": st.column_config.DateColumn(format="MM/DD/YYYY"),
            "Duración": st.column_config.NumberColumn(min_value=1, step=1),
            "Orden": st.column_config.NumberColumn(min_value=1, step=1),
            "Descripción": st.column_config.TextColumn(),
        }

        # Initialize session state for this course if not exists
        if modules_selected_course not in st.session_state.modules_df_by_course:
            st.session_state.modules_df_by_course[modules_selected_course] = display_df.copy()

        

        st.write("Editar módulos:")
        # Use the session state version for the editor
        edited_df = st.data_editor(
            st.session_state.modules_df_by_course[modules_selected_course],
            use_container_width=True,
            num_rows="dynamic",
            column_config=editor_column_config,
            key=f"main_editor_{modules_selected_course}"
        )

        # You update the session state with the (potentially problematic) edited data
        st.session_state.modules_df_by_course[modules_selected_course] = edited_df

        # This block cleans the data immediately after it has been edited.
        date_columns_to_reconvert = ["Fecha Inicio", "Fecha Fin"]
        for date_col in date_columns_to_reconvert:
            if date_col in st.session_state.modules_df_by_course[modules_selected_course].columns:
                st.session_state.modules_df_by_course[modules_selected_course][date_col] = pd.to_datetime(
                    st.session_state.modules_df_by_course[modules_selected_course][date_col], 
                    errors='coerce'
                )
        # Re-assign edited_df to the corrected dataframe from session state for consistency
        edited_df = st.session_state.modules_df_by_course[modules_selected_course]
        

        # Handle date recalculation for empty start dates
        if ((edited_df['Fecha Inicio'].isna()) | (edited_df['Fecha Fin'].isna())).any():
            st.warning("Algunos módulos tienen fecha de inicio o fin vacía. Por favor, revise y complete la información antes de guardar.")
            if st.button("Recalcular las fechas", key="recalcular_fechas"):
                # Find the last module with a valid order number
                valid_modules = edited_df[edited_df['Orden'].notna()]
                if not valid_modules.empty:
                    last_module = valid_modules.sort_values('Orden').iloc[-1]
                    last_orden = last_module['Orden']
                    
                    print(f"\n\nLast module with valid order:\n{last_module}")
                    
                    # Calculate the new start date (one day after the last module's end date)
                    if pd.notna(last_module['Fecha Fin']):
                        new_start_date = last_module['Fecha Fin'] + pd.DateOffset(days=1)
                        
                        # Find the row with None Orden and None Fecha Inicio
                        mask = (edited_df['Orden'].isna()) & (edited_df['Fecha Inicio'].isna())
                        
                        if mask.any():
                            # Create a fresh copy of the session state dataframe
                            updated_df = st.session_state.modules_df_by_course[modules_selected_course].copy()
                            
                            # Update the start date of the empty row
                            updated_df.loc[mask, 'Fecha Inicio'] = new_start_date
                            
                            # Debug info
                            print("\n\nUpdating empty row with start date:", new_start_date)
                            print("Updated row:", updated_df.loc[mask, ['Orden', 'Fecha Inicio', 'Fecha Fin']])

                            # Calculate the new end date (one week after the last module's start date)
                            
                            
                            # Update the session state with our modified copy
                            st.session_state.modules_df_by_course[modules_selected_course] = updated_df
                            st.rerun()
                        else:
                            st.warning("No se encontró ninguna fila vacía para actualizar.")
                    else:
                        st.warning("El último módulo no tiene fecha de fin definida.")
                else:
                    st.warning("No se encontraron módulos con orden válido.")
                st.rerun()

        # Add save button
        if st.button("💾 Guardar Cambios"):
            # Get the current state of the DataFrame from session_state as it reflects all edits and cleaning
            current_edited_df = st.session_state.modules_df_by_course[modules_selected_course]

            # Rename display columns back to original DB names for saving
            edited_df_for_save = current_edited_df.rename(columns=reverse_display_names)

            # Re-introduce the hidden columns from the original 'df' to preserve them.
            # We use the index to align the data correctly.
            # This ensures 'module_id', 'firebase_key', etc., are kept for existing rows.
            for col_to_preserve in df.columns:
                if col_to_preserve not in edited_df_for_save.columns:
                    # Align by index to avoid incorrect merging
                    edited_df_for_save[col_to_preserve] = df[col_to_preserve]

            # Convert the processed DataFrame to a list of dictionaries.
            # This handles new rows and is a safe format for DB operations.
            modules_to_save = edited_df_for_save.to_dict('records')

            # Final formatting pass before saving
            for module_data in modules_to_save:
                # Format dates to string, which is safe for databases (e.g., Firestore)
                for date_col in ['start_date', 'end_date']:
                    if date_col in module_data and pd.notna(module_data[date_col]):
                        # Convert pandas Timestamp to a string 'YYYY-MM-DD'
                        module_data[date_col] = module_data[date_col].strftime('%Y-%m-%d')
                    else:
                        module_data[date_col] = None # Ensure empty dates are None
            
            # Now, save the changes using the properly prepared list of modules
            if save_modules_to_db(modules_selected_course, modules_to_save):
                st.success("¡Cambios guardados exitosamente!")
                # Clean the state for the course to force a fresh reload next time
                if modules_selected_course in st.session_state.modules_df_by_course:
                    del st.session_state.modules_df_by_course[modules_selected_course]
                st.rerun()
    else:
        st.info("No hay módulos disponibles. Por favor, agregue módulos.") # Keep this message
except Exception as e:
    st.error(f"Error al cargar o procesar los módulos: {str(e)}")
