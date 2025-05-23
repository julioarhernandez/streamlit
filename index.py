import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime, timedelta
import io
from copy import deepcopy
from typing import List, Tuple, Optional, Dict, Any
import tempfile
import uuid

def format_date(fecha, separator='-'):
    """
    Format a date object as 'MM-DD-YY' or 'MM/DD/YY'.
    
    Args:
        fecha: datetime.date object
        separator: Either '-' or '/' to separate date components
        
    Returns:
        str: Formatted date string
    """
    if separator not in ('-', '/'):
        raise ValueError("Separator must be either '-' or '/'")
    return f"{fecha.month}{separator}{fecha.day}{separator}{fecha.year % 100}"

def cargar_lista_residentes(uploaded_file=None) -> pd.DataFrame:
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    return pd.DataFrame()

def procesar_archivo_asistencia(uploaded_file) -> List[str]:
    """Process an uploaded attendance file and return list of participants."""
    try:
        # Read the file content as string
        content = uploaded_file.getvalue().decode('utf-16')
        lines = content.split('\n')
        
        # Find the start and end of the participants section
        start_idx = next((i for i, line in enumerate(lines) 
                         if line.strip().startswith("Name\tFirst Join")), None)
        
        if start_idx is None:
            st.warning("Formato de archivo no reconocido. No se encontró el encabezado de participantes.")
            return []
            
        end_idx = next((i for i, line in enumerate(lines[start_idx:], start_idx)
                      if "3. In-Meeting Activities" in line.strip()), len(lines))
        
        # Get the participants section
        data_lines = lines[start_idx:end_idx]
        
        # Create DataFrame from the specific lines
        df = pd.read_csv(io.StringIO("\n".join(data_lines)), sep="\t")
        
        # Filter out organizers and get unique names
        df_filtered = df[df['Role'] != 'Organizer']
        participantes = df_filtered["Name"].dropna().unique().tolist()
        
        return participantes
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        return []

# This function is replaced by procesar_archivo_asistencia

def asistencia_dia(fecha, uploaded_files=None):
    """Process attendance for a specific date using uploaded files.
    
    Args:
        fecha: Date as datetime or string
        uploaded_files: List of uploaded files
        
    Returns:
        Tuple of (nombres_manana, nombres_tarde) - lists of names
    """
    nombres_manana = set()
    nombres_tarde = set()
    
    if uploaded_files:
        # Convert date to multiple possible string formats for matching
        if not isinstance(fecha, str):
            # Try multiple date formats that might be in filenames
            date_formats = [
                f"{fecha.month}-{fecha.day}-{fecha.year % 100}",  # M-D-YY
                f"{fecha.month:02d}-{fecha.day:02d}-{fecha.year % 100:02d}",  # MM-DD-YY
                f"{fecha.month}/{fecha.day}/{fecha.year % 100}",  # M/D/YY
                f"{fecha.month:02d}/{fecha.day:02d}/{fecha.year % 100:02d}",  # MM/DD/YY
                f"{fecha.year}-{fecha.month:02d}-{fecha.day:02d}"  # YYYY-MM-DD
            ]
        else:
            date_formats = [fecha]
        
        for file in uploaded_files:
            file_name = file.name
            
            # Check if this file is for any of the date formats and session
            for date_fmt in date_formats:
                if str(date_fmt) in file_name:
                    try:
                        if "mañana" in file_name.lower():
                            nombres_manana.update(procesar_archivo_asistencia(file))
                        elif "tarde" in file_name.lower():
                            nombres_tarde.update(procesar_archivo_asistencia(file))
                        break  # Found a matching date format, no need to check others
                    except Exception as e:
                        st.warning(f"Error procesando archivo {file_name}: {str(e)}")
                        break
    
    return list(nombres_manana), list(nombres_tarde)

def asistencia_semana(desde, hasta, uploaded_files=None, skip_weekends=True):
    dias = pd.date_range(desde, hasta)
    if skip_weekends:
        dias = [d for d in dias if d.weekday() < 5]  # Only keep weekdays (0-4 = Monday-Friday)
    
    asistencias = []
    for dia in dias:
        asistencia_manana, asistencia_tarde = asistencia_dia(dia, uploaded_files)
        asistencias.append((asistencia_manana, asistencia_tarde))
    
    return asistencias

# --- UI ---
st.title("📋 Seguimiento de Asistencia - Curso de CBA")

# Initialize session state for manual attendance changes if not exists
if 'manual_attendance' not in st.session_state:
    st.session_state.manual_attendance = {}

# Get date range input
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha de inicio")
with col2:
    fecha_fin = st.date_input("Fecha de fin")

# Checkbox for weekend filtering
skip_weekends = st.checkbox(
    "Omitir fines de semana", 
    value=True,
    help="Si está marcado, no se incluirán sábados ni domingos",
    key="skip_weekends"
)

# Format dates as M-DD-YY
fecha_inicio_str = f"{fecha_inicio.month}-{fecha_inicio.day}-{fecha_inicio.year % 100}"
fecha_fin_str = f"{fecha_fin.month}-{fecha_fin.day}-{fecha_fin.year % 100}"

# File uploaders
st.sidebar.header("📤 Cargar Archivos")

# Upload resident list
uploaded_residentes = st.sidebar.file_uploader(
    "📝 Lista de residentes (CSV)",
    type=["csv"],
    help="Sube el archivo CSV con la lista de residentes"
)

# Upload attendance files
uploaded_files = st.sidebar.file_uploader(
    "📊 Archivos de asistencia",
    type=["csv"],
    accept_multiple_files=True,
    help="Sube los archivos de asistencia exportados de Zoom"
)

