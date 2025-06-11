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
    {'name': 'Summer Break', 'start_date': '2025-06-30', 'end_date': '2025-07-06'},
]

# --- DATE CALCULATION LOGIC ---

def parse_breaks(breaks_data):
    """
    Convierte una lista de diccionarios de vacaciones en tuplas de fechas (inicio, fin).
    Omite entradas inválidas.
    """
    parsed = []
    for b in breaks_data:
        try:
            start = datetime.datetime.strptime(b['start_date'], '%Y-%m-%d').date()
            end = datetime.datetime.strptime(b['end_date'], '%Y-%m-%d').date()
            parsed.append((start, end))
        except (ValueError, TypeError):
            # Saltar entradas de vacaciones inválidas o incompletas
            continue
    return parsed

def adjust_date_for_breaks(current_date, breaks):
    """
    Verifica si una fecha cae dentro de un período de vacaciones.
    Si es así, retorna el día después de que las vacaciones terminan.
    Si no, retorna la fecha original.
    """
    for b_start, b_end in breaks:
        if b_start <= current_date <= b_end:
            # La fecha está dentro de unas vacaciones, moverla al día después de las vacaciones
            return b_end + datetime.timedelta(days=1)
    # La fecha no está en vacaciones
    return current_date

def calculate_schedule(modules_list, initial_start_date, breaks):
    """
    Calcula y retorna una nueva lista de módulos con fechas actualizadas para dos ciclos.
    Esta versión cuenta los días de duración como días hábiles efectivos,
    pausando el módulo durante los períodos de vacaciones.
    """
    if not modules_list:
        return []

    # Ordenar módulos por 'credits' (orden)
    modules_sorted = sorted(
        modules_list, 
        key=lambda x: int(x.get('credits') or 999)
    )
    
    # Usar un diccionario para facilitar las actualizaciones, con firebase_key como clave
    modules_dict = {mod['firebase_key']: mod.copy() for mod in modules_sorted}

    # --- Pase 1: Calcular todas las fechas del Ciclo 1 ---
    current_start_c1 = initial_start_date
    
    for mod_data in modules_sorted:
        key = mod_data['firebase_key']
        
        # Ajustar la fecha de inicio del módulo actual para cualquier vacación precedente
        current_start_c1 = adjust_date_for_breaks(current_start_c1, breaks)
        
        duration_weeks = int(mod_data.get('duration_weeks') or 1)
        duration_days_to_count = duration_weeks * 7 # Número de días de trabajo efectivos necesarios

        # Lógica para contar los días de trabajo efectivos
        current_date_for_duration = current_start_c1
        days_counted_for_module = 0

        while days_counted_for_module < duration_days_to_count:
            # Primero, ajustamos la fecha actual para saltar cualquier vacación si cae en una
            current_date_for_duration = adjust_date_for_breaks(current_date_for_duration, breaks)
            
            # Este día ajustado es un día hábil, así que lo contamos
            days_counted_for_module += 1
            
            # Moverse al siguiente día calendario para verificar en la próxima iteración
            # Este día se ajustará nuevamente por adjust_date_for_breaks si cae en vacaciones
            current_date_for_duration += datetime.timedelta(days=1)
        
        # current_date_for_duration ahora es el día *después* del último día hábil del módulo.
        # Por lo tanto, la fecha de finalización real es un día antes de esta.
        final_end_date = current_date_for_duration - datetime.timedelta(days=1)
        
        modules_dict[key]['fecha_inicio_1'] = current_start_c1.isoformat()
        modules_dict[key]['fecha_fin_1'] = final_end_date.isoformat()
        
        # La fecha de inicio para el *siguiente* módulo en el Ciclo 1 es el día después del fin del módulo actual
        current_start_c1 = final_end_date + datetime.timedelta(days=1)

    # --- Pase 2: Calcular todas las fechas del Ciclo 2 ---
    # El Ciclo 2 comienza el día después de que termina el último módulo del Ciclo 1
    current_start_c2 = current_start_c1 

    for mod_data in modules_sorted:
        key = mod_data['firebase_key']
        
        # Ajustar la fecha de inicio del módulo actual para cualquier vacación precedente
        current_start_c2 = adjust_date_for_breaks(current_start_c2, breaks)
        
        duration_weeks = int(mod_data.get('duration_weeks') or 1)
        duration_days_to_count = duration_weeks * 7 # Número de días de trabajo efectivos necesarios

        # Lógica para contar los días de trabajo efectivos (igual que en el Ciclo 1)
        current_date_for_duration = current_start_c2
        days_counted_for_module = 0

        while days_counted_for_module < duration_days_to_count:
            current_date_for_duration = adjust_date_for_breaks(current_date_for_duration, breaks)
            days_counted_for_module += 1
            current_date_for_duration += datetime.timedelta(days=1)
        
        final_end_date = current_date_for_duration - datetime.timedelta(days=1)
        
        modules_dict[key]['fecha_inicio_2'] = current_start_c2.isoformat()
        modules_dict[key]['fecha_fin_2'] = final_end_date.isoformat()

        # La fecha de inicio para el *siguiente* módulo en el Ciclo 2 es el día después del fin del módulo actual
        current_start_c2 = final_end_date + datetime.timedelta(days=1)

    # Retornar los módulos actualizados como una lista de diccionarios
    return list(modules_dict.values())

