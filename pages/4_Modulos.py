import streamlit as st
import pandas as pd
import datetime
import time
import math
import uuid
from config import setup_page, db

# --- Page Setup and Login Check ---
setup_page("Gestión de Módulos")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

# --- MOCK DATA (to be replaced by a DB table later) ---
breaks_list = [
    {'name': 'Spring Break', 'start_date': '2025-06-01', 'end_date': '2025-06-08'},
    {'name': 'Summer Break', 'start_date': '2025-07-01', 'end_date': '2025-07-08'},
]

# --- DATE CALCULATION LOGIC (Integrated from your script) ---

def parse_breaks(breaks_data):
    """Converts a list of break dictionaries into date tuples."""
    parsed = []
    for b in breaks_data:
        try:
            start = datetime.datetime.strptime(b['start_date'], '%Y-%m-%d').date()
            end = datetime.datetime.strptime(b['end_date'], '%Y-%m-%d').date()
            parsed.append((start, end))
        except (ValueError, TypeError):
            # Skip invalid or incomplete break entries
            continue
    return parsed

def adjust_date_for_breaks(current_date, breaks):
    """Checks if a date falls within a break and returns the day after the break ends."""
    for b_start, b_end in breaks:
        if b_start <= current_date <= b_end:
            # The date is inside a break, so move it to the day after the break
            return b_end + datetime.timedelta(days=1)
    # The date is not in a break
    return current_date

def calculate_schedule(modules_list, initial_start_date, breaks):
    """
    Calculates and returns a new list of modules with updated dates for two cycles.
    This version correctly handles the start of Cycle 2.
    """
    if not modules_list:
        return []

    # Sort modules by 'credits' (order)
    modules_sorted = sorted(
        modules_list, 
        key=lambda x: int(x.get('credits') or 999)
    )
    
    # Use a dictionary for easier updates, keyed by firebase_key
    modules_dict = {mod['firebase_key']: mod.copy() for mod in modules_sorted}

    # --- Pass 1: Calculate all of Cycle 1 ---
    current_start_c1 = initial_start_date
    for mod_data in modules_sorted:
        key = mod_data['firebase_key']
        
        current_start_c1 = adjust_date_for_breaks(current_start_c1, breaks)
        
        duration_weeks = int(mod_data.get('duration_weeks') or 1)
        duration = datetime.timedelta(weeks=duration_weeks)
        
        end_date = current_start_c1
        days_added = 0
        while days_added < duration.days:
            end_date += datetime.timedelta(days=1)
            end_date = adjust_date_for_breaks(end_date, breaks)
            days_added += 1
        
        final_end_date = end_date - datetime.timedelta(days=1)
        
        modules_dict[key]['ciclo1_inicio'] = current_start_c1.isoformat()
        modules_dict[key]['ciclo1_fin'] = final_end_date.isoformat()
        
        # Set start for the *next* module in Cycle 1
        current_start_c1 = final_end_date + datetime.timedelta(days=1)

    # --- Pass 2: Calculate all of Cycle 2 ---
    # Cycle 2 starts the day after the last module of Cycle 1 finishes
    current_start_c2 = current_start_c1 

    for mod_data in modules_sorted:
        key = mod_data['firebase_key']
        
        current_start_c2 = adjust_date_for_breaks(current_start_c2, breaks)
        
        duration_weeks = int(mod_data.get('duration_weeks') or 1)
        duration = datetime.timedelta(weeks=duration_weeks)

        end_date = current_start_c2
        days_added = 0
        while days_added < duration.days:
            end_date += datetime.timedelta(days=1)
            end_date = adjust_date_for_breaks(end_date, breaks)
            days_added += 1
        
        final_end_date = end_date - datetime.timedelta(days=1)
        
        modules_dict[key]['ciclo2_inicio'] = current_start_c2.isoformat()
        modules_dict[key]['ciclo2_fin'] = final_end_date.isoformat()

        # Set start for the *next* module in Cycle 2
        current_start_c2 = final_end_date + datetime.timedelta(days=1)

    # Return the updated modules as a list of dictionaries
    return list(modules_dict.values())
# --- DATABASE & CACHE FUNCTIONS ---

