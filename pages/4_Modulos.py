import streamlit as st
import pandas as pd
import datetime
import time
import math
import uuid
from config import setup_page, db
from utils import set_last_updated  
from utils import load_modules

# --- Page Setup and Login Check ---
setup_page("Gestión de Módulos")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

# def load_breaks_from_db():
#     """Load breaks from Firebase and format them for date calculations."""
#     try:
#         breaks_ref = db.child("breaks").get()
#         if not breaks_ref.val():
#             return []
            
#         breaks_list = []
#         for break_id, break_data in breaks_ref.val().items():
#             if not break_data or not isinstance(break_data, dict):
#                 continue
                
#             try:
#                 start_date = datetime.datetime.strptime(break_data.get('start_date', ''), '%Y-%m-%d').date()
#                 duration_weeks = int(break_data.get('duration_weeks', 1))
#                 end_date = start_date + datetime.timedelta(weeks=duration_weeks)
                
#                 breaks_list.append({
#                     'name': break_data.get('name', 'Semana de Descanso'),
#                     'start_date': start_date.strftime('%Y-%m-%d'),
#                     'end_date': end_date.strftime('%Y-%m-%d')
#                 })
#             except (ValueError, KeyError) as e:
#                 st.warning(f"Error al procesar semana de descanso {break_id}: {e}")
#                 continue
                
#         return breaks_list
#     except Exception as e:
#         st.error(f"Error al cargar semanas de descanso: {e}")
#         return []

# # --- DATE CALCULATION LOGIC ---

# def parse_breaks(breaks_data):
#     """
#     Convierte una lista de diccionarios de vacaciones en tuplas de fechas (inicio, fin).
#     Omite entradas inválidas.
#     """
#     parsed = []
#     for b in breaks_data:
#         try:
#             start = datetime.datetime.strptime(b['start_date'], '%Y-%m-%d').date()
#             end = datetime.datetime.strptime(b['end_date'], '%Y-%m-%d').date()
#             parsed.append((start, end))
#         except (ValueError, TypeError):
#             # Saltar entradas de vacaciones inválidas o incompletas
#             continue
#     return parsed

# def adjust_date_for_breaks(current_date, breaks):
#     """
#     Verifica si una fecha cae dentro de un período de vacaciones.
#     Si es así, retorna el día después de que las vacaciones terminan.
#     Si no, retorna la fecha original.
#     """
#     for b_start, b_end in breaks:
#         if b_start <= current_date <= b_end:
#             # La fecha está dentro de unas vacaciones, moverla al día después de las vacaciones
#             return b_end + datetime.timedelta(days=1)
#     # La fecha no está en vacaciones
#     return current_date

# def count_working_days_backward(end_date_inclusive, num_working_days, breaks):
#     """
#     Cuenta `num_working_days` días hábiles hacia atrás desde `end_date_inclusive`,
#     saltándose los días de vacaciones. Retorna la fecha de inicio.
#     """
#     current_date = end_date_inclusive
#     days_counted = 0
    
#     # Iterar hacia atrás, día a día, hasta que hayamos contado suficientes días hábiles
#     while days_counted < num_working_days:
#         # Moverse al día calendario anterior
#         current_date -= datetime.timedelta(days=1)
        
#         # Verificar si este nuevo current_date es un día de vacaciones.
#         # Si lo es, no lo contamos y seguimos moviéndonos hacia atrás.
#         is_break_day = False
#         for b_start, b_end in breaks:
#             if b_start <= current_date <= b_end:
#                 is_break_day = True
#                 break
        
#         if not is_break_day:
#             days_counted += 1 # Solo contar si es un día hábil
            
#     return current_date

# def recalculate_full_schedule(modules_list, breaks, current_module_pivot_order=None, current_module_pivot_start_date=None):
#     """
#     Recalcula el cronograma completo para todos los módulos, utilizando un módulo actual
#     especificado como punto de pivote fijo si se proporciona. Si no hay pivote,
#     comienza desde el primer módulo y calcula hacia adelante desde hoy.
#     """
#     if not modules_list:
#         return []

