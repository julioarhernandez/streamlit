import streamlit as st
import pandas as pd
import datetime
import math
import uuid # For generating unique module IDs
from config import setup_page, db # Assuming db is initialized in config.py

# Function to save a new module to Firebase
def save_new_module_to_db(user_email, module_data):
    try:
        user_email_sanitized = user_email.replace('.', ',')
        # Create a new reference for a module, or use module_id if provided and unique
        # For simplicity, let's assume we push to create a new unique ID by Firebase
        db.child("modules").child(user_email_sanitized).push(module_data)
        return True
    except Exception as e:
        st.error(f"Error saving module to Firebase: {e}")
        return False

# Function to delete a module
def delete_module_from_db(user_email, module_id):
    st.write(f"Debug: delete_module_from_db called with user_email: {user_email}, module_id: {module_id}")
    if not user_email or not module_id:
        st.error("Error: Datos de usuario o ID de módulo no válidos.")
        return False
        
    try:
        user_email_sanitized = user_email.replace('.', ',')
        # Get module name before deleting for better feedback
        module_ref = db.child("modules").child(user_email_sanitized).child(module_id).get()
        module_name = module_ref.val().get('name', '') if module_ref.val() else 'Desconocido'
        st.write(f"Debug: module_name: {module_name}")
        # Delete the module
        db.child("modules").child(user_email_sanitized).child(module_id).remove()
        
        # Show success message
        st.toast(f"Módulo eliminado: {module_name} (ID: {module_id[-4:]})")
        return True
    except Exception as e:
        st.error(f"Error al eliminar el módulo: {str(e)}")
        return False

# Function to load all modules for the current user from Firebase.
def load_modules(user_email_from_session):
    if not user_email_from_session:
        return pd.DataFrame()
    try:
        user_email_sanitized = user_email_from_session.replace('.', ',')
        modules_data = db.child("modules").child(user_email_sanitized).get().val()

        if not modules_data:
            df = pd.DataFrame()
        elif isinstance(modules_data, list):
            processed_list = [item for item in modules_data if item is not None and isinstance(item, dict)]
            if not processed_list:
                df = pd.DataFrame()
            else:
                df = pd.DataFrame(processed_list)
        elif isinstance(modules_data, dict):
            processed_list = []
            for key, item in modules_data.items():
                if item is not None and isinstance(item, dict):
                    if 'module_id' not in item: # If item doesn't have its own module_id field
                        item['module_id'] = key # Use Firebase key as module_id
                    processed_list.append(item)
            if not processed_list:
                df = pd.DataFrame()
            else:
                df = pd.DataFrame(processed_list)
        else:
            st.warning(f"Unexpected data type for modules: {type(modules_data)}")
            df = pd.DataFrame()
        
        # Ensure all expected columns are present in the DataFrame
        expected_cols = ['module_id', 'name', 'description', 'credits', 'duration_weeks', 'created_at']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None # Add missing column and fill with None
        
        return df

    except Exception as e:
        st.error(f"Error loading modules from Firebase: {e}")
        # Return an empty DataFrame with expected columns in case of error too
        return pd.DataFrame(columns=expected_cols)

# --- Page Setup and Login Check ---
setup_page("Gestión de Módulos")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

user_email = st.session_state.get('email')

# Function to calculate end date based on start date and duration
def calculate_end_date(start_date, duration_weeks):
    if start_date and duration_weeks:
        return start_date + datetime.timedelta(weeks=duration_weeks)
    return None

# Initialize session state for dates if not exists
if 'module_duration_weeks' not in st.session_state:
    st.session_state.module_duration_weeks = 1
if 'ciclo1_inicio' not in st.session_state:
    st.session_state.ciclo1_inicio = datetime.date.today()
if 'ciclo2_inicio' not in st.session_state:
    st.session_state.ciclo2_inicio = datetime.date.today()

# --- FORM TO ADD NEW MODULE ---
st.subheader("Agregar Nuevo Módulo")