# --- DATABASE & CACHE FUNCTIONS ---

def save_new_module_to_db(user_email, module_data):
    """Guarda un nuevo módulo en la base de datos de Firebase."""
    try:
        user_email_sanitized = user_email.replace('.', ',')
        db.child("modules").child(user_email_sanitized).push(module_data)
        return True
    except Exception as e:
        st.error(f"Error al guardar el módulo en Firebase: {e}")
        return False

def delete_module_from_db(user_email, module_key):
    """Elimina un módulo de la base de datos de Firebase."""
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
    """Carga los módulos de la base de datos de Firebase para el usuario actual."""
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
        
        # Updated expected_cols to match the new date column names
        expected_cols = ['module_id', 'name', 'description', 'credits', 'duration_weeks', 'created_at', 
                          'fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # Ordenar el dataframe por 'credits' para la visualización inicial
        if 'credits' in df.columns:
            df = df.sort_values(by='credits').reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Error al cargar módulos de Firebase: {e}")
        return pd.DataFrame()

def invalidate_cache_and_rerun():
    """Invalida el DataFrame en caché y vuelve a ejecutar la aplicación."""
    if 'modules_df' in st.session_state:
        del st.session_state.modules_df
    st.rerun()

# --- MAIN APP LOGIC ---
user_email = st.session_state.get('email')

if 'modules_df' not in st.session_state:
    st.session_state.modules_df = None

# --- FORMULARIO PARA AGREGAR NUEVO MÓDULO ---
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
                # Las fechas se omiten intencionadamente; se calcularán más tarde.
            }
            if save_new_module_to_db(user_email, new_module_data):
                st.success(f"Módulo '{module_name}' agregado. Ahora puede recalcular las fechas.")
                invalidate_cache_and_rerun()
            else:
                st.error("No se pudo guardar el módulo.")