#     modules_sorted = sorted(
#         modules_list, 
#         key=lambda x: int(x.get('credits') or 999)
#     )
#     modules_dict = {mod['firebase_key']: mod.copy() for mod in modules_sorted}

#     # Determine the actual pivot module and its start date.
#     # If no pivot is provided (e.g., initial load or no active module),
#     # assume the module with the smallest 'credits' starts today.
#     effective_pivot_order = current_module_pivot_order
#     effective_pivot_start_date = current_module_pivot_start_date

#     if not effective_pivot_order or not effective_pivot_start_date:
#         if modules_sorted:
#             # Default to the first module in sorted order starting today
#             effective_pivot_order = int(modules_sorted[0].get('credits') or 1)
#             effective_pivot_start_date = datetime.date.today()
#         else:
#             return [] # No modules to schedule

#     # Find the index of the effective pivot module in the sorted list
#     pivot_list_index = -1
#     for i, mod in enumerate(modules_sorted):
#         if int(mod['credits']) == effective_pivot_order:
#             pivot_list_index = i
#             break
    
#     if pivot_list_index == -1:
#         # This case should ideally not happen if modules_sorted is correctly populated
#         # and default pivot is chosen from it.
#         st.error("Error lógico: El módulo pivote efectivo no se encontró en la lista ordenada.")
#         return []

#     # --- Construct the circular schedule order for one full cycle ---
#     # Start from the pivot module, then cycle through the list
#     full_cycle_schedule_order = []
    
#     # Add modules from the pivot to the end of the sorted list
#     for i in range(pivot_list_index, len(modules_sorted)):
#         full_cycle_schedule_order.append(modules_sorted[i])
        
#     # Add modules from the beginning up to the pivot module (wrapping around)
#     for i in range(0, pivot_list_index):
#         full_cycle_schedule_order.append(modules_sorted[i])

#     # --- Calculate dates based on this circular order ---
#     current_start_date = effective_pivot_start_date # Start from the fixed pivot date

#     for i, mod_data in enumerate(full_cycle_schedule_order):
#         key = mod_data['firebase_key']
        
#         # For the very first module in this new sequence (which is our pivot),
#         # its start date is already determined. We'll adjust its end date.
#         # For subsequent modules, their start date is determined by the previous module's end date + 1.
#         if i == 0: # This is the pivot module in our custom sequence
#             calculated_start = current_start_date
#         else:
#             calculated_start = current_start_date # This 'current_start_date' comes from the previous iteration's 'final_end_date + 1'

#         # Adjust the calculated start date for any breaks
#         adjusted_start = adjust_date_for_breaks(calculated_start, breaks)
        
#         duration_weeks = int(mod_data.get('duration_weeks') or 1)
#         duration_days_to_count = duration_weeks * 7

#         temp_current_date_for_duration = adjusted_start
#         temp_days_counted = 0
#         while temp_days_counted < duration_days_to_count:
#             temp_current_date_for_duration = adjust_date_for_breaks(temp_current_date_for_duration, breaks)
#             temp_days_counted += 1
#             temp_current_date_for_duration += datetime.timedelta(days=1)
#         final_end_date = temp_current_date_for_duration - datetime.timedelta(days=1)
        
#         modules_dict[key]['fecha_inicio_1'] = adjusted_start.isoformat()
#         modules_dict[key]['fecha_fin_1'] = final_end_date.isoformat()
        
#         # The start date for the next module in the sequence
#         current_start_date = final_end_date + datetime.timedelta(days=1)
            
#     return list(modules_dict.values())

# # --- NEW FUNCTION: find_current_module_info ---
# def find_current_module_info(modules_df, today):
#     """
#     Identifica el módulo actual (si lo hay) basado en la fecha de hoy.
#     Retorna la fecha de inicio, orden, y nombre del módulo actual,
#     o None, None, None si no se encuentra un módulo activo.
#     Solo considera el primer ciclo de fechas.
#     """
#     current_module_start = None
#     current_module_order = None
#     current_module_name = None

