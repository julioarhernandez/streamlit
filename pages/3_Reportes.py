# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\pages\3_Reports.py
import streamlit as st
import pandas as pd
import datetime
from config import setup_page # Assuming db is implicitly used by load_attendance via utils
from utils import load_attendance, load_students # Use the centralized functions
from utils import format_date_for_display, create_filename_date_range, get_student_start_date, date_format, get_attendance_dates

# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()
# --- End Login Check ---

# Setup page
setup_page("Reportes de Asistencia") # Reverted call

# Manual Spanish day name mapping to avoid locale/encoding issues
SPANISH_DAY_NAMES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

# Main UI

# Date selectors for range
today = datetime.date.today()
# Default start date to the first day of the current month for a more common report view
default_start_date = today.replace(day=1) 

# Format date inputs with MM/DD/YYYY format
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Fecha de Inicio", 
        value=default_start_date,
        key="report_start_date",
        format="MM/DD/YYYY"
    )
with col2:
    end_date = st.date_input(
        "Fecha de Fin",
        value=today,
        key="report_end_date",
        format="MM/DD/YYYY"
    )


# Show available attendance dates
st.caption("Asistencia(s) guardada(s):")
try:
    # Get all attendance dates
    all_attendance = get_attendance_dates()
    
    if all_attendance:
        # Display dates in a grid
        all_badges = " ".join([f":gray-badge[:material/calendar_today: {datetime.datetime.strptime(date_str, '%Y-%m-%d').date().strftime('%m-%d-%Y')}] " for date_str in all_attendance])
        st.markdown(all_badges)
    else:
        st.caption("No hay fechas con asistencia registrada")
        
except Exception as e:
    st.error(f"Error al cargar fechas de asistencia: {str(e)}")

if start_date > end_date:
    st.error("Error: La fecha de inicio no puede ser posterior a la fecha de fin.") # Translated
