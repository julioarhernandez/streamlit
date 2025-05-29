import streamlit as st
import pandas as pd
from config import setup_page
from utils import save_students, load_students

# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop() 
# --- End Login Check ---

# Setup page title (now that config is done and user is logged in)
setup_page("Gestión de Estudiantes")

# Load current students to display count
df_loaded, _ = load_students()
if df_loaded is not None and not df_loaded.empty:
    st.subheader(f"Total de Estudiantes Registrados: {len(df_loaded)}")
    st.divider()

# Main UI
# st.header("Gestionar Estudiantes") # st.title is usually sufficient for the main page title

# Create tabs for different input methods
tab1, tab2 = st.tabs(["📤 Subir Archivo", "✏️ Ingresar Texto"])

with tab1:
    st.subheader("Cargar desde Archivo")
    uploaded_file = st.file_uploader(
        "Seleccione un archivo CSV o Excel con los estudiantes",
        type=['csv', 'xlsx', 'xls'],
        key="file_uploader"
    )

with tab2:
    st.subheader("Ingresar Nombres Manualmente")
    students_text_area = st.text_area(
        "Ingrese un nombre de estudiante por línea",
        height=150,
        key="text_area_input"
    )
    submit_add_students_text = st.button("Agregar Estudiantes desde Texto")

if uploaded_file is not None:
    try:
        df_upload = pd.read_csv(uploaded_file)
    
        df_upload.columns = df_upload.columns.str.lower().str.strip()
        
        required_columns = {'nombre'}
        missing_columns = required_columns - set(df_upload.columns)
        
        if missing_columns:
            st.error(f"Error: El archivo subido no contiene las columnas requeridas: {', '.join(missing_columns)}. " 
                    f"Por favor asegúrese de que su archivo incluya estas columnas: nombre")
        else:
            df_upload['nombre'] = df_upload['nombre'].astype(str).str.strip()
            
            st.subheader("Vista Previa del Archivo Subido")
            st.write(f"Total de estudiantes en el archivo: {len(df_upload)}")
            st.dataframe(df_upload)
            
            if st.button("Guardar Estudiantes Subidos (reemplaza la lista existente)"):
                if save_students(df_upload):
                    st.success("¡Datos de estudiantes del archivo guardados exitosamente! La lista existente fue reemplazada.")
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error procesando el archivo: {str(e)}")
        st.error("Por favor, asegúrese de que el archivo no esté abierto en otro programa e inténtelo de nuevo.")

st.divider()

# --- Add Multiple Students via Text Area ---
if 'text_area_input' in st.session_state and st.session_state.text_area_input and submit_add_students_text:
    if not students_text_area.strip():
        st.warning("El área de texto está vacía. Por favor, ingrese nombres de estudiantes.")
    else:
        lines = students_text_area.strip().split('\n')
        potential_new_names = [line.strip() for line in lines if line.strip()]
        
        if not potential_new_names:
            st.warning("No se encontraron nombres de estudiantes válidos en el área de texto después del procesamiento.")
        else:
            current_students_df, _ = load_students()
            if current_students_df is None:
                current_students_df = pd.DataFrame(columns=['nombre'])
            
            if 'nombre' not in current_students_df.columns:
                current_students_df['nombre'] = pd.Series(dtype='str')
            else:
                current_students_df['nombre'] = current_students_df['nombre'].astype(str)

            existing_normalized_names = set(current_students_df['nombre'].str.lower().str.strip())
            
            added_count = 0
            skipped_names = []
            students_to_add_list = []
            
            unique_potential_new_names = []
            seen_in_input = set()
            for name in potential_new_names:
                normalized_name = name.lower().strip()
                if normalized_name not in seen_in_input:
                    unique_potential_new_names.append(name)
                    seen_in_input.add(normalized_name)
            
            for name in unique_potential_new_names:
                normalized_name = name.lower().strip()
                if normalized_name not in existing_normalized_names:
                    students_to_add_list.append({'nombre': name})
                    added_count += 1
                else:
                    skipped_names.append(name)
            
            if not students_to_add_list:
                st.info("No hay nuevos estudiantes para agregar. Todos los nombres proporcionados ya existen o eran duplicados en la entrada.")
                if skipped_names:
                    st.caption(f"Nombres omitidos (ya existen o duplicados): {', '.join(skipped_names)}")
            else:
                new_students_df = pd.DataFrame(students_to_add_list)
                updated_students_df = pd.concat([current_students_df, new_students_df], ignore_index=True)
                
                if save_students(updated_students_df):
                    st.success(f"¡{added_count} estudiante(s) agregado(s) exitosamente!")
                    if skipped_names:
                        st.caption(f"Nombres omitidos (ya existen o duplicados en la entrada): {', '.join(skipped_names)}")
                    st.rerun()
                else:
                    st.error("Error al agregar estudiantes desde el área de texto.")

st.divider()

# --- Display and Manage Current Students ---
st.subheader(f"Estudiantes Actuales (Total: {len(df_loaded) if df_loaded is not None else 0})")
df_loaded, _ = load_students()

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