#     for index, row in modules_df.iterrows():
#         # Convert dates to datetime.date objects for comparison
#         # This acts as a safeguard in case they are still strings or other types
#         fecha_inicio_1 = pd.to_datetime(row['fecha_inicio_1'], errors='coerce').date() if pd.notna(row['fecha_inicio_1']) else None
#         fecha_fin_1 = pd.to_datetime(row['fecha_fin_1'], errors='coerce').date() if pd.notna(row['fecha_fin_1']) else None

#         # Check Cycle 1
#         if fecha_inicio_1 and fecha_fin_1: # Ensure they are valid dates
#             if fecha_inicio_1 <= today <= fecha_fin_1:
#                 current_module_start = fecha_inicio_1
#                 current_module_order = int(row['credits'])
#                 current_module_name = row['name']
#                 return current_module_start, current_module_order, current_module_name
                
#     return None, None, None


# --- DATABASE & CACHE FUNCTIONS ---

# def save_new_module_to_db(user_email, module_data):
#     """Guarda un nuevo módulo en la base de datos de Firebase."""
#     try:
#         user_email_sanitized = user_email.replace('.', ',')
#         db.child("modules").child(user_email_sanitized).push(module_data)
#         set_last_updated('modules', user_email)
#         return True
#     except Exception as e:
#         st.error(f"Error al guardar el módulo en Firebase: {e}")
#         return False

# def delete_module_from_db(user_email, module_key):
#     """Elimina un módulo de la base de datos de Firebase."""
#     if not user_email or not module_key: return False
#     try:
#         user_path = user_email.replace('.', ',')
#         db.child("modules").child(user_path).child(module_key).remove()
#         set_last_updated('modules', user_email)
#         st.toast("✅ Módulo eliminado de la base de datos.")
#         return True
#     except Exception as e:
#         st.error(f"Error al eliminar el módulo: {str(e)}")
#         return False

# def load_modules(user_email_from_session):
#     """Carga los módulos de la base de datos de Firebase para el usuario actual."""
#     if not user_email_from_session: return pd.DataFrame()
#     try:
#         user_email_sanitized = user_email.replace('.', ',')
#         modules_data = db.child("modules").child(user_email_sanitized).get().val()
        
#         if not modules_data or not isinstance(modules_data, dict):
#             return pd.DataFrame()
        
#         processed_list = [
#             {**item, 'firebase_key': key}
#             for key, item in modules_data.items()
#             if item and isinstance(item, dict)
#         ]
#         df = pd.DataFrame(processed_list) if processed_list else pd.DataFrame()
        
#         # Updated expected_cols to match the new date column names (only one cycle)
#         expected_cols = ['module_id', 'name', 'description', 'credits', 'duration_weeks', 'created_at', 
#                           'fecha_inicio_1', 'fecha_fin_1']
#         for col in expected_cols:
#             if col not in df.columns:
#                 df[col] = None
        
#         # Convert date columns to datetime.date objects here after DataFrame creation
#         date_cols_to_convert = ['fecha_inicio_1', 'fecha_fin_1']
#         for col in date_cols_to_convert:
#             if col in df.columns and df[col].notna().any(): # Only convert if column exists and has non-NaN values
#                 df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        
#         # Ordenar el dataframe por 'credits' para la visualización inicial
#         if 'credits' in df.columns:
#             df = df.sort_values(by='credits').reset_index(drop=True)
#         return df

#     except Exception as e:
#         st.error(f"Error al cargar módulos de Firebase: {e}")
#         return pd.DataFrame()

def invalidate_cache_and_rerun():
    """Invalida el DataFrame en caché y vuelve a ejecutar la aplicación."""
    if 'modules_df' in st.session_state:
        del st.session_state.modules_df
    st.rerun()