else:
    if st.button("Generar Reporte", key="generate_report_btn", type="primary"): # Translated
        # 1. Load all students
        all_students_df, _ = load_students()
        if all_students_df is None or all_students_df.empty:
            st.error("No se pudo cargar la lista de estudiantes. Por favor, registre estudiantes en la página 'Estudiantes'.") # Translated
            st.stop()
        
        # Assuming student names are in 'nombre' column and are unique identifiers
        master_student_list = set(all_students_df['nombre'].astype(str).str.strip().unique())
        total_registered_students = len(master_student_list)

        # 2. Process attendance data for the date range
        daily_summary_data = []
        students_present_in_range = set() # This still considers all days for 'never attended'
        
        current_date_iter = start_date
        
        spinner_message = f"Cargando y procesando asistencia desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}..." # Translated
        with st.spinner(spinner_message):
            while current_date_iter <= end_date:
                # Exclude weekends (Saturday=5, Sunday=6 in weekday() method)
                if current_date_iter.weekday() >= 5: # 0=Monday, 1=Tuesday, ..., 5=Saturday, 6=Sunday
                    current_date_iter += datetime.timedelta(days=1)
                    continue # Skip to next day if it's a weekend
                    
                daily_attendance_dict = load_attendance(current_date_iter) # {name: {'status': 'Present', ...}}
                
                present_today_count = 0
                if daily_attendance_dict:
                    for student_name, details in daily_attendance_dict.items():
                        # Ensure names are consistently handled (e.g. case, stripping) if needed for matching
                        # For now, assume names from load_attendance match those in master_student_list
                        if details.get('Presente', False):
                            present_today_count += 1
                            # For 'never attended', we still need to know if they were present on any day, including potential weekends if data existed
                            # However, the daily summary table will exclude weekends.
                            # If the requirement is to also exclude weekend presence from 'never attended', this logic would need adjustment.
                            # For now, students_present_in_range includes all days where data is found.
                            students_present_in_range.add(student_name) # Or details.get('name', student_name)
                
                absent_today_count = total_registered_students - present_today_count
                english_day_name = current_date_iter.strftime('%A')
                spanish_day_name = SPANISH_DAY_NAMES.get(english_day_name, english_day_name) # Fallback to English if not found
                
                daily_summary_data.append({
                    'Fecha': date_format(current_date_iter, '%Y-%m-%d'), # Keep 'Fecha' or 'Date'
                    'Día': spanish_day_name.capitalize(), # Spanish Day Name, capitalized
                    '# Presentes': present_today_count, # Translated
                    '# Ausentes': absent_today_count    # Translated
                })
                current_date_iter += datetime.timedelta(days=1)
        
        # 3. Display Daily Summary Report
        if daily_summary_data:
            summary_header = f"Resumen Diario de Asistencia: {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}" # Translated
            st.subheader(summary_header)
            df_summary_display = pd.DataFrame(daily_summary_data)
            # Reorder columns for better display, including Day Name
            cols_order = ['Fecha', 'Día', '# Presentes', '# Ausentes'] # Updated column names
            df_summary_display = df_summary_display[cols_order]
            st.dataframe(df_summary_display, use_container_width=True, hide_index=True)
            
            csv_export = df_summary_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar Resumen", # Translated
                data=csv_export,
                file_name=f"resumen_asistencia_diaria_sin_fines_semana_{start_date.strftime('%Y%m%d')}_a_{end_date.strftime('%Y%m%d')}.csv", # Translated filename
                mime='text/csv',
                key='download_summary_csv_btn'
            )
        else:
            st.info("No se procesaron datos de asistencia para días laborables en el rango de fechas seleccionado.") # Translated

        # 4. Identify and Display Students Who Never Attended
        st.divider()
        st.subheader("Estudiantes que Nunca Asistieron en las fechas Seleccionadas") # Clarify this includes weekends if data existed
        students_never_attended_list = sorted(list(master_student_list - students_present_in_range))
        
        if students_never_attended_list:
            warning_msg = f"{len(students_never_attended_list)} estudiante(s) no tuvieron registros de 'Presente' en este período:"
            st.warning(warning_msg)
            
            # Get student data with start dates
            try:
                all_students_df, _ = load_students()
            except Exception as e:
                st.error(f"Error loading student data: {str(e)}")
                all_students_df = pd.DataFrame()
            
            # Create DataFrame for display with start dates
            never_attended_data = []
            for student_name in students_never_attended_list:
                start_date = get_student_start_date(all_students_df, student_name)
                never_attended_data.append({
                    'Nombre del Estudiante': student_name.strip(),
                    'Fecha de Inicio': start_date
                })
            
            # Display the dataframe
            df_never_attended = pd.DataFrame(never_attended_data)
            st.dataframe(df_never_attended, use_container_width=True, hide_index=True)
            
            # Create CSV download
            try:
                csv_never_attended = df_never_attended.to_csv(index=False, encoding='utf-8-sig')
                
                # Create filename with date range
                date_suffix = create_filename_date_range(start_date, end_date)
                filename = f"nunca_asistieron{date_suffix}.csv"
                
                st.download_button(
                    label="Descargar Lista de Estudiantes que Nunca Asistieron",
                    data=csv_never_attended,
                    file_name=filename,
                    mime='text/csv; charset=utf-8-sig',
                    key='download_never_attended_csv_btn'
                )
            except Exception as e:
                st.error(f"Error creating download file: {str(e)}")
                # Fallback download without date range
                try:
                    csv_never_attended = df_never_attended.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="Descargar Lista de Estudiantes que Nunca Asistieron",
                        data=csv_never_attended,
                        file_name="nunca_asistieron.csv",
                        mime='text/csv; charset=utf-8-sig',
                        key='download_never_attended_csv_btn_fallback'
                    )
                except Exception as fallback_e:
                    st.error(f"Error creating fallback download: {str(fallback_e)}")

        else:
            st.success("Todos los estudiantes registrados asistieron al menos una vez en el rango de fechas seleccionado (considerando todos los días).")
