import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime, timedelta
import io
from copy import deepcopy
from typing import List, Tuple, Optional, Dict, Any, Union
import tempfile
import uuid
import json

# Initialize session state for resident data
if 'residentes_df' not in st.session_state:
    st.session_state.residentes_df = pd.DataFrame()
    st.session_state.residentes_filename = None

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
    """Carga la lista de residentes desde el archivo subido o desde la sesión"""
    if uploaded_file is not None:
        try:
            # Read the file
            df = pd.read_csv(uploaded_file)
            # Update session state
            st.session_state.residentes_df = df
            st.session_state.residentes_filename = uploaded_file.name
            return df
        except Exception as e:
            st.error(f"Error al cargar el archivo de residentes: {str(e)}")
            return pd.DataFrame()
    
    # Return from session state if available
    if not st.session_state.residentes_df.empty:
        return st.session_state.residentes_df
    
    return pd.DataFrame()

def obtener_nombre_archivo_residentes() -> str:
    """Obtiene el nombre del archivo de residentes guardado"""
    return st.session_state.get('residentes_filename', "No se ha cargado ningún archivo")

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

def initialize_attendance_for_date(fecha, residentes_df, uploaded_files=None):
    """Initialize attendance state for a specific date if not exists"""
    fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}"
    attendance_key = f"attendance_{fecha_str}"
    
    if attendance_key not in st.session_state:
        # Get automatic attendance from files
        asistentes_manana_auto, asistentes_tarde_auto = asistencia_dia(fecha, uploaded_files)
        
        # Initialize with automatic attendance
        st.session_state[attendance_key] = {}
        
        # Ensure we have residentes data
        if not residentes_df.empty:
            for _, row in residentes_df.iterrows():
                nombre = row["nombre"]
                st.session_state[attendance_key][nombre] = {
                    'mañana': nombre in asistentes_manana_auto,
                    'tarde': nombre in asistentes_tarde_auto
                }
    
    return attendance_key

# --- UI ---
st.title("📋 Seguimiento de Asistencia - Curso de CBA")

# Initialize only if not exists
if 'rango_fechas' not in st.session_state:
    st.session_state.rango_fechas = True

# Get date range input
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha de inicio")

# Only show end date if range is enabled
if st.session_state.rango_fechas:
    with col2:
        fecha_fin = st.date_input("Fecha de fin")
else:
    fecha_fin = fecha_inicio  # Use start date as end date

# Date range checkbox - use session state key directly
st.checkbox(
    "Rango de fechas",
    value=st.session_state.rango_fechas,
    key='rango_fechas',  # This directly updates st.session_state.rango_fechas
    help="Marcar para seleccionar un rango de fechas, desmarcar para una sola fecha"
)

# Checkbox for weekend filtering
skip_weekends = st.checkbox(
    "Omitir fines de semana", 
    value=True,
    help="Si está marcado, no se incluirán sábados ni domingos",
    key="skip_weekends"
)

# File uploaders
st.sidebar.header("📤 Cargar Archivos")

# Show current resident file info if exists
current_resident_file = obtener_nombre_archivo_residentes()
if current_resident_file != "No se ha cargado ningún archivo":
    st.sidebar.success(f"✅ Archivo cargado: {current_resident_file}")
    if st.sidebar.button("🗑️ Limpiar archivo de residentes"):
        st.session_state.residentes_df = pd.DataFrame()
        st.session_state.residentes_filename = None
        st.rerun()

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

# Load resident data
residentes = cargar_lista_residentes(uploaded_residentes)

# Show warning if no resident data is available
if residentes.empty:
    st.warning("Por favor, sube el archivo con la lista de residentes")
    st.stop()

# Store in session for faster access
st.session_state.residentes_df = residentes

# Get attendance for the selected date range
asistencias_por_dia = asistencia_semana(fecha_inicio, fecha_fin, uploaded_files, st.session_state.skip_weekends)

# Create a DataFrame to store daily attendance
attendance_data = []

# Get attendance for each date in the range
for i, fecha in enumerate(pd.date_range(fecha_inicio, fecha_fin)):
    # Skip weekends if the checkbox is checked
    if st.session_state.skip_weekends and fecha.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        continue
        
    fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}"
    
    # Get attendance from the pre-calculated data
    if i < len(asistencias_por_dia):
        asistentes_manana, asistentes_tarde = asistencias_por_dia[i]
        total_manana = len(asistentes_manana)
        total_tarde = len(asistentes_tarde)
    else:
        total_manana = 0
        total_tarde = 0
    
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
    # Add a metric for total attendance only for single dates
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Mañana", f"{attendance_df['Mañana'].sum()}")
        with col2:
            st.metric("Total Tarde", f"{attendance_df['Tarde'].sum()}")

