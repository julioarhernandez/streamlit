import streamlit as st
import pandas as pd
import datetime
import time
import math
import uuid # For generating unique module IDs
from config import setup_page, db # Assuming db is initialized in config.py

# --- Page Setup and Login Check ---
setup_page("Gestión de Módulos")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

# --- Database Functions (No changes needed here) ---
def save_new_module_to_db(user_email, module_data):
    try:
        user_email_sanitized = user_email.replace('.', ',')
        db.child("modules").child(user_email_sanitized).push(module_data)
        return True
    except Exception as e:
        st.error(f"Error saving module to Firebase: {e}")
        print(f"Error saving module to Firebase: {e}")
        return False

def delete_module_from_db(user_email, module_key):
    if not user_email or not module_key:
        st.error("Error: Datos de usuario o clave de módulo no válidos.")
        return False
    try:
        user_path = user_email.replace('.', ',')
        module_ref = db.child("modules").child(user_path).child(module_key)
        module_data = module_ref.get()
        if not module_data.val():
            st.error(f"Error: No se encontró el módulo con la clave: {module_key}")
            return False
        module_info = module_data.val()
        module_name = module_info.get('name', 'Nombre no disponible')
        db.child("modules").child(user_path).child(module_key).remove()
        verification = db.child("modules").child(user_path).child(module_key).get()
        if not verification.val():
            st.toast(f"✅ Módulo eliminado: {module_name}")
            return True
        else:
            st.error(f"Error: No se pudo eliminar el módulo {module_name}")
            return False
    except Exception as e:
        st.error(f"Error al eliminar el módulo: {str(e)}")
        print(f"Error al eliminar el módulo: {str(e)}")
        return False    

def load_modules(user_email_from_session):
    if not user_email_from_session:
        return pd.DataFrame()
    try:
        user_email_sanitized = user_email_from_session.replace('.', ',')
        modules_data = db.child("modules").child(user_email_sanitized).get().val()
        if not modules_data:
            df = pd.DataFrame()
        elif isinstance(modules_data, dict):
            processed_list = []
            for key, item in modules_data.items():
                if item and isinstance(item, dict):
                    item['firebase_key'] = key
                    processed_list.append(item)
            df = pd.DataFrame(processed_list) if processed_list else pd.DataFrame()
        else:
            st.warning(f"Unexpected data type for modules: {type(modules_data)}")
            df = pd.DataFrame()
        
        expected_cols = ['module_id', 'name', 'description', 'credits', 'duration_weeks', 'created_at']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        return df
    except Exception as e:
        st.error(f"Error loading modules from Firebase: {e}")
        print(f"Error loading modules from Firebase: {e}")
        return pd.DataFrame(columns=expected_cols)

# --- Utility Functions (No changes needed here) ---
def calculate_end_date(start_date, duration_weeks):
    if start_date and duration_weeks:
        return start_date + datetime.timedelta(weeks=duration_weeks) - datetime.timedelta(days=1)
    return None

# --- Main App Logic ---
user_email = st.session_state.get('email')

# <<< CHANGE: Initialize session state for the cached DataFrame
if 'modules_df' not in st.session_state:
    st.session_state.modules_df = None

# <<< CHANGE: Define a function to invalidate the cache.
def invalidate_cache_and_rerun():
    """Deletes the cached DataFrame and reruns the app."""
    if 'modules_df' in st.session_state:
        del st.session_state.modules_df
    # Also reset any other transient state if needed
    if 'ids_to_delete' in st.session_state:
        st.session_state.ids_to_delete = set()
    if 'show_delete_dialog' in st.session_state:
        st.session_state.show_delete_dialog = False
    st.rerun()

# --- Form State Initialization ---
if 'module_duration_weeks' not in st.session_state:
    st.session_state.module_duration_weeks = 1
if 'ciclo1_inicio' not in st.session_state:
    st.session_state.ciclo1_inicio = datetime.date.today()
if 'ciclo2_inicio' not in st.session_state:
    st.session_state.ciclo2_inicio = datetime.date.today()