def save_new_module_to_db(user_email, module_data):
    try:
        user_email_sanitized = user_email.replace('.', ',')
        db.child("modules").child(user_email_sanitized).push(module_data)
        return True
    except Exception as e:
        st.error(f"Error saving module to Firebase: {e}")
        return False

def delete_module_from_db(user_email, module_key):
    # (Your existing delete function is fine, no changes needed)
    if not user_email or not module_key: return False
    try:
        user_path = user_email.replace('.', ',')
        db.child("modules").child(user_path).child(module_key).remove()
        st.toast("✅ Módulo eliminado de la base de datos.")
        return True
    except Exception as e:
        st.error(f"Error al eliminar el módulo: {str(e)}")
        return False

def load_modules(user_email_from_session):
    # (Your existing load function is fine, no changes needed)
    if not user_email_from_session: return pd.DataFrame()
    try:
        user_email_sanitized = user_email_from_session.replace('.', ',')
        modules_data = db.child("modules").child(user_email_sanitized).get().val()
        if not modules_data or not isinstance(modules_data, dict):
             return pd.DataFrame()
        
        processed_list = [
            {**item, 'firebase_key': key}
            for key, item in modules_data.items()
            if item and isinstance(item, dict)
        ]
        df = pd.DataFrame(processed_list) if processed_list else pd.DataFrame()
        
        expected_cols = ['module_id', 'name', 'description', 'credits', 'duration_weeks', 'created_at', 'ciclo1_inicio', 'ciclo1_fin', 'ciclo2_inicio', 'ciclo2_fin']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # Sort dataframe by 'credits' for initial display
        if 'credits' in df.columns:
            df = df.sort_values(by='credits').reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Error loading modules from Firebase: {e}")
        return pd.DataFrame()

def invalidate_cache_and_rerun():
    """Deletes the cached DataFrame and reruns the app."""
    if 'modules_df' in st.session_state:
        del st.session_state.modules_df
    st.rerun()

# --- MAIN APP LOGIC ---
user_email = st.session_state.get('email')

if 'modules_df' not in st.session_state:
    st.session_state.modules_df = None

# --- FORM TO ADD NEW MODULE ---
st.subheader("Agregar Nuevo Módulo")
with st.form("new_module_form", clear_on_submit=True):
    col_nombre, col_desc = st.columns(2)
    module_name = col_nombre.text_input("Nombre del Módulo")
    module_description = col_desc.text_input("Descripción")
    
    col_orden, col_duracion = st.columns(2)
    module_credits = col_orden.number_input("Orden (Créditos)", min_value=1, step=1)
    module_duration_weeks = col_duracion.number_input("Duración (Semanas)", min_value=1, step=1)
    
    submitted_new_module = st.form_submit_button("Agregar Módulo")
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
                'created_at': datetime.datetime.now().isoformat()
                # Dates are intentionally omitted; they will be calculated later.
            }
            if save_new_module_to_db(user_email, new_module_data):
                st.success(f"Módulo '{module_name}' agregado. Ahora puede recalcular las fechas.")
                invalidate_cache_and_rerun()
            else:
                st.error("No se pudo guardar el módulo.")

