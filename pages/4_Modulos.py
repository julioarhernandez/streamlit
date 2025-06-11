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

def count_working_days_backward(end_date_inclusive, num_working_days, breaks):
    """
    Cuenta `num_working_days` días hábiles hacia atrás desde `end_date_inclusive`,
    saltándose los días de vacaciones. Retorna la fecha de inicio.
    """
    current_date = end_date_inclusive
    days_counted = 0
    
    # Iterar hacia atrás, día a día, hasta que hayamos contado suficientes días hábiles
    while days_counted < num_working_days:
        # Moverse al día calendario anterior
        current_date -= datetime.timedelta(days=1)
        
        # Verificar si este nuevo current_date es un día de vacaciones.
        # Si lo es, no lo contamos y seguimos moviéndonos hacia atrás.
        is_break_day = False
        for b_start, b_end in breaks:
            if b_start <= current_date <= b_end:
                is_break_day = True
                break
        
        if not is_break_day:
            days_counted += 1 # Solo contar si es un día hábil
            
    return current_date

def find_true_program_start_date(modules_list, desired_module_start_date, desired_module_order, breaks):
    """
    Calcula la fecha de inicio real del programa (módulo con orden 1)
    dada una fecha de inicio deseada para un módulo específico y su orden.
    """
    if not modules_list:
        return desired_module_start_date # Si no hay módulos, la fecha de inicio es la proporcionada

    modules_sorted = sorted(
        modules_list,
        key=lambda x: int(x.get('credits') or 999)
    )

    pivot_module_index = -1
    for i, mod in enumerate(modules_sorted):
        if int(mod.get('credits') or 0) == desired_module_order:
            pivot_module_index = i
            break
    
    if pivot_module_index == -1:
        # Si no se encuentra el orden de módulo deseado, asumir que desired_module_start_date es para el módulo 1
        st.warning(f"No se encontró un módulo con orden '{desired_module_order}'. Asumiendo que la fecha de inicio del programa es para el primer módulo.")
        return desired_module_start_date # Retornar la fecha proporcionada, asumiendo que es para el módulo 1

    # Si el módulo pivote es el primer módulo, entonces la fecha de inicio del programa es la deseada.
    if desired_module_order == 1:
        return desired_module_start_date

    # El inicio del módulo pivote es fijo por el usuario.
    # El fin del módulo anterior es el día antes del inicio del módulo pivote.
    current_end_for_prev_module = desired_module_start_date - datetime.timedelta(days=1)
    
    # Recorrer los módulos hacia atrás desde el módulo anterior al pivote hasta el primer módulo.
    for i in range(pivot_module_index - 1, -1, -1): # Iterar hacia atrás desde el módulo antes del pivote
        prev_mod_data = modules_sorted[i]
        
        duration_weeks_prev = int(prev_mod_data.get('duration_weeks') or 1)
        duration_days_prev = duration_weeks_prev * 7

        # Calcular la fecha de inicio del módulo anterior
        # current_end_for_prev_module es el día *inclusive* de fin del módulo anterior.
        calculated_start_prev = count_working_days_backward(current_end_for_prev_module, duration_days_prev, breaks)
        
        # Si este es el primer módulo (orden 1), hemos encontrado la fecha de inicio real del programa.
        if int(prev_mod_data.get('credits') or 0) == 1:
            return calculated_start_prev
            
        # Para la próxima iteración hacia atrás, el fin del módulo "anterior a este"
        # será el día antes del inicio de `prev_mod_data`.
        current_end_for_prev_module = calculated_start_prev - datetime.timedelta(days=1)
        
    # Si por alguna razón no se encontró el módulo 1 en el bucle (lo cual no debería ocurrir si los datos son coherentes),
    # retornar la fecha de inicio deseada como un valor de seguridad.
    return desired_module_start_date


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