def highlight_current_module(row):
    today = datetime.date.today()
    try:
        start_date = datetime.datetime.strptime(row['Inicio'], '%m/%d/%Y').date()
        end_date = datetime.datetime.strptime(row['Fin'], '%m/%d/%Y').date()
        if start_date <= today <= end_date:
            return ['background-color: #e6f7ff'] * len(row)
    except:
        pass
    return [''] * len(row)

# --- MAIN APP LOGIC ---
user_email = st.session_state.get('email')

if 'modules_df' not in st.session_state:
    st.session_state.modules_df = None

# --- FORMULARIO PARA AGREGAR NUEVO MÓDULO ---
# st.subheader("Agregar Nuevo Módulo")
# with st.form("new_module_form", clear_on_submit=True):
#     col_nombre, col_desc = st.columns(2)
#     module_name = col_nombre.text_input("Nombre del Módulo")
#     module_description = col_desc.text_input("Descripción")
    
#     col_orden, col_duracion = st.columns(2)
#     module_credits = col_orden.number_input("Orden (Créditos)", min_value=1, step=1)
#     module_duration_weeks = col_duracion.number_input("Duración (Semanas)", min_value=1, step=1)
    
#     submitted_new_module = st.form_submit_button("Agregar Módulo")
#     if submitted_new_module and user_email:
#         if not module_name:
#             st.warning("El nombre del módulo es obligatorio.")
#         else:
#             # Load current modules to check for duplicates
#             current_modules_df = load_modules(user_email)
#             if not current_modules_df.empty and module_credits in current_modules_df['credits'].values:
#                 st.warning(f"Ya existe un módulo con la orden (créditos) '{module_credits}'. Por favor, elija un valor diferente.")
#             else:
#                 new_module_data = {
#                     'module_id': str(uuid.uuid4()),
#                     'name': module_name,
#                     'description': module_description,
#                     'credits': module_credits,
#                     'duration_weeks': module_duration_weeks,
#                     'created_at': datetime.datetime.now().isoformat()
#                     # Las fechas se omiten intencionadamente; se calcularán más tarde.
#                 }
#                 if save_new_module_to_db(user_email, new_module_data):
#                     st.success(f"Módulo '{module_name}' agregado. Ahora se recalcularán las fechas automáticamente.")
#                     invalidate_cache_and_rerun()
#                 else:
#                     st.error("No se pudo guardar el módulo.")

