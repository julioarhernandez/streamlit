import streamlit as st
import pandas as pd
import datetime
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
    # Initialize session state for tracking shown toasts if it doesn't exist
    if 'shown_toasts' not in st.session_state:
        st.session_state.shown_toasts = set()
    
    # Check if we've already shown a toast for this module_id
    if module_id in st.session_state.shown_toasts:
        return True  # Skip showing the toast again
        
    try:
        user_email_sanitized = user_email.replace('.', ',')
        db.child("modules").child(user_email_sanitized).child(module_id).remove()
        
        # Mark this module_id as having shown a toast
        st.session_state.shown_toasts.add(module_id)
        
        # Show toast only once
        st.toast(f"Módulo ID: {module_id} eliminado.")
        return True
    except Exception as e:
        st.error(f"Error deleting module {module_id}: {e}")
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
            
        # Create the data editor with visible columns only
        edited_df = st.data_editor(
            modules_df_from_db[['module_id'] + display_cols_in_editor],  # Include module_id in data but not in display
            column_config={
                **final_column_config,
                "module_id": None  # This hides the column from display
            },
            hide_index=True,
            num_rows="dynamic",
            key="modules_editor_main",
            use_container_width=True
        )
        
        # Detect and process deletions
        if 'module_id' in edited_df.columns:
            current_module_ids = set(edited_df['module_id'].dropna().tolist())
            ids_to_delete = original_module_ids - current_module_ids
            
            # Process deletions without forcing a rerun
            for module_id_to_delete in ids_to_delete:
                delete_module_from_db(user_email, module_id_to_delete)
            # The data editor will update automatically due to Streamlit's reactivity
            
            # Button to save other changes (edits, new rows if editor adds them)
            if st.button("Guardar Cambios en Módulos Editados/Agregados"):
                st.warning("La funcionalidad de guardar ediciones o nuevas filas desde este editor aún no está implementada.")
                # Placeholder for update/add logic:
                # Compare edited_df with modules_df_from_db row by row (e.g., by module_id)
                # For new rows (if editor adds them with blank module_id), they'd need to be saved with save_new_module_to_db

else:
    st.error("Error de sesión: No se pudo obtener el email del usuario para cargar los módulos.")

# --- MODULE ENROLLMENT SECTION (Placeholder) ---
# st.divider()
# st.header("Inscripción a Módulos")
# Add enrollment logic here if needed
