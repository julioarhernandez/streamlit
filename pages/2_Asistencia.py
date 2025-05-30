# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\pages\2_Asistencia.py
import streamlit as st
import pandas as pd
import datetime
import re
import io
import time
from utils import save_attendance, load_students, load_attendance, delete_attendance_dates, get_attendance_dates
from config import setup_page

# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()
# --- End Login Check ---

# Setup page title (now that config is done and user is logged in)
setup_page("Gestión de Asistencia")

# --- Session State Initialization ---
if 'uploader_key_suffix' not in st.session_state:
    st.session_state.uploader_key_suffix = 0  # Initialize as integer

if 'current_batch_data_by_date' not in st.session_state:
    st.session_state.current_batch_data_by_date = {}

if 'prepared_attendance_dfs' not in st.session_state:
    st.session_state.prepared_attendance_dfs = {}

if 'processed_files_this_session' not in st.session_state:
    st.session_state.processed_files_this_session = set()

# --- Helper Functions (extract_date_from_filename, parse_attendance_report) ---
# def extract_date_from_filename(filename: str) -> datetime.date | None:
#     match_keyword = re.search(r'Informe de Asistencia ', filename, re.IGNORECASE)
#     if match_keyword:
#         date_str_candidate = filename[match_keyword.end():]
#         match_date = re.match(r'(\d{1,2})-(\d{1,2})-(\d{2})', date_str_candidate)
#         if match_date:
#             month, day, year_short = map(int, match_date.groups())
#             year = 2000 + year_short
#             try:
#                 return datetime.date(year, month, day)
#             except ValueError:
#                 return None
#     return None
def extract_date_from_filename(filename: str) -> datetime.date | None:
    # Define patterns to match
    patterns = [
        r'(Informe de Asistencia )',
        r'(Attendance report )'
    ]

    for pattern in patterns:
        match_keyword = re.search(pattern, filename, re.IGNORECASE)
        if match_keyword:
            # Get the part after the matched keyword
            date_str_candidate = filename[match_keyword.end():]

            # Look for date pattern at the start
            match_date = re.match(r'(\d{1,2})-(\d{1,2})-(\d{2})', date_str_candidate)
            if match_date:
                month, day, year_short = map(int, match_date.groups())
                year = 2000 + year_short
                try:
                    return datetime.date(year, month, day)
                except ValueError:
                    return None
    return None


def parse_attendance_report(file_content_str: str, filename_for_debug: str) -> list:
    lines = file_content_str.splitlines()
    start_marker_found_at = -1
    end_marker_found_at = -1

    for i, line in enumerate(lines):
        line_stripped_lower = line.strip().lower()
        if line_stripped_lower.startswith("2. participants"):
            start_marker_found_at = i
            continue 
        if start_marker_found_at != -1 and line_stripped_lower.startswith("3. in-meeting activities"):
            end_marker_found_at = i
            break 

    if start_marker_found_at == -1:
        st.warning(f"No se pudo encontrar el marcador de sección '2. Participants' en '{filename_for_debug}'.")
        return []

    actual_data_start_index = start_marker_found_at + 1
    actual_data_end_index = end_marker_found_at if end_marker_found_at != -1 else len(lines)

    participant_data_lines = lines[actual_data_start_index : actual_data_end_index]

    if not participant_data_lines:
        st.warning(f"No se encontraron líneas de datos entre '2. Participantes' y '3. Actividades en la reunión' (o fin de archivo) en '{filename_for_debug}'.")
        return []

    header_row_index_in_block = -1
    for i, line_in_block in enumerate(participant_data_lines):
        line_norm = line_in_block.strip().lower()
        if "name" in line_norm and ("first join" in line_norm or "last leave" in line_norm or "email" in line_norm or "duration" in line_norm):
            header_row_index_in_block = i
            break
    if header_row_index_in_block == -1:
        st.warning(f"No se pudo encontrar la fila de encabezado en el archivo: {filename_for_debug}")
        return []

    csv_like_data_for_pandas = "\n".join(participant_data_lines[header_row_index_in_block:])
    
    try:
        df = pd.read_csv(io.StringIO(csv_like_data_for_pandas), sep='\t')
        df.columns = [col.strip().lower() for col in df.columns] 
        
        if "name" in df.columns:
            return df["name"].astype(str).str.strip().unique().tolist()
        else:
            st.warning(f"Columna 'nombre' no encontrada después del análisis en '{filename_for_debug}'. Columnas encontradas: {df.columns.tolist()}")
            return []
    except pd.errors.EmptyDataError:
        st.warning(f"No se pudieron analizar filas de datos del contenido CSV en '{filename_for_debug}'. El encabezado identificado podría haber sido la última línea o los datos estaban vacíos.")
        return []
    except Exception as e:
        st.error(f"Error analizando datos CSV de la sección 'Participantes' de '{filename_for_debug}': {e}")
        return []