# --- MOSTRAR/EDITAR MÓDULOS EXISTENTES ---
st.divider()
if user_email:
    # Cargar desde la base de datos si el caché está vacío
    if 'modules_df' not in st.session_state or st.session_state.modules_df is None:
        with st.spinner("Cargando módulos..."):
            st.session_state.modules_df = load_modules(user_email)
    
    modules_df = st.session_state.modules_df

    if modules_df.empty:
        st.info("No hay módulos existentes. Contacte con el administrador.")
    else:
        st.subheader("Módulos")
        st.info("Los módulos se muestran en orden cronológico, con el módulo actual destacado.")
        modules_df = modules_df.rename(columns={
            'name': 'Nombre', 
            'description': 'Descripción', 
            'credits': 'Orden', 
            'duration_weeks': 'Duración (Semanas)', 
            'fecha_inicio_1': 'Inicio',
            'fecha_fin_1': 'Fin'})
        modules_df = modules_df[['Nombre', 'Descripción', 'Orden', 'Duración (Semanas)', 'Inicio', 'Fin']]
        # Convert 'Inicio' and 'Fin' to datetime
        modules_df['Inicio'] = pd.to_datetime(modules_df['Inicio'], errors='coerce', dayfirst=True)
        modules_df['Fin'] = pd.to_datetime(modules_df['Fin'], errors='coerce', dayfirst=True)

        # Sort by actual datetime
        modules_df = modules_df.sort_values('Inicio')

        # Format as strings for display (after sorting)
        for col in ['Inicio', 'Fin']:
            if col in modules_df.columns:
                modules_df[col] = modules_df[col].apply(lambda x: x.strftime('%m/%d/%Y') if pd.notna(x) else '')

        # Ensure correct types for other columns
        modules_df['Orden'] = modules_df['Orden'].astype(int)
        modules_df['Duración (Semanas)'] = modules_df['Duración (Semanas)'].astype(int)

        column_properties = {
            'Duración (Semanas)': 'width: 80px;',  # Adjust the width as needed
            'Orden': 'width: 60px;'  # Also making Orden narrower for consistency
        }

        styled_df = modules_df.style.apply(highlight_current_module, axis=1)
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
        # # --- Automatic Recalculation Logic ---
        # breaks_data = load_breaks_from_db()
        # breaks = parse_breaks(breaks_data)
        # today = datetime.date.today()

        # # Find the current module's info (only for Cycle 1)
        # current_module_start, current_module_order, current_module_name = \
        #     find_current_module_info(modules_df, today)

        # recalculate_needed = False
        # recalculation_reason = ""

        # # Get the currently stored dates from modules_df for comparison later
        # current_dates_df = modules_df[['firebase_key', 'fecha_inicio_1', 'fecha_fin_1']].copy()
        # # Convert to string to avoid issues with NaT vs None in comparison
        # for col in ['fecha_inicio_1', 'fecha_fin_1']:
        #     current_dates_df[col] = current_dates_df[col].astype(str)

        # pivot_order_for_calc = None
        # pivot_start_date_for_calc = None

        # if current_module_start:
        #     # If a current module is found, use its start date and order as the pivot
        #     pivot_start_date_for_calc = current_module_start
        #     pivot_order_for_calc = current_module_order
        #     recalculate_needed = True
        #     recalculation_reason = f"El cronograma se está recalculando automáticamente basado en el módulo actual: '{current_module_name}' (Orden {current_module_order}) que inició el {current_module_start.strftime('%Y-%m-%d')}."
        # elif not modules_df.empty:
        #     # If there are modules but none are 'current' today,
        #     # assume the module with the lowest 'credits' order starts today as the pivot.
        #     pivot_order_for_calc = modules_df['credits'].min()
        #     pivot_start_date_for_calc = today # Starts from today
            
        #     # Ensure selected_module_order_for_calculation has a valid name for the message
        #     if not modules_df.empty and pivot_order_for_calc in modules_df['credits'].values:
        #         first_module_name = modules_df[modules_df['credits'] == pivot_order_for_calc]['name'].iloc[0]
        #     else:
        #         first_module_name = "el Módulo 1" # Fallback if module name not found (e.g., no modules or first module order is not 1)

        #     recalculate_needed = True
        #     recalculation_reason = f"No se detectó un módulo activo hoy. Recalculando el cronograma asumiendo que {first_module_name} (Orden {pivot_order_for_calc}) comienza hoy."
        # else:
        #     # No modules exist, no recalculation needed yet.
        #     recalculate_needed = False

        # if recalculate_needed:
        #     st.info(recalculation_reason, icon="ℹ️")
        #     with st.spinner("Calculando nuevo cronograma..."):
        #         modules_list_for_calc = modules_df.to_dict('records')

        #         # Call the refactored recalculate_full_schedule
        #         updated_modules_with_dates_list = recalculate_full_schedule(
        #             modules_list_for_calc,
        #             breaks,
        #             current_module_pivot_order=pivot_order_for_calc,
        #             current_module_pivot_start_date=pivot_start_date_for_calc
        #         )
                
        #         # Convert the calculated list back to a DataFrame for comparison
        #         calculated_df_temp = pd.DataFrame(updated_modules_with_dates_list)
        #         calculated_df_compare = calculated_df_temp[['firebase_key', 'fecha_inicio_1', 'fecha_fin_1']].copy()
        #         for col in ['fecha_inicio_1', 'fecha_fin_1']:
        #             calculated_df_compare[col] = calculated_df_compare[col].astype(str)
                
        #         # Merge with current_dates_df to compare dates for the same firebase_key
        #         merged_df = pd.merge(current_dates_df, calculated_df_compare, on='firebase_key', suffixes=('_current', '_calc'), how='left')
                
        #         # Identify if any date column has changed
        #         dates_have_changed = False
        #         for col_name in ['fecha_inicio_1', 'fecha_fin_1']:
        #             # Compare if there are any differences
        #             # Use .fillna('') to treat NaN/None/NaT consistently as empty string for comparison
        #             if not merged_df[f"{col_name}_current"].fillna('').equals(merged_df[f"{col_name}_calc"].fillna('')):
        #                 dates_have_changed = True
        #                 break

        #         if dates_have_changed:
        #             update_payload = {}
        #             for mod in updated_modules_with_dates_list:
        #                 firebase_key = mod.get('firebase_key')
        #                 if firebase_key:
        #                     mod_to_save = {key: value for key, value in mod.items() if key != 'Eliminar' and pd.notna(value)}
        #                     update_payload[firebase_key] = mod_to_save

        #             if update_payload:
        #                 try:
        #                     user_path = user_email.replace('.', ',')
        #                     db.child("modules").child(user_path).update(update_payload)
        #                     st.success("¡Cronograma recalculado y guardado exitosamente!")
        #                     time.sleep(1)
        #                     invalidate_cache_and_rerun() # Rerun to display updated data
        #                 except Exception as e:
        #                     st.error(f"Error al guardar el cronograma actualizado: {e}")
        #             else:
        #                 st.warning("No se encontraron módulos con fechas para actualizar.")
        #         else:
        #             st.info("Las fechas ya están actualizadas. No se requiere guardar el cronograma.")
        
        # st.subheader("Módulos Existentes y Planificación")

        # # --- FUNCIÓN PARA GUARDAR MÓDULOS ACTUALIZADOS ---
        # # def save_updated_modules(updated_df):
        # #     try:
        # #         update_payload = {}
        # #         for _, row in updated_df.iterrows():
        # #             if pd.notna(row.get('firebase_key')):
        # #                 mod_updates = row.drop('Eliminar', errors='ignore').to_dict()
                        
        # #                 clean_updates = {}
        # #                 for k, v in mod_updates.items():
        # #                     if v is None or pd.isna(v) or k == 'firebase_key':
        # #                         continue
                                
        # #                     if hasattr(v, 'item'): # Convert numpy types to Python native types
        # #                         v = v.item()
                                
        # #                     if isinstance(v, (datetime.date, datetime.datetime)): # Convert date objects to ISO format strings
        # #                         v = v.isoformat()
                                
        # #                     clean_updates[k] = v
                                
        # #                 if clean_updates:  # Solo agregar si hay actualizaciones
        # #                     update_payload[row['firebase_key']] = clean_updates
                
        # #         if update_payload:
        # #             user_path = user_email.replace('.', ',')
        # #             db.child("modules").child(user_path).update(update_payload)
        # #             set_last_updated('modules', user_email)
        # #             return True, "¡Cambios guardados exitosamente!"
        # #         return False, "No hay cambios para guardar."
        # #     except Exception as e:
        # #         import traceback
        # #         return False, f"Error al guardar cambios: {str(e)}\n{traceback.format_exc()}"

        # # --- EDITOR DE DATOS (Definido antes de cualquier lógica que use su salida) ---
        # df_to_edit = modules_df.copy()
        
        # # Define the date columns directly with the desired names (only one cycle)
        # date_columns = ['fecha_inicio_1', 'fecha_fin_1']
        
        # # Convertir las columnas de fecha a tipo datetime.date para el data_editor (ya se hizo en load_modules, pero es una doble verificación)
        # for col in date_columns:
        #     if col in df_to_edit.columns:
        #         try:
        #             df_to_edit[col] = pd.to_datetime(df_to_edit[col], errors='coerce').dt.date
        #         except Exception as e:
        #             st.error(f"Error al convertir la columna {col} a fecha para visualización: {str(e)}")
        # df_to_edit['Eliminar'] = False
        
        # # Configuración de columnas en el orden solicitado (solo un ciclo)
        # column_config = {
        #     "Eliminar": st.column_config.CheckboxColumn("Borrar", help="Seleccione para eliminar", default=False, width="small"),
        #     "name": st.column_config.TextColumn("Nombre del Módulo", required=True),
        #     "duration_weeks": st.column_config.NumberColumn("Semanas", format="%d", min_value=1, required=True, width="small"),
        #     "credits": st.column_config.NumberColumn("Orden", format="%d", min_value=1, required=True, width="small"),
        #     "fecha_inicio_1": st.column_config.DateColumn("Fecha Inicio", format="MM/DD/YYYY", disabled=True),
        #     "fecha_fin_1": st.column_config.DateColumn("Fecha Fin", format="MM/DD/YYYY", disabled=True),
        #     "module_id": None, "firebase_key": None, "description": None, "created_at": None, "updated_at": None,
        # }
        
        # # Ordenar las columnas según el orden deseado (solo un ciclo)
        # column_order = [
        #     "Eliminar", 
        #     "name", 
        #     "duration_weeks", 
        #     "credits", 
        #     "fecha_inicio_1", 
        #     "fecha_fin_1"
        # ]
        
        # # Asegurarse de que solo se incluyan las columnas que existen en el DataFrame
        # column_order = [col for col in column_order if col in df_to_edit.columns]
        
        # # Reordenar el DataFrame
        # df_to_edit = df_to_edit[column_order + [col for col in df_to_edit.columns if col not in column_order]]
        
        # # Esta es la única fuente de verdad. Siempre es un DataFrame.
        # # Usando num_rows="fixed" para evitar añadir nuevas filas
        # edited_df = st.data_editor(
        #     df_to_edit,
        #     column_config=column_config,
        #     hide_index=True,
        #     num_rows="fixed",
        #     key="modules_editor_main",
        #     use_container_width=True,
        # )
        
        # # Verificar cambios y eliminaciones
        # has_changes = not edited_df.equals(df_to_edit)
        # rows_to_delete = edited_df[edited_df['Eliminar'] == True]
        # has_deletions = not rows_to_delete.empty

        # # Crear columnas para botones
        # col1, col2 = st.columns([1, 3])
        
        # # Botón "Guardar Cambios"
        # if has_changes:
        #     with col1:
        #         if st.button("💾 Guardar Cambios", type="primary"):
        #             success, message = save_updated_modules(edited_df)
        #             if success:
        #                 st.success(message)
        #                 invalidate_cache_and_rerun()
        #             else:
        #                 st.error(message)
            
        # # Botón "Confirmar Eliminación"
        # if has_deletions:
        #     with col2:
        #         if st.button("🗑️ Confirmar Eliminación"):
        #             keys_to_delete = rows_to_delete['firebase_key'].tolist()
        #             deleted_count = 0
        #             with st.spinner("Eliminando módulos..."):
        #                 for key in keys_to_delete:
        #                     if delete_module_from_db(user_email, key):
        #                         deleted_count += 1
                    
        #             st.success(f"{deleted_count} módulo(s) eliminados. Se recalculará el cronograma automáticamente.")
        #             invalidate_cache_and_rerun()
        
        # # Mensajes de estado
        # if has_changes:
        #     st.warning("Tiene cambios sin guardar. Haga clic en 'Guardar Cambios' para guardar sus modificaciones.")
        # elif has_deletions:
        #     st.warning("Ha marcado módulos para eliminar. La eliminación es permanente.")
        # else:
        #     st.info("Realice cambios en la tabla y haga clic en 'Guardar Cambios' para guardar.")

        # # --- Se elimina la UI de Recalculación Manual ---
        # st.info("El cronograma de módulos se recalcula automáticamente al cargar la página o al agregar/eliminar módulos, basándose en la fecha actual y el módulo activo.", icon="💡")


else:
    st.error("Error de sesión: No se pudo obtener el email del usuario.")