# --- DISPLAY/EDIT EXISTING MODULES ---
st.divider()
if user_email:
    if st.session_state.modules_df is None:
        with st.spinner("Cargando módulos..."):
            st.session_state.modules_df = load_modules(user_email)
    
    modules_df = st.session_state.modules_df

    if modules_df.empty:
        st.info("No hay módulos existentes. Puede agregar uno usando el formulario de arriba.")
    else:
        st.subheader("Módulos Existentes y Planificación")

        # --- DATA EDITOR (Now defined before the button that uses its output) ---
        df_to_edit = modules_df.copy()
        
        date_columns = ['ciclo1_inicio', 'ciclo1_fin', 'ciclo2_inicio', 'ciclo2_fin']
        for col in date_columns:
            if col in df_to_edit.columns:
                df_to_edit[col] = pd.to_datetime(df_to_edit[col], errors='coerce').dt.date

        df_to_edit['Eliminar'] = False
        
        column_config = {
            "Eliminar": st.column_config.CheckboxColumn("Borrar", help="Seleccione para eliminar", default=False),
            "name": st.column_config.TextColumn("Nombre del Módulo", required=True),
            "credits": st.column_config.NumberColumn("Orden", format="%d", min_value=1, required=True),
            "duration_weeks": st.column_config.NumberColumn("Semanas", format="%d", min_value=1, required=True),
            "ciclo1_inicio": st.column_config.DateColumn("Ciclo 1 Inicio", format="MM/DD/YYYY", disabled=True),
            "ciclo1_fin": st.column_config.DateColumn("Ciclo 1 Fin", format="MM/DD/YYYY", disabled=True),
            "ciclo2_inicio": st.column_config.DateColumn("Ciclo 2 Inicio", format="MM/DD/YYYY", disabled=True),
            "ciclo2_fin": st.column_config.DateColumn("Ciclo 2 Fin", format="MM/DD/YYYY", disabled=True),
            "module_id": None, "firebase_key": None, "description": None, "created_at": None,
        }
        
        # This is the single source of truth for the edited data in this script run
        edited_df = st.data_editor(
            df_to_edit,
            column_config=column_config,
            hide_index=True,
            num_rows="dynamic",
            key="modules_editor_main",
            use_container_width=True,
        )

        # --- RECALCULATION UI (Now uses the 'edited_df' variable directly) ---
        col1, col2 = st.columns([1, 2])
        with col1:
            program_start_date = st.date_input(
                "Fecha de Inicio del Programa",
                value=datetime.date.today(),
                key="program_start_date"
            )

        with col2:
            st.write("") # Spacer
            st.write("") # Spacer
            if st.button("🚀 Recalcular y Guardar Fechas", type="primary", use_container_width=True):
                with st.spinner("Calculando nuevo cronograma y guardando..."):
                    # --- START OF THE DEFINITIVE FIX ---
                    # Use the DataFrame returned by st.data_editor directly.
                    # This avoids any issues with stale/corrupted session state.
                    modules_from_editor = edited_df.to_dict('records')
                    # --- END OF THE DEFINITIVE FIX ---

                    current_modules = [
                        mod for mod in modules_from_editor
                        if isinstance(mod, dict) and mod.get('firebase_key')
                    ]

                    if not current_modules:
                        st.warning("No hay módulos existentes para calcular. Agregue un módulo primero.")
                    else:
                        breaks = parse_breaks(breaks_list)
                        updated_modules_with_dates = calculate_schedule(current_modules, program_start_date, breaks)
                        
                        if updated_modules_with_dates:
                            update_payload = {}
                            for mod in updated_modules_with_dates:
                                firebase_key = mod.get('firebase_key')
                                if firebase_key:
                                    mod_to_save = mod.copy()
                                    mod_to_save.pop('Eliminar', None)
                                    update_payload[firebase_key] = mod_to_save

                            if update_payload:
                                try:
                                    user_path = user_email.replace('.', ',')
                                    db.child("modules").child(user_path).update(update_payload)
                                    st.success("¡Cronograma recalculado y guardado exitosamente!")
                                    time.sleep(1)
                                    invalidate_cache_and_rerun()
                                except Exception as e:
                                    st.error(f"Error al guardar el cronograma actualizado: {e}")
                            else:
                                st.warning("No se encontraron módulos existentes para actualizar.")
                        else:
                            st.warning("No se pudieron calcular las fechas del cronograma.")
        
        st.info("Cambie el 'Orden' o 'Semanas' y presione 'Recalcular' para actualizar el cronograma.", icon="ℹ️")

        # --- Deletion Logic (Also uses the 'edited_df' variable) ---
        rows_to_delete = edited_df[edited_df['Eliminar'] == True]
        if not rows_to_delete.empty:
            st.warning("Ha marcado módulos para eliminar. La eliminación es permanente.")
            if st.button("Confirmar Eliminación", type="primary"):
                keys_to_delete = rows_to_delete['firebase_key'].tolist()
                deleted_count = 0
                with st.spinner("Eliminando módulos..."):
                    for key in keys_to_delete:
                        if delete_module_from_db(user_email, key):
                            deleted_count += 1
                
                st.success(f"{deleted_count} módulo(s) eliminados. Puede recalcular las fechas para el resto.")
                invalidate_cache_and_rerun()
else:
    st.error("Error de sesión: No se pudo obtener el email del usuario para cargar los módulos.")