# Use a container for the form-like layout
with st.container():
    # Create two columns for Nombre and Descripción
    col_nombre, col_desc = st.columns([1, 1])  # Descripción gets more space as it's typically longer
    
    with col_nombre:
        module_name = st.text_input("Nombre del Módulo", key="new_module_name")
    
    with col_desc:
        module_description = st.text_input("Descripción", key="new_module_desc")
    
    # Create two columns for Orden and Duración
    col_orden, col_duracion = st.columns(2)
    
    with col_orden:
        module_credits = st.number_input("Orden", min_value=1, step=1, key="new_module_credits")
    
    with col_duracion:
        # Duration input with immediate update
        module_duration_weeks = st.number_input(
            "Duración (Semanas)", 
            min_value=1, 
            step=1, 
            key="new_module_duration",
            value=st.session_state.module_duration_weeks
        )
    
    # Update duration in session state if changed
    if module_duration_weeks != st.session_state.module_duration_weeks:
        st.session_state.module_duration_weeks = module_duration_weeks
        st.rerun()
    
    # Add date inputs for Cycle 1
    st.subheader("Ciclo 1")
    col1, col2 = st.columns(2)
    
    with col1:
        ciclo1_inicio = st.date_input(
            "Fecha de Inicio (MM/DD/YYYY)", 
            key="_ciclo1_inicio",
            value=st.session_state.ciclo1_inicio,
            format="MM/DD/YYYY"
        )
        
        # Update session state if date changes
        if ciclo1_inicio != st.session_state.ciclo1_inicio:
            st.session_state.ciclo1_inicio = ciclo1_inicio
            st.rerun()
    
    with col2:
        # Calculate end date using current values
        ciclo1_fin = calculate_end_date(st.session_state.ciclo1_inicio, st.session_state.module_duration_weeks)
        
        # Show toast when end date changes
        if 'prev_ciclo1_fin' not in st.session_state:
            st.session_state.prev_ciclo1_fin = None
            
        # if ciclo1_fin != st.session_state.prev_ciclo1_fin and st.session_state.prev_ciclo1_fin is not None:
        #     st.toast(f"Ciclo 1 - Nueva fecha de fin: {ciclo1_fin}")
            
        st.session_state.prev_ciclo1_fin = ciclo1_fin
        
        st.date_input(
            "Fecha de Fin (MM/DD/YYYY)",
            value=ciclo1_fin if ciclo1_fin else datetime.date.today(),
            key="ciclo1_fin_display",
            format="MM/DD/YYYY",
            disabled=True
        )
    
    # Add date inputs for Cycle 2
    st.subheader("Ciclo 2")
    col3, col4 = st.columns(2)
    
    with col3:
        ciclo2_inicio = st.date_input(
            "Fecha de Inicio (MM/DD/YYYY)",
            key="_ciclo2_inicio",
            value=st.session_state.ciclo2_inicio,
            format="MM/DD/YYYY"
        )
        
        # Update session state if date changes
        if ciclo2_inicio != st.session_state.ciclo2_inicio:
            st.session_state.ciclo2_inicio = ciclo2_inicio
            st.rerun()
    
    with col4:
        # Calculate end date using current values
        ciclo2_fin = calculate_end_date(st.session_state.ciclo2_inicio, st.session_state.module_duration_weeks)
        
        # Show toast when end date changes
        if 'prev_ciclo2_fin' not in st.session_state:
            st.session_state.prev_ciclo2_fin = None
            
        # if ciclo2_fin != st.session_state.prev_ciclo2_fin and st.session_state.prev_ciclo2_fin is not None:
        #     st.toast(f"Ciclo 2 - Nueva fecha de fin: {ciclo2_fin}")
            
        st.session_state.prev_ciclo2_fin = ciclo2_fin
        
        st.date_input(
            "Fecha de Fin (MM/DD/YYYY)",
            value=ciclo2_fin if ciclo2_fin else datetime.date.today(),
            key="ciclo2_fin_display",
            format="MM/DD/YYYY",
            disabled=True
        )
    
    # Add a submit button that will handle the form submission
    submitted_new_module = st.button("Agregar Módulo")

    if submitted_new_module and user_email:
        if not module_name:
            st.warning("El nombre del módulo es obligatorio.")
        else:
            new_module_data = {
                'module_id': str(uuid.uuid4()), # Generate a unique ID
                'name': module_name,
                'description': module_description,
                'credits': module_credits,
                'duration_weeks': module_duration_weeks,
                'ciclo1_inicio': ciclo1_inicio.isoformat() if 'ciclo1_inicio' in locals() else None,
                'ciclo1_fin': calculate_end_date(ciclo1_inicio, module_duration_weeks).isoformat() if 'ciclo1_inicio' in locals() and ciclo1_inicio else None,
                'ciclo2_inicio': ciclo2_inicio.isoformat() if 'ciclo2_inicio' in locals() else None,
                'ciclo2_fin': calculate_end_date(ciclo2_inicio, module_duration_weeks).isoformat() if 'ciclo2_inicio' in locals() and ciclo2_inicio else None,
                'created_at': datetime.datetime.now().isoformat()
            }
            if save_new_module_to_db(user_email, new_module_data):
                st.success(f"Módulo '{module_name}' guardado exitosamente!")
                st.rerun()
            else:
                st.error("No se pudo guardar el módulo.")
    elif submitted_new_module and not user_email:
        st.error("Error de sesión. No se pudo obtener el email del usuario.")