# --- FORM TO ADD NEW MODULE ---
st.subheader("Agregar Nuevo Módulo")
with st.container():
    # ... (No changes inside the form layout itself)
    col_nombre, col_desc = st.columns([1, 1])
    with col_nombre: module_name = st.text_input("Nombre del Módulo", key="new_module_name")
    with col_desc: module_description = st.text_input("Descripción", key="new_module_desc")
    col_orden, col_duracion = st.columns(2)
    with col_orden: module_credits = st.number_input("Orden", min_value=1, step=1, key="new_module_credits")
    with col_duracion:
        module_duration_weeks = st.number_input("Duración (Semanas)", min_value=1, step=1, key="new_module_duration", value=st.session_state.module_duration_weeks)
    if module_duration_weeks != st.session_state.module_duration_weeks:
        st.session_state.module_duration_weeks = module_duration_weeks
        st.rerun()
    
    st.subheader("Ciclo 1")
    col1, col2 = st.columns(2)
    with col1:
        ciclo1_inicio = st.date_input("Fecha de Inicio (MM/DD/YYYY)", key="_ciclo1_inicio", value=st.session_state.ciclo1_inicio, format="MM/DD/YYYY")
        if ciclo1_inicio != st.session_state.ciclo1_inicio:
            st.session_state.ciclo1_inicio = ciclo1_inicio
            st.rerun()
    with col2:
        ciclo1_fin = calculate_end_date(st.session_state.ciclo1_inicio, st.session_state.module_duration_weeks)
        st.date_input("Fecha de Fin (MM/DD/YYYY)", value=ciclo1_fin if ciclo1_fin else datetime.date.today(), key="ciclo1_fin_display", format="MM/DD/YYYY", disabled=True)

    st.subheader("Ciclo 2")
    col3, col4 = st.columns(2)
    with col3:
        ciclo2_inicio = st.date_input("Fecha de Inicio (MM/DD/YYYY)", key="_ciclo2_inicio", value=st.session_state.ciclo2_inicio, format="MM/DD/YYYY")
        if ciclo2_inicio != st.session_state.ciclo2_inicio:
            st.session_state.ciclo2_inicio = ciclo2_inicio
            st.rerun()
    with col4:
        ciclo2_fin = calculate_end_date(st.session_state.ciclo2_inicio, st.session_state.module_duration_weeks)
        st.date_input("Fecha de Fin (MM/DD/YYYY)", value=ciclo2_fin if ciclo2_fin else datetime.date.today(), key="ciclo2_fin_display", format="MM/DD/YYYY", disabled=True)
    
    submitted_new_module = st.button("Agregar Módulo")
    if submitted_new_module and user_email:
        if not module_name:
            st.warning("El nombre del módulo es obligatorio.")
        else:
            new_module_data = {
                'module_id': str(uuid.uuid4()),
                'name': module_name,
                'description': module_description,
                'credits': module_credits,
                'duration_weeks': module_duration_weeks,
                'ciclo1_inicio': ciclo1_inicio.isoformat() if ciclo1_inicio else None,
                'ciclo1_fin': calculate_end_date(ciclo1_inicio, module_duration_weeks).isoformat() if ciclo1_inicio else None,
                'ciclo2_inicio': ciclo2_inicio.isoformat() if ciclo2_inicio else None,
                'ciclo2_fin': calculate_end_date(ciclo2_inicio, module_duration_weeks).isoformat() if ciclo2_inicio else None,
                'created_at': datetime.datetime.now().isoformat()
            }
            if save_new_module_to_db(user_email, new_module_data):
                st.success(f"Módulo '{module_name}' guardado exitosamente!")
                # <<< CHANGE: Invalidate cache instead of just rerunning
                invalidate_cache_and_rerun()
            else:
                st.error("No se pudo guardar el módulo.")
                print("No se pudo guardar el módulo.")  
    elif submitted_new_module and not user_email:
        st.error("Error de sesión. No se pudo obtener el email del usuario.")
        print("Error de sesión. No se pudo obtener el email del usuario.")

