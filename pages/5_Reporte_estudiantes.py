import streamlit as st
import pandas as pd
import datetime
from config import setup_page # Assuming db is implicitly used by load_attendance via utils
from utils import load_attendance, load_students # Use the centralized functions
from utils import format_date_for_display, create_filename_date_range, get_student_start_date, date_format, get_attendance_dates

# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()
# --- End Login Check ---

setup_page("Reporte de Estudiantes")
df_loaded, _ = load_students()

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
col1, col2 = st.columns(2)



# --- Display and Manage Current Students ---
st.subheader(f"Estudiantes Actuales (Total: {len(df_loaded) if df_loaded is not None else 0})")

if df_loaded is not None and not df_loaded.empty:
    if 'nombre' not in df_loaded.columns:
        st.error("Los datos de los estudiantes no tienen la columna 'nombre', que es obligatoria.")
    else:
        df_display = df_loaded.copy()
        if '🗑️' not in df_display.columns:
            df_display.insert(0, '🗑️', False)
        
        disabled_columns = [col for col in df_loaded.columns if col != '🗑️']

        st.info("Puede editar los nombres de los estudiantes directamente en la tabla. Los cambios se guardarán cuando haga clic en 'Guardar Cambios'.")
        
        # Make a copy of the dataframe for editing
        editable_df = df_display.copy()
        
        # Display the editable table
        edited_df = st.data_editor(
            editable_df, 
            disabled=[],  # Make all columns editable
            hide_index=True,
            column_config={
                "🗑️": st.column_config.CheckboxColumn(
                    "🗑️",
                    help="Seleccione estudiantes para eliminar",
                    default=False,
                    width="small"
                ),
                "nombre": st.column_config.TextColumn(
                    "Nombre del Estudiante",
                    help="Edite el nombre del estudiante",
                    width="large",
                    required=True
                )
            },
            key="students_editor"
        )
        
        # Add save button
        if st.button("💾 Guardar Cambios", key="save_changes_btn"):
            # Check if there are any changes
            if not edited_df['nombre'].equals(editable_df['nombre']):
                # Create a copy of the original dataframe to modify
                updated_df = df_loaded.copy()
                # Update only the names that have changed
                name_changes = edited_df[edited_df['nombre'] != editable_df['nombre']]
                
                # Apply changes to the original dataframe
                for idx, row in name_changes.iterrows():
                    original_idx = df_loaded.index[idx]
                    updated_df.at[original_idx, 'nombre'] = row['nombre']
                
                # Save the updated dataframe
                if save_students(updated_df):
                    st.success("¡Cambios guardados exitosamente!")
                    # Add a button to refresh the page to see changes
                    if st.button("Actualizar página"):
                        st.rerun()
                else:
                    st.error("Error al guardar los cambios. Intente nuevamente.")
            else:
                st.info("No se detectaron cambios para guardar.")
        students_selected_for_deletion = edited_df[edited_df['🗑️'] == True]

        if not students_selected_for_deletion.empty:
            if st.button("Eliminar Estudiantes Seleccionados", type="primary"):
                names_to_delete = students_selected_for_deletion['nombre'].tolist()
                
                current_students_df_from_db, _ = load_students()
                if current_students_df_from_db is None:
                    st.error("No se pudieron recargar los datos de los estudiantes para realizar la eliminación. Por favor, inténtelo de nuevo.")
                else:
                    normalized_names_to_delete = {str(name).lower().strip() for name in names_to_delete}
                    
                    students_to_keep_df = current_students_df_from_db[
                        ~current_students_df_from_db['nombre'].astype(str).str.lower().str.strip().isin(normalized_names_to_delete)
                    ]
                    
                    if save_students(students_to_keep_df):
                        st.success(f"¡{len(names_to_delete)} estudiante(s) eliminado(s) exitosamente!")
                        st.rerun()
                    else:
                        st.error("Error al guardar los cambios después de intentar eliminar estudiantes.")
        elif any(edited_df['🗑️']):
             pass 

elif df_loaded is not None and df_loaded.empty:
    st.info("La lista de estudiantes está actualmente vacía. Suba un archivo para agregar estudiantes.")
else:
    st.info("No se encontraron datos de estudiantes o falló la carga. Por favor, suba un archivo para comenzar.")