# --- DISPLAY/EDIT EXISTING MODULES ---
st.divider()
if user_email:
    modules_df_from_db = load_modules(user_email) # Renamed to clarify source

    # --- Debugging Information (Optional) ---
    # st.subheader("Información de Depuración de Módulos (Post-Carga)")
    # if isinstance(modules_df_from_db, pd.DataFrame):
    #     st.write("Columnas de modules_df:", modules_df_from_db.columns.tolist() if not modules_df_from_db.empty else "DataFrame vacío")
    #     st.write("Primeras filas de modules_df:", modules_df_from_db.head())
    #     st.write("¿modules_df está vacío?", modules_df_from_db.empty)
    # else:
    #     st.write("modules_df no es un DataFrame. Tipo:", type(modules_df_from_db))

    if modules_df_from_db.empty:
        st.info("No hay módulos existentes para este usuario. Puede agregar nuevos módulos utilizando el formulario anterior.")
    else:
        st.subheader("Módulos Existentes")
        
        # Store original module_ids to detect deletions
        if 'module_id' in modules_df_from_db.columns:
            original_module_ids = set(modules_df_from_db['module_id'].dropna().tolist())
        else:
            original_module_ids = set()
            st.warning("La columna 'module_id' no se encontró. La detección de eliminaciones no funcionará correctamente.")

        if 'ids_to_delete' not in st.session_state:
            st.session_state.ids_to_delete = set()

        # Configure date display format
        date_format = "MM/DD/YYYY"
        
        editable_cols_config = {
            "module_id": st.column_config.TextColumn("ID del Módulo", disabled=True, help="ID único del módulo, no editable."),
            "name": st.column_config.TextColumn("Nombre del Módulo", required=True),
            "description": st.column_config.TextColumn("Descripción"),
            "credits": st.column_config.NumberColumn("Orden", format="%d", min_value=1, help="Número de orden del módulo"),
            "duration_weeks": st.column_config.NumberColumn("Duración (Semanas)", format="%d", min_value=1),
            "ciclo1_inicio": st.column_config.DateColumn("Ciclo 1 Inicio", format=date_format, disabled=True),
            "ciclo1_fin": st.column_config.DateColumn("Ciclo 1 Fin", format=date_format, disabled=True),
            "ciclo2_inicio": st.column_config.DateColumn("Ciclo 2 Inicio", format=date_format, disabled=True),
            "ciclo2_fin": st.column_config.DateColumn("Ciclo 2 Fin", format=date_format, disabled=True)
            # 'created_at' could also be displayed as disabled if desired
        }
        
        display_cols_in_editor = []
        final_column_config = {}

        # Define the order of columns for display (module_id will be hidden but kept in data)
        display_columns = [
            'name', 
            'description', 
            'duration_weeks', 
            'credits',
            'ciclo1_inicio',
            'ciclo1_fin',
            'ciclo2_inicio',
            'ciclo2_fin'
        ]  # Include all date columns
        
        # Configure which columns are shown and how
        for col_key in display_columns:
            if col_key in modules_df_from_db.columns:
                display_cols_in_editor.append(col_key)
                if col_key in editable_cols_config:
                    final_column_config[col_key] = editable_cols_config[col_key]
        
        # Ensure module_id exists in the data even if not displayed
        if 'module_id' not in modules_df_from_db.columns:
            st.error("Error: 'module_id' no encontrado en los datos. No se puede mostrar el editor de módulos de forma segura.")
            st.stop()
            
        # Create the data editor with row deletion enabled
        st.write("Debug: modules_df_from_db before editor:", modules_df_from_db['module_id'].tolist() if 'module_id' in modules_df_from_db else "No module_id col")

        edited_df = st.data_editor(
            modules_df_from_db[['module_id'] + display_cols_in_editor].copy(),  # Try with .copy()
            column_config={
                **final_column_config,
                "module_id": None  # This hides the column from display
            },
            hide_index=True,
            num_rows="dynamic",
            key="modules_editor_main", # This key is important
            use_container_width=True,
            disabled=("module_id",), 
            on_change=None 
        )
        
        # --- Start of new section: Detect UI Deletions and Trigger Confirmation ---
        # This logic should be placed immediately after the st.data_editor call.
        # It replaces any previous logic that tried to handle deletions immediately or with a different UI.

        st.write("--- Debug Deletion Detection ---")
        st.write(f"Debug: original_module_ids: {original_module_ids}") 
        st.write(f"Debug: st.session_state.ids_to_delete (before detection): {st.session_state.ids_to_delete}")
        st.write(f"Debug: 'module_id' in edited_df.columns: {'module_id' in edited_df.columns}")
        if 'module_id' in edited_df.columns:
            st.write(f"Debug: edited_df['module_id'].dropna().tolist(): {edited_df['module_id'].dropna().tolist()}")
        st.write("--- End Debug Deletion Detection ---")
        
        # Detect if rows were removed in the data_editor UI and no confirmation is currently active
        if 'module_id' in edited_df.columns and not st.session_state.ids_to_delete:
            # 'original_module_ids' should be defined earlier, containing IDs from the DB load
            current_module_ids_in_editor = set(edited_df['module_id'].dropna().tolist())
            ids_to_delete_detected = original_module_ids - current_module_ids_in_editor

            st.write("--- Debug Inside Detection Logic ---")
            st.write(f"Debug: current_module_ids_in_editor: {current_module_ids_in_editor}")
            st.write(f"Debug: ids_to_delete_detected: {ids_to_delete_detected}")
            st.write("--- End Debug Inside Detection Logic ---")

            if ids_to_delete_detected:
                st.write("Debug: Detected IDs to delete. Setting session_state and calling st.rerun().") # ADD THIS LINE
                st.session_state.ids_to_delete = ids_to_delete_detected
                st.rerun() # Rerun to display the confirmation dialog below

        # Display Confirmation Dialog for pending deletions
        # This block will only be active if st.session_state.ids_to_delete is populated

        st.write("--- Debug Confirmation Dialog ---") # ADD THIS LINE
        st.write(f"Debug: st.session_state.ids_to_delete (before showing dialog): {st.session_state.ids_to_delete}") # ADD THIS LINE
        st.write("--- End Debug Confirmation Dialog ---") # ADD THIS LINE
        

        if st.session_state.ids_to_delete:
            ids_to_confirm = st.session_state.ids_to_delete
            st.warning(f"Está a punto de eliminar {len(ids_to_confirm)} módulo(s) seleccionados en la tabla. Esta acción no se puede deshacer. ¿Está seguro?")
            
            col_confirm_del, col_cancel_del, _ = st.columns([1,1,3]) # Added a third column for spacing

            with col_confirm_del:
                if st.button("Sí, eliminar módulo(s)", type="primary", key="confirm_final_delete_button"):
                    st.write("Debug: 'Sí, eliminar módulo(s)' button clicked.") # DEBUG LINE
                    
                    # It's safer to operate on a copy if iterating and potentially modifying session state,
                    # though here we clear it at the end.
                    ids_to_process_deletion = list(st.session_state.ids_to_delete) 
                    st.write(f"Debug: Attempting to delete IDs: {ids_to_process_deletion}") # DEBUG LINE
                    
                    deleted_count = 0
                    if not ids_to_process_deletion:
                        st.write("Debug: No IDs found in st.session_state.ids_to_delete to process.") # DEBUG LINE
                    
                    with st.spinner("Eliminando módulos..."):
                        for module_id_to_remove in ids_to_process_deletion:
                            st.write(f"Debug: Calling delete_module_from_db for ID: {module_id_to_remove}") # DEBUG LINE
                            # Ensure user_email is correctly available in this scope
                            # st.write(f"Debug: user_email for deletion: {user_email}") # Optional: uncomment if user_email might be an issue
                            delete_success = delete_module_from_db(user_email, module_id_to_remove)
                            st.write(f"Debug: delete_module_from_db returned {delete_success} for ID: {module_id_to_remove}") # DEBUG LINE
                            if delete_success:
                                deleted_count += 1
                    
                    st.write(f"Debug: Total deleted_count: {deleted_count}") # DEBUG LINE
                    if deleted_count > 0:
                        st.success(f"Se eliminaron {deleted_count} módulo(s) correctamente.")
                    elif len(ids_to_process_deletion) > 0 and deleted_count == 0: # Check against the list we iterated
                        st.error("No se pudo eliminar ninguno de los módulos seleccionados o ya habían sido eliminados.")
                    
                    st.write("Debug: Clearing st.session_state.ids_to_delete.") # DEBUG LINE
                    st.session_state.ids_to_delete = set()
                    st.write(f"Debug: st.session_state.ids_to_delete after clearing: {st.session_state.ids_to_delete}") # DEBUG LINE
                    
                    st.write("Debug: Calling st.rerun().") # DEBUG LINE
                    st.rerun()
                    # st.write("Debug: This line should NOT be reached if st.rerun() works immediately.") # DEBUG LINE

            with col_cancel_del:
                if st.button("Cancelar eliminación", key="cancel_final_delete_button"):
                    st.session_state.ids_to_delete = set() # Clear pending deletions
                    st.info("Eliminación cancelada. Los módulos no han sido eliminados de la base de datos.")
                    # Rerun to refresh the data_editor; it should revert to showing the rows
                    # as Streamlit's data_editor state might reset or you might need to reload data.
                    st.rerun() 
            
            # Stop further processing of the page, including the "Guardar Cambios" button,
            # until the deletion is confirmed or cancelled.
            st.stop()
            # --- End of new section ---
            
            # Button to save changes to Firebase
            if st.button("Guardar Cambios en Módulos"):
                # --- Start of modification ---
                # Check if a deletion confirmation is pending
                if st.session_state.ids_to_delete:
                    st.warning("Por favor, primero confirme o cancele la eliminación pendiente de módulos (ver mensaje de advertencia arriba).")
                    st.stop() # Prevent saving other edits while deletion is pending
                # --- End of modification ---

                # Proceed with saving edits if no deletions are pending
                # The edited_df should reflect the current state of the table.
                # Rows removed in UI are gone from it; actual DB deletion is handled by the confirmation dialog.
                modules_to_save = edited_df.to_dict('records')
                
                success_count = 0
                error_count = 0
                
                # (The rest of your existing saving logic for edits and new modules follows here)
                # Ensure this part correctly handles new rows (which won't have a module_id from original_module_ids)
                # and edited rows.
                with st.spinner('Guardando cambios...'):
                    for module in modules_to_save:
                        try:
                            # Prepare module data for Firebase
                            def convert_date_to_iso(date_val):
                                if pd.isna(date_val):
                                    return ''
                                if isinstance(date_val, (datetime.date, datetime.datetime)):
                                    return date_val.isoformat()
                                return str(date_val) if date_val is not None else ''
                            
                            def clean_value(val):
                                if pd.isna(val):
                                    return None
                                if isinstance(val, (int, float)) and math.isnan(val):
                                    return None
                                return val
                                
                            module_data = {
                                'name': str(module.get('name', '')),
                                'description': str(module.get('description', '')),
                                'credits': int(module.get('credits', 0)) if not pd.isna(module.get('credits')) else 0,
                                'duration_weeks': int(module.get('duration_weeks', 1)) if not pd.isna(module.get('duration_weeks')) else 1,
                                'ciclo1_inicio': convert_date_to_iso(module.get('ciclo1_inicio')),
                                'ciclo1_fin': convert_date_to_iso(module.get('ciclo1_fin')),
                                'ciclo2_inicio': convert_date_to_iso(module.get('ciclo2_inicio')),
                                'ciclo2_fin': convert_date_to_iso(module.get('ciclo2_fin')),
                                'updated_at': datetime.datetime.now().isoformat()
                            }
                            
                            # Remove None values as they can cause issues with Firebase
                            module_data = {k: v for k, v in module_data.items() if v is not None}
                            
                            # Debug: Print the data being saved
                            st.write(f"Saving module data: {module_data}")
                            
                            # Get the sanitized user email path
                            user_path = user_email.replace('.', ',')
                            
                            # Check if this is a new or existing module
                            if 'module_id' in module and module['module_id'] and module['module_id'] in original_module_ids:
                                try:
                                    # Update existing module - use set() with the same module_id to update
                                    db.child("modules").child(user_path).child(module['module_id']).set(module_data)
                                    st.write(f"Successfully updated module: {module['module_id']}")
                                except Exception as e:
                                    st.error(f"Error updating module {module.get('name', '')} ({module.get('module_id', '')}): {str(e)}")
                                    raise
                            else:
                                try:
                                    # Add new module - but first check if module with same name exists
                                    existing_modules = db.child("modules").child(user_path).order_by_child('name').equal_to(module_data['name']).get()
                                    if existing_modules.val():
                                        # Module with same name exists, update it instead of creating new one
                                        module_id = next(iter(existing_modules.val()))
                                        db.child("modules").child(user_path).child(module_id).set(module_data)
                                        st.write(f"Updated existing module with same name: {module_data['name']}")
                                    else:
                                        # Create new module
                                        module_id = str(uuid.uuid4())
                                        module_data['created_at'] = datetime.datetime.now().isoformat()
                                        module_data['module_id'] = module_id
                                        db.child("modules").child(user_path).child(module_id).set(module_data)
                                        st.write(f"Successfully created new module: {module_data['name']}")
                                except Exception as e:
                                    st.error(f"Error creating/updating module {module.get('name', '')}: {str(e)}")
                                    raise
                            
                            success_count += 1
                        except Exception as e:
                            st.error(f"Error al guardar el módulo {module.get('name', '')}: {str(e)}")
                            error_count += 1
                
                # Show success/error message
                if error_count == 0:
                    st.success(f"¡Se guardaron exitosamente {success_count} módulos!")
                    st.rerun()  # Refresh the data
                else:
                    st.warning(f"Se guardaron {success_count} módulos con éxito, pero hubo {error_count} errores.")
                

else:
    st.error("Error de sesión: No se pudo obtener el email del usuario para cargar los módulos.")

# --- MODULE ENROLLMENT SECTION (Placeholder) ---
# st.divider()
# st.header("Inscripción a Módulos")
# Add enrollment logic here if needed