# --- MOSTRAR/EDITAR MÓDULOS EXISTENTES ---
st.divider()
if user_email:
    # Cargar desde la base de datos si el caché está vacío
    if 'modules_df' not in st.session_state or st.session_state.modules_df is None:
        with st.spinner("Cargando módulos..."):
            st.session_state.modules_df = load_modules(user_email)
    
    modules_df = st.session_state.modules_df

    if modules_df.empty:
        st.info("No hay módulos existentes. Puede agregar uno usando el formulario de arriba.")
    else:
        st.subheader("Módulos Existentes y Planificación")

        # --- FUNCIÓN PARA GUARDAR MÓDULOS ACTUALIZADOS ---
        def save_updated_modules(updated_df):
            try:
                update_payload = {}
                for _, row in updated_df.iterrows():
                    if pd.notna(row.get('firebase_key')):
                        mod_updates = row.drop('Eliminar', errors='ignore').to_dict()
                        
                        clean_updates = {}
                        for k, v in mod_updates.items():
                            if v is None or pd.isna(v) or k == 'firebase_key':
                                continue
                                
                            if hasattr(v, 'item'): # Convert numpy types to Python native types
                                v = v.item()
                                
                            if isinstance(v, (datetime.date, datetime.datetime)): # Convert date objects to ISO format strings
                                v = v.isoformat()
                                
                            clean_updates[k] = v
                                
                        if clean_updates:  # Solo agregar si hay actualizaciones
                            update_payload[row['firebase_key']] = clean_updates
                
                if update_payload:
                    user_path = user_email.replace('.', ',')
                    db.child("modules").child(user_path).update(update_payload)
                    return True, "¡Cambios guardados exitosamente!"
                return False, "No hay cambios para guardar."
            except Exception as e:
                import traceback
                return False, f"Error al guardar cambios: {str(e)}\n{traceback.format_exc()}"

        # --- EDITOR DE DATOS (Definido antes de cualquier lógica que use su salida) ---
        df_to_edit = modules_df.copy()
        
        # Define the date columns directly with the desired names
        date_columns = ['fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']
        
        # Convertir las columnas de fecha a tipo datetime.date para el data_editor
        for col in date_columns:
            if col in df_to_edit.columns:
                try:
                    df_to_edit[col] = pd.to_datetime(df_to_edit[col], errors='coerce').dt.date
                except Exception as e:
                    st.error(f"Error al convertir la columna {col} a fecha para visualización: {str(e)}")
        df_to_edit['Eliminar'] = False
        
        # Configuración de columnas en el orden solicitado
        column_config = {
            "Eliminar": st.column_config.CheckboxColumn("Borrar", help="Seleccione para eliminar", default=False, width="small"),
            "name": st.column_config.TextColumn("Nombre del Módulo", required=True),
            "duration_weeks": st.column_config.NumberColumn("Semanas", format="%d", min_value=1, required=True, width="small"),
            "credits": st.column_config.NumberColumn("Orden", format="%d", min_value=1, required=True, width="small"),
            "fecha_inicio_1": st.column_config.DateColumn("Fecha Inicio 1", format="MM/DD/YYYY", disabled=True),
            "fecha_fin_1": st.column_config.DateColumn("Fecha Fin 1", format="MM/DD/YYYY", disabled=True),
            "fecha_inicio_2": st.column_config.DateColumn("Fecha Inicio 2", format="MM/DD/YYYY", disabled=True),
            "fecha_fin_2": st.column_config.DateColumn("Fecha Fin 2", format="MM/DD/YYYY", disabled=True),
            "module_id": None, "firebase_key": None, "description": None, "created_at": None, "updated_at": None,
        }
        
        # Ordenar las columnas según el orden deseado
        column_order = [
            "Eliminar", 
            "name", 
            "duration_weeks", 
            "credits", 
            "fecha_inicio_1", 
            "fecha_fin_1", 
            "fecha_inicio_2", 
            "fecha_fin_2"
        ]
        
        # Asegurarse de que solo se incluyan las columnas que existen en el DataFrame
        column_order = [col for col in column_order if col in df_to_edit.columns]
        
        # Reordenar el DataFrame
        df_to_edit = df_to_edit[column_order + [col for col in df_to_edit.columns if col not in column_order]]
        
        # Esta es la única fuente de verdad. Siempre es un DataFrame.
        # Usando num_rows="fixed" para evitar añadir nuevas filas
        edited_df = st.data_editor(
            df_to_edit,
            column_config=column_config,
            hide_index=True,
            num_rows="fixed",
            key="modules_editor_main",
            use_container_width=True,
        )
        
        # Verificar cambios y eliminaciones
        has_changes = not edited_df.equals(df_to_edit)
        rows_to_delete = edited_df[edited_df['Eliminar'] == True]
        has_deletions = not rows_to_delete.empty

        # Crear columnas para botones
        col1, col2 = st.columns([1, 3])
        
        # Botón "Guardar Cambios"
        if has_changes:
            with col1:
                if st.button("💾 Guardar Cambios", type="primary"):
                    success, message = save_updated_modules(edited_df)
                    if success:
                        st.success(message)
                        invalidate_cache_and_rerun()
                    else:
                        st.error(message)
            
        # Botón "Confirmar Eliminación"
        if has_deletions:
            with col2:
                if st.button("🗑️ Confirmar Eliminación"):
                    keys_to_delete = rows_to_delete['firebase_key'].tolist()
                    deleted_count = 0
                    with st.spinner("Eliminando módulos..."):
                        for key in keys_to_delete:
                            if delete_module_from_db(user_email, key):
                                deleted_count += 1
                    
                    st.success(f"{deleted_count} módulo(s) eliminados. Puede recalcular las fechas para el resto.")
                    invalidate_cache_and_rerun()
        
        # Mensajes de estado
        if has_changes:
            st.warning("Tiene cambios sin guardar. Haga clic en 'Guardar Cambios' para guardar sus modificaciones.")
        elif has_deletions:
            st.warning("Ha marcado módulos para eliminar. La eliminación es permanente.")
        else:
            st.info("Realice cambios en la tabla y haga clic en 'Guardar Cambios' para guardar.")

        # --- UI DE RECALCULACIÓN ---
        col1, col2 = st.columns([1, 2])
        with col1:
            # Inicializar last_saved_date en session state si no existe
            if 'last_saved_date' not in st.session_state:
                st.session_state.last_saved_date = datetime.date.today()
                
            program_start_date = st.date_input(
                "Fecha de Inicio del Programa",
                value=st.session_state.last_saved_date,
                key="program_start_date"
            )
            
            # Verificar si la fecha ha cambiado
            date_changed = program_start_date != st.session_state.last_saved_date

        with col2:
            st.write("") # Espaciador
            st.write("") # Espaciador
            # Mostrar el botón solo si la fecha ha cambiado
            if date_changed and st.button("🚀 Recalcular y Guardar Fechas", type="primary", use_container_width=True):
                with st.spinner("Calculando nuevo cronograma y guardando..."):
                    
                    modules_from_editor = edited_df.to_dict('records')

                    current_modules = [mod for mod in modules_from_editor if isinstance(mod, dict) and mod.get('firebase_key')]

                    if not current_modules:
                        st.warning("No hay módulos existentes para calcular.")
                    else:
                        breaks = parse_breaks(breaks_list)
                        updated_modules_with_dates = calculate_schedule(current_modules, program_start_date, breaks)
                        
                        if updated_modules_with_dates:
                            update_payload = {}
                            for mod in updated_modules_with_dates:
                                firebase_key = mod.get('firebase_key')
                                if firebase_key:
                                    # Sanitizar el diccionario para eliminar NaNs antes de guardar
                                    mod_to_save = {key: value for key, value in mod.items() if key != 'Eliminar' and pd.notna(value)}
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
        
        st.info("Cambie el 'Orden' o 'Semanas' y presione 'Recalcular' para actualizar.", icon="ℹ️")

else:
    st.error("Error de sesión: No se pudo obtener el email del usuario.")