# --- DISPLAY/EDIT EXISTING MODULES ---
st.divider()
if user_email:
    # <<< CHANGE: Load data only if the cache is empty.
    if st.session_state.modules_df is None:
        with st.spinner("Cargando módulos..."):
            st.session_state.modules_df = load_modules(user_email)
    
    # Always work with the cached DataFrame
    modules_df = st.session_state.modules_df

    if modules_df.empty:
        st.info("No hay módulos existentes para este usuario. Puede agregar nuevos módulos utilizando el formulario anterior.")
    else:
        st.subheader("Módulos Existentes")
        
        # <<< CHANGE: Use the cached 'modules_df' to get original keys
        if 'firebase_key' in modules_df.columns:
            original_module_keys = set(modules_df['firebase_key'].dropna().tolist())
        else:
            st.error("Error: No se encontró la columna 'firebase_key' en los datos. No se pueden gestionar eliminaciones.")
            print("Error: No se encontró la columna 'firebase_key' en los datos. No se pueden gestionar eliminaciones.")
            original_module_keys = set()
        
        # ... (The rest of the data_editor setup logic is largely the same)
        # It will now use the much faster, cached 'modules_df'
        # ...

        # Make a copy of the dataframe to work with
        df_to_edit = modules_df.copy() # Use the cached df
        
        # Convert date columns to datetime for the editor
        date_columns = ['ciclo1_inicio', 'ciclo1_fin', 'ciclo2_inicio', 'ciclo2_fin']
        for col in date_columns:
            if col in df_to_edit.columns:
                df_to_edit[col] = pd.to_datetime(df_to_edit[col], errors='coerce').dt.date

        # Add a delete button column
        df_to_edit['Eliminar'] = False
        
        # Display Columns and Configuration
        display_columns = ['name', 'duration_weeks', 'credits', 'ciclo1_inicio', 'ciclo1_fin', 'ciclo2_inicio', 'ciclo2_fin']
        column_config = {
            "Eliminar": st.column_config.CheckboxColumn("Borrar", help="Seleccione para eliminar", pinned=True),
            "name": st.column_config.TextColumn("Nombre del Módulo", required=True, width="medium"),
            "credits": st.column_config.NumberColumn("Orden", format="%d", min_value=1, width="small"),
            "duration_weeks": st.column_config.NumberColumn("Semanas", format="%d", min_value=1, width="small"),
            "ciclo1_inicio": st.column_config.DateColumn("Ciclo 1 Inicio", format="MM/DD/YYYY", width="small"),
            "ciclo1_fin": st.column_config.DateColumn("Ciclo 1 Fin", format="MM/DD/YYYY", width="small"),
            "ciclo2_inicio": st.column_config.DateColumn("Ciclo 2 Inicio", format="MM/DD/YYYY", width="small"),
            "ciclo2_fin": st.column_config.DateColumn("Ciclo 2 Fin", format="MM/DD/YYYY", width="small"),
            "module_id": None,
            "firebase_key": None,
        }
        
        # The data editor itself
        edited_df = st.data_editor(
            df_to_edit,
            column_config=column_config,
            hide_index=True,
            num_rows="fixed",
            key="modules_editor_main",
            use_container_width=True,
            disabled=["module_id", "firebase_key"],
            column_order=["Eliminar"] + display_columns
        )
        
        # ... Deletion and Saving Logic ...
        if 'ids_to_delete' not in st.session_state:
            st.session_state.ids_to_delete = set()
        if 'show_delete_dialog' not in st.session_state:
            st.session_state.show_delete_dialog = False

        col1, col2, _ = st.columns([2.5, 3.3, 4])
        with col1:
            if st.button("💾 Guardar Cambios"):
                if st.session_state.get('ids_to_delete') and st.session_state.ids_to_delete:
                    st.warning("Por favor, primero confirme o cancele la eliminación pendiente.")
                else:
                    try:
                        modules_to_save = edited_df.to_dict('records')
                        success_count = 0
                        error_count = 0
                        
                        with st.spinner('Guardando cambios...'):
                            user_path = user_email.replace('.', ',')

                            for module in modules_to_save:
                                firebase_key = module.get('firebase_key')
                                if not firebase_key:
                                    continue # Should not happen with existing modules, but safe to check

                                # --- START OF THE FIX ---
                                # Create a clean dictionary to hold only valid data for the update
                                data_for_update = {}
                                
                                # Define fields that can be edited
                                editable_fields = ['name', 'description', 'credits', 'duration_weeks', 'ciclo1_inicio', 'ciclo1_fin', 'ciclo2_inicio', 'ciclo2_fin']

                                for field in editable_fields:
                                    if field in module and pd.notna(module[field]):
                                        value = module[field]
                                        # Convert date/datetime objects to ISO format string
                                        if isinstance(value, (datetime.date, datetime.datetime)):
                                            data_for_update[field] = value.isoformat()
                                        # Ensure numbers are standard Python int/float, not numpy types
                                        elif isinstance(value, (int, float)):
                                            data_for_update[field] = int(value)
                                        # Handle strings and other valid types
                                        elif value is not None:
                                            data_for_update[field] = str(value)
                                
                                # Add a timestamp for the update
                                data_for_update['updated_at'] = datetime.datetime.now().isoformat()
                                # --- END OF THE FIX ---
                                
                                try:
                                    # Update the module in Firebase with the cleaned data
                                    db.child("modules").child(user_path).child(firebase_key).update(data_for_update)
                                    success_count += 1
                                except Exception as e:
                                    st.error(f"Error actualizando módulo {module.get('name', '')}: {e}")
                                    error_count += 1

                        if error_count == 0 and success_count > 0:
                            st.success(f"¡Se guardaron exitosamente los cambios en {success_count} módulos!")
                        elif success_count > 0:
                            st.warning(f"Se guardaron {success_count} módulos con éxito, pero hubo {error_count} errores.")
                        elif error_count > 0:
                            st.error(f"No se pudieron guardar los cambios. Se encontraron {error_count} errores.")
                        else:
                            st.info("No se detectaron cambios para guardar.")
                        
                        # Invalidate cache to force a fresh reload from DB
                        invalidate_cache_and_rerun()
                        
                    except Exception as e:
                        st.error(f"Ocurrió un error inesperado durante el proceso de guardado: {e}")

        with col2:
            if 'Eliminar' in edited_df.columns and edited_df['Eliminar'].any():
                if st.button("❌ Eliminar seleccionados"):
                    rows_to_delete = edited_df[edited_df['Eliminar'] == True]
                    st.session_state.ids_to_delete = set(rows_to_delete['firebase_key'].dropna().tolist())
                    st.session_state.show_delete_dialog = True
                    st.rerun()

            @st.dialog("Confirmar eliminación")
            def confirm_delete_dialog():
                st.write(f"¿Está seguro que desea eliminar {len(st.session_state.ids_to_delete)} módulo(s)? **Esta acción no se puede deshacer.**")
                col1, col2, _ = st.columns([1, 1, 2])
                with col1:
                    if st.button("✅ Sí, eliminar", type="primary"):
                        deleted_count = 0
                        with st.spinner("Eliminando módulos..."):
                            for module_key in list(st.session_state.ids_to_delete):
                                if delete_module_from_db(user_email, module_key):
                                    deleted_count += 1
                        st.success(f"Se eliminaron {deleted_count} módulo(s) correctamente.")
                        time.sleep(1)
                        # <<< CHANGE: Invalidate cache after deletion
                        invalidate_cache_and_rerun()
                with col2:
                    if st.button("Cancelar"):
                        st.session_state.ids_to_delete = set()
                        st.session_state.show_delete_dialog = False
                        st.rerun()

            if st.session_state.show_delete_dialog:
                confirm_delete_dialog()
else:
    st.error("Error de sesión: No se pudo obtener el email del usuario para cargar los módulos.")
    print("Error de sesión: No se pudo obtener el email del usuario para cargar los módulos.")