# --- NEW FUNCTION: find_current_module_info ---
def find_current_module_info(modules_df, today):
    """
    Identifica el módulo actual (si lo hay) basado en la fecha de hoy.
    Retorna la fecha de inicio, orden, nombre y ciclo del módulo actual,
    o None, None, None, None si no se encuentra un módulo activo.
    """
    current_module_start = None
    current_module_order = None
    current_module_name = None
    current_cycle = None

    for index, row in modules_df.iterrows():
        # Convert dates to datetime.date objects for comparison
        # This acts as a safeguard in case they are still strings or other types
        fecha_inicio_1 = pd.to_datetime(row['fecha_inicio_1'], errors='coerce').date() if pd.notna(row['fecha_inicio_1']) else None
        fecha_fin_1 = pd.to_datetime(row['fecha_fin_1'], errors='coerce').date() if pd.notna(row['fecha_fin_1']) else None
        fecha_inicio_2 = pd.to_datetime(row['fecha_inicio_2'], errors='coerce').date() if pd.notna(row['fecha_inicio_2']) else None
        fecha_fin_2 = pd.to_datetime(row['fecha_fin_2'], errors='coerce').date() if pd.notna(row['fecha_fin_2']) else None

        # Check Cycle 1
        if fecha_inicio_1 and fecha_fin_1: # Ensure they are valid dates
            if fecha_inicio_1 <= today <= fecha_fin_1:
                current_module_start = fecha_inicio_1
                current_module_order = int(row['credits'])
                current_module_name = row['name']
                current_cycle = 1
                return current_module_start, current_module_order, current_module_name, current_cycle
        
        # Check Cycle 2
        if fecha_inicio_2 and fecha_fin_2: # Ensure they are valid dates
            if fecha_inicio_2 <= today <= fecha_fin_2:
                current_module_start = fecha_inicio_2
                current_module_order = int(row['credits'])
                current_module_name = row['name']
                current_cycle = 2
                return current_module_start, current_module_order, current_module_name, current_cycle
                
    return None, None, None, None


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
        
        # Convert date columns to datetime.date objects here after DataFrame creation
        date_cols_to_convert = ['fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']
        for col in date_cols_to_convert:
            if col in df.columns and df[col].notna().any(): # Only convert if column exists and has non-NaN values
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        
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
            # Load current modules to check for duplicates
            current_modules_df = load_modules(user_email)
            if not current_modules_df.empty and module_credits in current_modules_df['credits'].values:
                st.warning(f"Ya existe un módulo con la orden (créditos) '{module_credits}'. Por favor, elija un valor diferente.")
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
                    st.success(f"Módulo '{module_name}' agregado. Ahora se recalcularán las fechas automáticamente.")
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
        # --- Automatic Recalculation Logic ---
        breaks = parse_breaks(breaks_list)
        today = datetime.date.today()

        # Find the current module's info
        current_module_start, current_module_order, current_module_name, current_cycle = \
            find_current_module_info(modules_df, today)

        recalculate_needed = False
        recalculation_reason = ""

        # Get the currently stored dates from modules_df for comparison later
        # Create a simplified DataFrame for comparison of only date columns
        current_dates_df = modules_df[['firebase_key', 'fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']].copy()
        # Convert to string to avoid issues with NaT vs None in comparison
        for col in ['fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']:
            current_dates_df[col] = current_dates_df[col].astype(str)

        if current_module_start:
            program_start_date_for_calculation = current_module_start
            selected_module_order_for_calculation = current_module_order
            recalculate_needed = True
            recalculation_reason = f"El cronograma se está recalculando automáticamente basado en el módulo actual: '{current_module_name}' (Orden {current_module_order}, Ciclo {current_cycle}) que inició el {current_module_start.strftime('%Y-%m-%d')}."
        elif not modules_df.empty and not current_module_start:
            program_start_date_for_calculation = today
            selected_module_order_for_calculation = modules_df['credits'].min()
            recalculate_needed = True
            recalculation_reason = f"No se detectó un módulo activo hoy. Recalculando el cronograma asumiendo que el Módulo '{modules_df[modules_df['credits'] == selected_module_order_for_calculation]['name'].iloc[0]}' (Orden {selected_module_order_for_calculation}) comienza hoy."
        else:
            recalculate_needed = False

        if recalculate_needed:
            st.info(recalculation_reason, icon="ℹ️")
            with st.spinner("Calculando nuevo cronograma..."):
                modules_list_for_calc = modules_df.to_dict('records')

                true_start_date_for_program = find_true_program_start_date(
                    modules_list_for_calc,
                    program_start_date_for_calculation,
                    selected_module_order_for_calculation,
                    breaks
                )
                
                updated_modules_with_dates_list = calculate_schedule(
                    modules_list_for_calc,
                    true_start_date_for_program,
                    breaks
                )
                
                # Convert the calculated list back to a DataFrame for comparison
                # Ensure the same columns and types are used for accurate comparison
                calculated_df_temp = pd.DataFrame(updated_modules_with_dates_list)
                # Select only the date columns for comparison, and ensure 'firebase_key' is present
                calculated_df_compare = calculated_df_temp[['firebase_key', 'fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']].copy()
                # Convert to string to avoid issues with NaT vs None in comparison
                for col in ['fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']:
                    calculated_df_compare[col] = calculated_df_compare[col].astype(str)
                
                # Merge with current_dates_df to compare dates for the same firebase_key
                merged_df = pd.merge(current_dates_df, calculated_df_compare, on='firebase_key', suffixes=('_current', '_calc'), how='left')
                
                # Identify if any date column has changed
                dates_have_changed = False
                for col_name in ['fecha_inicio_1', 'fecha_fin_1', 'fecha_inicio_2', 'fecha_fin_2']:
                    if not merged_df[f"{col_name}_current"].equals(merged_df[f"{col_name}_calc"]):
                        dates_have_changed = True
                        break

                if dates_have_changed:
                    update_payload = {}
                    for mod in updated_modules_with_dates_list:
                        firebase_key = mod.get('firebase_key')
                        if firebase_key:
                            mod_to_save = {key: value for key, value in mod.items() if key != 'Eliminar' and pd.notna(value)}
                            update_payload[firebase_key] = mod_to_save

                    if update_payload:
                        try:
                            user_path = user_email.replace('.', ',')
                            db.child("modules").child(user_path).update(update_payload)
                            st.success("¡Cronograma recalculado y guardado exitosamente!")
                            time.sleep(1)
                            invalidate_cache_and_rerun() # Rerun to display updated data
                        except Exception as e:
                            st.error(f"Error al guardar el cronograma actualizado: {e}")
                    else:
                        st.warning("No se encontraron módulos con fechas para actualizar.")
                else:
                    st.info("Las fechas ya están actualizadas. No se requiere guardar el cronograma.")
        
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
        
        # Convertir las columnas de fecha a tipo datetime.date para el data_editor (ya se hizo en load_modules, pero es una doble verificación)
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
                    
                    st.success(f"{deleted_count} módulo(s) eliminados. Se recalculará el cronograma automáticamente.")
                    invalidate_cache_and_rerun()
        
        # Mensajes de estado
        if has_changes:
            st.warning("Tiene cambios sin guardar. Haga clic en 'Guardar Cambios' para guardar sus modificaciones.")
        elif has_deletions:
            st.warning("Ha marcado módulos para eliminar. La eliminación es permanente.")
        else:
            st.info("Realice cambios en la tabla y haga clic en 'Guardar Cambios' para guardar.")

        # --- Se elimina la UI de Recalculación Manual ---
        st.info("El cronograma de módulos se recalcula automáticamente al cargar la página o al agregar/eliminar módulos, basándose en la fecha actual y el módulo activo.", icon="💡")


else:
    st.error("Error de sesión: No se pudo obtener el email del usuario.")