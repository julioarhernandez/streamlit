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


def delete_module_from_db(user_email, module_key):
    """
    Delete a specific module from Firebase database.
    Path: modules -> user_email_sanitized -> module_key
    """
    if not user_email or not module_key:
        st.error("Error: Datos de usuario o clave de módulo no válidos.")
        return False
        
    try:
        # Sanitize email for Firebase path
        user_path = user_email.replace('.', ',')
        
        # Build the specific path to the module
        module_path = f"modules/{user_path}/{module_key}"
        
        # Get reference to the specific module
        module_ref = db.child("modules").child(user_path).child(module_key)
        
        # First, verify the module exists
        module_data = module_ref.get()
        if not module_data.val():
            st.error(f"Error: No se encontró el módulo con la clave: {module_key}")
            return False
            
        # Get module name for confirmation message
        module_info = module_data.val()
        module_name = module_info.get('name', 'Nombre no disponible') if isinstance(module_info, dict) else 'Nombre no disponible'
        
        # Delete the specific module using the direct path
        # This is the safest way to ensure we only delete the specific module
        db.child("modules").child(user_path).child(module_key).remove()
        
        # Verify deletion was successful by checking if the module still exists
        verification = db.child("modules").child(user_path).child(module_key).get()
        if not verification.val():
            st.toast(f"✅ Módulo eliminado: {module_name}")
            return True
        else:
            st.error(f"Error: No se pudo eliminar el módulo {module_name}")
            return False
            
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
                    # Add the firebase_key to the item
                    item['firebase_key'] = key
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
        
        # Store original module keys to detect deletions
        if 'firebase_key' in modules_df_from_db.columns:
            original_module_keys = set(modules_df_from_db['firebase_key'].dropna().tolist())
        else:
            st.error("Error: No se encontró la columna 'firebase_key' en los datos. No se pueden gestionar eliminaciones.")
            original_module_keys = set()

        if 'ids_to_delete' not in st.session_state:
            st.session_state.ids_to_delete = set()

        # Configure date display format
        date_format = "MM/DD/YYYY"
        
        editable_cols_config = {
            "firebase_key": st.column_config.TextColumn("Firebase Key", disabled=True, help="Clave única de Firebase para este módulo"),
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
            'firebase_key',
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
            
        # Create the data editor with row deletion enabled but no adding new rows
        columns_to_show = ['module_id', 'firebase_key'] + [col for col in display_cols_in_editor if col != 'firebase_key']
        
        # Make a copy of the dataframe to work with
        df_to_edit = modules_df_from_db[columns_to_show].copy()
        
        # Add a delete button column
        df_to_edit['Eliminar'] = False
        
        # Configure columns for the editor
        column_config = {
            **final_column_config,
            "module_id": None,  # Hide module_id from display
            "firebase_key": final_column_config.get("firebase_key", None),  # Show the firebase_key
            "Eliminar": st.column_config.CheckboxColumn("Eliminar", help="Seleccione para eliminar")
        }
        
        # Show the editor with the delete checkbox
        edited_df = st.data_editor(
            df_to_edit,
            column_config=column_config,
            hide_index=True,
            num_rows="fixed",  # Prevents adding new rows
            key="modules_editor_main",
            use_container_width=True,
            disabled=("module_id", "firebase_key"),
            on_change=None
        )
        
        # Check for rows marked for deletion
        if 'Eliminar' in edited_df.columns:
            rows_to_delete = edited_df[edited_df['Eliminar'] == True]
            if not rows_to_delete.empty:
                st.session_state.ids_to_delete = set(rows_to_delete['firebase_key'].dropna().tolist())
        
        # Detect if rows were removed in the data_editor UI and no confirmation is currently active
        if 'firebase_key' in edited_df.columns and not st.session_state.ids_to_delete:
            current_module_keys_in_editor = set(edited_df['firebase_key'].dropna().tolist())
            keys_to_delete_detected = original_module_keys - current_module_keys_in_editor

            if keys_to_delete_detected:
                st.session_state.ids_to_delete = keys_to_delete_detected
                st.rerun() # Rerun to display the confirmation dialog below
        
        # Handle module deletion confirmation
        if st.session_state.ids_to_delete:
            # Create a form to handle the confirmation/cancellation
            with st.form("delete_confirmation_form"):
                st.warning(f"Está a punto de eliminar {len(st.session_state.ids_to_delete)} módulo(s) seleccionados en la tabla. Esta acción no se puede deshecer. ¿Está seguro?")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.form_submit_button("Sí, eliminar módulo(s)"):
                        ids_to_process_deletion = list(st.session_state.ids_to_delete)
                        deleted_count = 0
                        
                        with st.spinner("Eliminando módulos..."):
                            for module_key in ids_to_process_deletion:
                                if delete_module_from_db(user_email, module_key):
                                    deleted_count += 1
                        
                        if deleted_count > 0:
                            st.success(f"Se eliminaron {deleted_count} módulo(s) correctamente.")
                        
                        st.session_state.ids_to_delete = set()
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("Cancelar eliminación"):
                        st.session_state.ids_to_delete = set()
                        st.rerun()
            
            # Stop further execution until deletion is confirmed or cancelled
            st.stop()
        
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
            
            # Get original module IDs for comparison
            original_module_ids = set(modules_df_from_db['module_id'].dropna().tolist()) if 'module_id' in modules_df_from_db.columns else set()
            
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
                        
                        # Get the sanitized user email path
                        user_path = user_email.replace('.', ',')
                        
                        # Check if this is a new or existing module using firebase_key
                        firebase_key = module.get('firebase_key')
                        if firebase_key and firebase_key in original_module_keys:
                            try:
                                # Update existing module using firebase_key
                                db.child("modules").child(user_path).child(firebase_key).update(module_data)
                                success_count += 1
                            except Exception as e:
                                st.error(f"Error updating module {module.get('name', '')} (firebase_key: {firebase_key}): {str(e)}")
                                error_count += 1
                        else:
                            try:
                                # Add new module
                                module_id = str(uuid.uuid4())
                                module_data['created_at'] = datetime.datetime.now().isoformat()
                                module_data['module_id'] = module_id
                                db.child("modules").child(user_path).child(module_id).set(module_data)
                                success_count += 1
                            except Exception as e:
                                st.error(f"Error creating module {module.get('name', '')}: {str(e)}")
                                error_count += 1
                        
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