# Display the attendance table without index
st.dataframe(attendance_df, hide_index=True)

# ATTENDANCE EDITOR - Only for the last date in range
fecha_actual_str = f"{fecha_fin.month}-{fecha_fin.day}-{fecha_fin.year % 100}"
fecha_actual_slash = format_date(fecha_fin, '/')

# Initialize attendance state for this date
attendance_key = initialize_attendance_for_date(fecha_fin, residentes, uploaded_files)

# Create DataFrame for the editor using session state - FIXED VERSION
editor_data = []
if attendance_key in st.session_state and st.session_state[attendance_key]:
    for nombre in st.session_state[attendance_key]:
        editor_data.append({
            'nombre': nombre,
            'mañana': st.session_state[attendance_key][nombre]['mañana'],
            'tarde': st.session_state[attendance_key][nombre]['tarde']
        })
else:
    # Fallback: create editor data from residentes if attendance state is empty
    for _, row in residentes.iterrows():
        nombre = row["nombre"]
        editor_data.append({
            'nombre': nombre,
            'mañana': False,
            'tarde': False
        })

editor_df = pd.DataFrame(editor_data)

# Display the editor
with st.container():
    st.subheader(f"✏️ Asistencia para {fecha_actual_slash}")
    
    # Only show editor if we have data
    if not editor_df.empty:
        # Use a unique key that includes date to avoid conflicts
        editor_key = f"editor_{fecha_actual_str}_{hash(str(fecha_fin))}"
        
        edited_df = st.data_editor(
            editor_df,
            column_config={
                "nombre": st.column_config.TextColumn("Nombre", disabled=True),
                "mañana": st.column_config.CheckboxColumn("Mañana"),
                "tarde": st.column_config.CheckboxColumn("Tarde")
            },
            disabled=["nombre"],
            hide_index=True,
            key=editor_key,
            use_container_width=True
        )
        
        # Update session state with changes - FIXED VERSION
        if edited_df is not None and not edited_df.empty:
            # Ensure attendance_key exists in session state
            if attendance_key not in st.session_state:
                st.session_state[attendance_key] = {}
            
            # Update each row
            for _, row in edited_df.iterrows():
                nombre = row["nombre"]
                st.session_state[attendance_key][nombre] = {
                    'mañana': bool(row['mañana']),
                    'tarde': bool(row['tarde'])
                }
    else:
        st.warning("No hay datos de estudiantes para mostrar. Verifica que el archivo de residentes esté cargado correctamente.")

# Calculate who attended during the entire range (including manual edits)
asistencia_total = set()

# Add from file-based attendance
for asistencia_manana, asistencia_tarde in asistencias_por_dia:
    asistencia_total.update(asistencia_manana)
    asistencia_total.update(asistencia_tarde)

# Add from manual attendance for the current date being edited
if attendance_key in st.session_state and st.session_state[attendance_key]:
    for nombre in st.session_state[attendance_key]:
        if (st.session_state[attendance_key][nombre]['mañana'] or 
            st.session_state[attendance_key][nombre]['tarde']):
            asistencia_total.add(nombre)

# Create the final attendance status
residentes_con_asistencia = residentes.copy()
residentes_con_asistencia["asistio_semana"] = residentes_con_asistencia["nombre"].isin(asistencia_total)

# Show absent students report
st.subheader("📉 Estudiantes sin asistencia este rango de fecha")

# Get the list of absent students
ausentes = residentes_con_asistencia[~residentes_con_asistencia["asistio_semana"]][["nombre"]]

# Calculate total absent students
num_ausentes = len(ausentes)

# Display total absent students in a metric
col1 = st.columns(1)[0]
with col1:
    st.metric("Total ausentes", f"{num_ausentes}")

# Show the list of absent students
st.dataframe(ausentes, hide_index=True)

# Download Excel with absent students
if st.button("📥 Descargar reporte de ausentes"):
    output = "ausentes_semana.xlsx"
    ausentes.to_excel(output, index=False)
    with open(output, "rb") as f:
        st.download_button("Descargar Excel", f, output)