# --- Main UI --- 
st.header("Archivos de Asistencia guardados")

with st.expander("Ver lista de fechas"):
    try:
        # Get all attendance dates
        all_attendance = get_attendance_dates()
        
        if all_attendance:
            # Create a DataFrame with the dates and a delete column
            dates_df = pd.DataFrame({
                'Fecha': [datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%Y-%m-%d') for d in all_attendance],
                'Eliminar': [False] * len(all_attendance)
            })
            
            # Display the data editor
            with st.form("attendance_dates_form"):
                st.write("Seleccione las asistencias a eliminar:")
                edited_df = st.data_editor(
                    dates_df,
                    column_config={
                        "Fecha": st.column_config.TextColumn("Fecha", disabled=True),
                        "Eliminar": st.column_config.CheckboxColumn("Seleccionar para eliminar")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Add buttons for actions
                col1, col2, _ = st.columns([3, 3,4])
                with col1:
                    delete_selected = st.form_submit_button("Eliminar seleccionados", type="secondary")
                with col2:
                    delete_all = st.form_submit_button("Eliminar todo", type="primary")
                
                if delete_selected:
                    try:
                        # It's good practice to ensure edited_df is what you expect
                        if edited_df is not None:
                            selected_rows = edited_df[edited_df['Eliminar']]
                            if not selected_rows.empty:
                                to_delete = selected_rows['Fecha'].tolist()
                            else:
                                to_delete = []
                        else:
                            to_delete = []
                            st.error("Error interno: No se pudieron obtener los datos editados.")

                        if to_delete: # Only proceed if to_delete is a non-empty list
                            if delete_attendance_dates(to_delete): # This is the crucial call
                                st.success(f"Se eliminaron {len(to_delete)} asistencias correctamente.")
                                st.session_state.uploader_key_suffix += 1
                                st.rerun()
                            else:
                                st.error("Error al eliminar las asistencias seleccionadas (la función de borrado informó un fallo).")
                        else:
                            # This handles both cases: nothing selected, or edited_df was None
                            if edited_df is not None: # Only show warning if data editor was available
                                st.warning("Por favor seleccione al menos una asistencia para eliminar. (La lista 'to_delete' estaba vacía).")
                            
                    except Exception as e_selected:
                        st.error(f"Error crítico procesando la eliminación de seleccionados: {str(e_selected)}")


                        
                elif delete_all:
                    if st.toggle("¿Está seguro que desea eliminar TODAS las asistencias?", key="confirm_delete_all"):
                        if delete_attendance_dates(delete_all=True):
                            # Clear all relevant session state variables
                            uploaded_reports = []
                            st.session_state.current_batch_data_by_date = {}
                            st.session_state.prepared_attendance_dfs = {}
                            st.session_state.processed_files_this_session = set()
                            # Increment the uploader key suffix to force a new file uploader
                            st.session_state.uploader_key_suffix += 1
                            st.success("Todas las asistencias han sido eliminadas correctamente.")
                            st.rerun()
                        else:
                            st.error("Error al eliminar las asistencias.")
        else:
            st.info("No hay asistencias registradas.")
        
    except Exception as e:
        st.error(f"Error al cargar las asistencias: {str(e)}")

# --- Main UI --- 
st.header("Subir Archivos de Informe de Asistencia")
uploaded_reports = st.file_uploader(
    "Las fechas se detectarán de los nombres de archivo.",
    type=['csv'],
    accept_multiple_files=True,
    key=f"report_uploader_daily_{st.session_state.uploader_key_suffix}",
    help="Suba archivos CSV. La fecha se detecta del nombre de archivo (p.ej., '...Attendance Report MM-DD-YY.csv')"
)

if uploaded_reports:
    files_processed_summary = {}
    files_skipped_summary = {}

    for report_file in uploaded_reports:
        if report_file.name in st.session_state.processed_files_this_session:
            continue

        file_date = extract_date_from_filename(report_file.name)

        if not file_date:
            st.warning(f"Omitiendo '{report_file.name}': No se pudo extraer la fecha del nombre del archivo.")
            files_skipped_summary[report_file.name] = "Sin fecha en el nombre del archivo"
            st.session_state.processed_files_this_session.add(report_file.name)
            continue

        file_bytes = report_file.getvalue()
        file_content_str = None
        successful_encoding = None
        tried_encodings_list = ['utf-16', 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252'] 

        try:
            file_content_str = file_bytes.decode('utf-16')
            successful_encoding = 'utf-16'
        except UnicodeDecodeError:
            other_encodings_to_attempt = [enc for enc in tried_encodings_list if enc != 'utf-16']
            for enc in other_encodings_to_attempt:
                try:
                    file_content_str = file_bytes.decode(enc)
                    successful_encoding = enc
                    break 
                except UnicodeDecodeError:
                    continue
        
        if file_content_str is None:
            st.error(f"Error al decodificar '{report_file.name}'. Intentados: {', '.join(tried_encodings_list)}. El archivo podría estar corrupto o en una codificación no soportada.")
            files_skipped_summary[report_file.name] = "Falló la decodificación"
            st.session_state.processed_files_this_session.add(report_file.name)
            continue

        names_from_report = parse_attendance_report(file_content_str, report_file.name)
        
        if names_from_report:
            st.session_state.current_batch_data_by_date.setdefault(file_date, set()).update(names_from_report)
            files_processed_summary.setdefault(file_date, []).append(report_file.name)
        else:
            st.warning(f"No se pudieron extraer nombres de '{report_file.name}' (después de decodificación exitosa). Verifique la lógica del analizador o la estructura del archivo.")
            files_skipped_summary[report_file.name] = "Falló el análisis de nombres"
        
        st.session_state.processed_files_this_session.add(report_file.name)

    if files_processed_summary:
        st.markdown("### ✅ Archivos Procesados Exitosamente")

        for date_obj, filenames in files_processed_summary.items():
            attendee_count = len(st.session_state.current_batch_data_by_date.get(date_obj, set()))
            
            with st.expander(f"{date_obj.strftime('%Y-%m-%d')} — {len(filenames)} archivo(s), {attendee_count} asistentes únicos"):
                col1, col2 = st.columns([1, 3])
                col1.markdown("**Archivos:**")
                for filename in filenames:
                    col2.write(f"📄 {filename}")
    # if files_processed_summary:
    #     st.markdown("**Archivos Procesados Exitosamente:**")
    #     for date_obj, filenames in files_processed_summary.items():
    #         attendee_count = len(st.session_state.current_batch_data_by_date.get(date_obj, set()))
    #         st.write(f"- **{date_obj.strftime('%Y-%m-%d')}**: {len(filenames)} archivo(s) procesado(s), contribuyendo a {attendee_count} asistentes únicos para esta fecha.")
    
    if files_skipped_summary:
        st.markdown("**Archivos Omitidos:**")
        for filename, reason in files_skipped_summary.items():
            st.write(f"- {filename}: {reason}")

if not st.session_state.current_batch_data_by_date and not uploaded_reports:
    st.info("Suba archivos de informe de asistencia para comenzar.")
elif not st.session_state.current_batch_data_by_date and uploaded_reports:
    st.info("No se procesaron datos de asistencia de los archivos subidos. Verifique los archivos e inténtelo de nuevo.")

if st.session_state.current_batch_data_by_date:
    st.divider()
    st.subheader("Paso 2: Preparar Tablas de Asistencia")
    if st.button("Preparar Tablas de Asistencia para Edición"):
        students_df, _ = load_students()
        if students_df is None or students_df.empty:
            st.error("No se encontraron datos de estudiantes. Por favor, suba una lista de estudiantes en la página 'Gestión de Estudiantes' primero.")
            st.stop()
        
        student_names_master_list = students_df['nombre'].astype(str).str.strip().tolist()

        for date_obj, names_from_reports_set in st.session_state.current_batch_data_by_date.items():
            normalized_names_from_reports = {name.lower().strip() for name in names_from_reports_set}
            
            attendance_records = []
            for master_name in student_names_master_list:
                normalized_master_name = master_name.lower().strip()
                present = normalized_master_name in normalized_names_from_reports
                attendance_records.append({'Nombre': master_name, 'Presente': present})
            
            if attendance_records:
                attendance_df = pd.DataFrame(attendance_records)
                st.session_state.prepared_attendance_dfs[date_obj] = attendance_df
            else:
                st.info(f"No se generaron registros de asistencia para {date_obj.strftime('%Y-%m-%d')} porque la lista de estudiantes está vacía o no hubo coincidencias.")
        
        if st.session_state.prepared_attendance_dfs:
            st.success("Tablas de asistencia preparadas. Proceda al Paso 3.")
            st.rerun()
        else:
            st.warning("No se pudieron preparar tablas de asistencia. Verifique los datos de los estudiantes y los archivos de reporte.")

if st.session_state.prepared_attendance_dfs:
    st.divider()
    st.subheader("Paso 3: Revisar y Guardar Asistencia")
    st.caption("Revise los registros de asistencia abajo. Marque la casilla 'Presente' para los estudiantes que asistieron. Desmarque para los ausentes.")

    if not st.session_state.prepared_attendance_dfs:
        st.warning("No hay datos de asistencia preparados para guardar. Vaya al Paso 2 para preparar las tablas de asistencia.")
    else:
        dates_with_data = sorted(st.session_state.prepared_attendance_dfs.keys())

        if not dates_with_data:
            st.info("No hay datos de asistencia preparados para mostrar.")
        else:
            selected_date_str = st.selectbox(
                "Seleccione una fecha para ver/editar asistencia:",
                options=[d.strftime('%Y-%m-%d') for d in dates_with_data],
                index=0
            )
            selected_date_obj = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()

            if selected_date_obj in st.session_state.prepared_attendance_dfs:
                df_to_edit = st.session_state.prepared_attendance_dfs[selected_date_obj]
                total_attended = df_to_edit['Presente'].value_counts().get(True, 0)
                st.markdown(f"#### Asistencia para: {selected_date_obj.strftime('%A, %d de %B de %Y')} ({total_attended} de {len(df_to_edit)})")
                edited_df = st.data_editor(
                    df_to_edit,
                    column_config={
                        "Nombre": st.column_config.TextColumn("Nombre del Estudiante", disabled=True, width="large"),
                        "Presente": st.column_config.CheckboxColumn("¿Presente?", default=False, width="small")
                    },
                    hide_index=True,
                    key=f"attendance_editor_{selected_date_str}"
                )
                st.session_state.prepared_attendance_dfs[selected_date_obj] = edited_df  # Update with edits

                col1, col2, _ = st.columns([2, 3, 2])
                with col1:
                    if st.button(f"💾 Guardar {selected_date_str}", key=f"save_{selected_date_str}"):
                        attendance_data_to_save = edited_df.to_dict('records')
                        if save_attendance(selected_date_obj, attendance_data_to_save):
                            st.success(f"¡Asistencia guardada exitosamente para {selected_date_str}!")
                            st.rerun()
                        else:
                            st.error(f"Error al guardar asistencia para {selected_date_str}.")
                with col2:
                    if st.button("🗑️ Limpiar Datos Cargados"):
                        st.session_state.current_batch_data_by_date = {}
                        st.session_state.prepared_attendance_dfs = {}
                        st.session_state.processed_files_this_session = set()
                        st.rerun()
                
                # Add Save All button at the top
                if st.button("💾 Guardar Todos los Reportes", type="primary", key="save_all_reports"):
                    save_success = True
                    saved_count = 0
                    
                    for date_obj, df in st.session_state.prepared_attendance_dfs.items():
                        date_str = date_obj.strftime('%Y-%m-%d')
                        attendance_data = df.to_dict('records')
                        if save_attendance(date_obj, attendance_data):
                            saved_count += 1
                        else:
                            save_success = False
                            st.error(f"Error al guardar la asistencia para {date_str}.")
                    
                    if save_success and saved_count > 0:
                        st.toast("¡Informes guardados exitosamente!", icon="✅")
                        st.success(f"¡Se guardaron exitosamente {saved_count} reporte(s) de asistencia!")
                        st.balloons()
                        # Add delay to ensure toast is visible before rerun
                        time.sleep(3)  # 3 seconds delay
                        st.rerun()
                    elif saved_count == 0:
                        st.warning("No se pudo guardar ningún reporte. Por favor intente de nuevo.")
                
                st.markdown("---")
            else:
                st.warning("La fecha seleccionada ya no tiene datos preparados. Por favor, recargue o seleccione otra fecha.")