if not uploaded_residentes:
    st.warning("Por favor, sube el archivo con la lista de residentes")
    st.stop()

# Load resident data
residentes = cargar_lista_residentes(uploaded_residentes)

# Get attendance for the selected date range
asistencias_por_dia = asistencia_semana(fecha_inicio, fecha_fin, uploaded_files)

# Create a copy of residentes to modify
residentes_editados = residentes.copy()

# Create a DataFrame to store daily attendance
attendance_data = []

# Get attendance for each date in the range
for fecha in pd.date_range(fecha_inicio, fecha_fin):
    # Skip weekends if the checkbox is checked
    if st.session_state.skip_weekends and fecha.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        continue
        
    fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}"
    # Use the uploaded files for attendance processing
    asistentes_manana, asistentes_tarde = asistencia_dia(fecha, uploaded_files)
    
    # Get manual attendance for this date
    if fecha_str not in st.session_state.manual_attendance:
        st.session_state.manual_attendance[fecha_str] = {
            'mañana': set(),
            'tarde': set()
        }
    
    # Apply file-based attendance
    residentes_editados[f"mañana_{fecha_str}"] = residentes_editados["nombre"].isin(asistentes_manana)
    residentes_editados[f"tarde_{fecha_str}"] = residentes_editados["nombre"].isin(asistentes_tarde)
    
    # Apply manual attendance
    residentes_editados[f"mañana_{fecha_str}"] = residentes_editados[f"mañana_{fecha_str}"] | residentes_editados["nombre"].isin(st.session_state.manual_attendance[fecha_str]['mañana'])
    residentes_editados[f"tarde_{fecha_str}"] = residentes_editados[f"tarde_{fecha_str}"] | residentes_editados["nombre"].isin(st.session_state.manual_attendance[fecha_str]['tarde'])
    
    # Get attendance totals for this date
    total_manana = len(residentes_editados[residentes_editados[f"mañana_{fecha_str}"]])
    total_tarde = len(residentes_editados[residentes_editados[f"tarde_{fecha_str}"]])
    
    # Add to attendance data
    attendance_data.append({
        'Día': fecha.strftime('%A'),  # Get day name (e.g., 'Monday', 'Tuesday', etc.)
        'Fecha': fecha_str,
        'Mañana': total_manana,
        'Tarde': total_tarde
    })

# Create a DataFrame for the attendance table
attendance_df = pd.DataFrame(attendance_data)

# Display the attendance table
st.subheader("📊 Reporte diario de asistencia")

if fecha_inicio == fecha_fin:
    # Add a metric for total attendance only for date ranges
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Mañana", f"{attendance_df['Mañana'].sum()}")
        with col2:
            st.metric("Total Tarde", f"{attendance_df['Tarde'].sum()}")

# Display the attendance table without index
st.dataframe(attendance_df, hide_index=True)

# Show checkboxes for the last date in the range to allow manual changes
fecha_actual_str = f"{fecha_fin.month}-{fecha_fin.day}-{fecha_fin.year % 100}"
fecha_actual_slash = format_date(fecha_fin, '/')


# Display the data editor in a container with a title
with st.container():
    st.subheader(f"✏️ Asistencia para {fecha_actual_slash}")
    residentes_editados = st.data_editor(
        residentes_editados[["nombre", f"mañana_{fecha_actual_str}", f"tarde_{fecha_actual_str}"]], 
        column_config={
            "nombre": "Nombre",
            f"mañana_{fecha_actual_str}": "Mañana",
            f"tarde_{fecha_actual_str}": "Tarde"
        },
        num_rows="dynamic"
    )

# Update session state with manual changes for the last date
manual_manana = set(residentes_editados[residentes_editados[f"mañana_{fecha_actual_str}"]]["nombre"])
manual_tarde = set(residentes_editados[residentes_editados[f"tarde_{fecha_actual_str}"]]["nombre"])
    
# Update session state with changes
st.session_state.manual_attendance[fecha_actual_str] = {
    'mañana': manual_manana,
    'tarde': manual_tarde
}

# Get attendance for the selected date range
asistencia_total = set()
for asistencia_manana, asistencia_tarde in asistencias_por_dia:
    asistencia_total.update(asistencia_manana)
    asistencia_total.update(asistencia_tarde)
    
# Update the "asistió_semana" column considering manual changes
residentes_editados["asistió_semana"] = residentes_editados["nombre"].isin(asistencia_total) | \
    residentes_editados["nombre"].isin(manual_manana) | \
    residentes_editados["nombre"].isin(manual_tarde)

# Update the "asistió_semana" column considering manual changes
residentes_editados["asistió_semana"] = residentes_editados["nombre"].isin(asistencia_total) | \
    residentes_editados["nombre"].isin(manual_manana) | \
    residentes_editados["nombre"].isin(manual_tarde)

# Mostrar reporte de ausentes semanales
st.subheader("📉 Estudiantes sin asistencia este rango de fecha")

# Get the list of absent students first
ausentes = residentes_editados[~residentes_editados["asistió_semana"]][["nombre"]]

# Calculate total absent students
num_ausentes = len(ausentes)

# Display total absent students in a metric
col1 = st.columns(1)[0]
with col1:
    st.metric("Total ausentes", f"{num_ausentes}")

# Show the list of absent students
st.dataframe(ausentes)

# Descargar Excel con ausentes
if st.button("📥 Descargar reporte de ausentes"):
    output = "ausentes_semana.xlsx"
    ausentes.to_excel(output, index=False)
    with open(output, "rb") as f:
        st.download_button("Descargar Excel", f, output)
