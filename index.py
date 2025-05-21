import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime, timedelta
import io
from copy import deepcopy

CARPETA_ONEDRIVE = r"C:\Users\JulioRodriguez\OneDrive - InterAmerican Technical Institute\Attendance"
ARCHIVO_RESIDENTES = "residentes.csv"

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

def cargar_lista_residentes():
    path_residentes = os.path.join(CARPETA_ONEDRIVE, ARCHIVO_RESIDENTES)
    return pd.read_csv(path_residentes)

def buscar_archivos_asistencia(fecha_str, tipo="Tarde"):
    # Construct pattern that matches any prefix followed by the consistent parts
    patron = f"*{tipo} - Attendance report {fecha_str}.csv"
    ruta = os.path.join(CARPETA_ONEDRIVE, patron)
    archivos = glob.glob(ruta)
    
    # Add debug logging
    # st.write(f"Searching for pattern: {patron}")
    # st.write(f"Found files: {archivos}")
    
    return archivos

def extraer_participantes(archivo):
    try:
        # Read the file line by line to handle TSV format
        with open(archivo, 'r', encoding='utf-16') as f:
            lines = f.readlines()
        
        # Find the start of the participants section
        start_idx = next(i for i, line in enumerate(lines)
                         if line.strip().startswith("Name\tFirst Join"))
        
        # Find the end of the participants section (line with "3. In-Meeting Activities")
        end_idx = next(i for i, line in enumerate(lines[start_idx:], start_idx)
                      if "3. In-Meeting Activities" in line.strip())
        
        # Get the participants section (including the header line)
        data_lines = lines[start_idx:end_idx]  # Get all lines from start to end_idx (exclusive)
        
        # Create DataFrame from the specific lines
        df = pd.read_csv(io.StringIO("".join(data_lines)), sep="\t")
        
        # Debug logging
        # st.write(f"\nReading file: {archivo}")
        # st.write(f"Raw data: {df}")
        
        # Filter out organizers and get unique names
        df_filtered = df[df['Role'] != 'Organizer']
        participantes = df_filtered["Name"].dropna().unique()
        # st.write(f"Filtered participants: {participantes}")
        
        return participantes
    except Exception as e:
        st.warning(f"No se pudo leer: {archivo}\nError: {e}")
        return []

def asistencia_dia(fecha):
    # If fecha is already a string, use it directly
    if isinstance(fecha, str):
        fecha_str = fecha
    else:
        # Format date as M-DD-YY
        fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}" 
    
    # First check for Mañana files
    archivos_manana = buscar_archivos_asistencia(fecha_str, "Mañana")
    nombres_manana = set()
    if archivos_manana:
        nombres_manana = set(extraer_participantes(archivos_manana[0]))
    
    # Then check for Tarde files
    archivos_tarde = buscar_archivos_asistencia(fecha_str, "Tarde")
    nombres_tarde = set()
    if archivos_tarde:
        nombres_tarde = set(extraer_participantes(archivos_tarde[0]))
    
    # Convert sets to lists for consistent ordering
    return list(nombres_manana), list(nombres_tarde)

def asistencia_semana(desde, hasta):
    dias = pd.date_range(desde, hasta) 
    asistencias = []
    for dia in dias:
        # Format date as M-DD-YY (single digit month)
        fecha_str = f"{dia.month}-{dia.day}-{dia.year % 100}"
        # st.write(f"Processing date: {fecha_str}")
        
        # Get attendance for this date
        asistencia_manana, asistencia_tarde = asistencia_dia(fecha_str)
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

# Format dates as M-DD-YY
fecha_inicio_str = f"{fecha_inicio.month}-{fecha_inicio.day}-{fecha_inicio.year % 100}"
fecha_fin_str = f"{fecha_fin.month}-{fecha_fin.day}-{fecha_fin.year % 100}"

# Get base attendance data
residentes = cargar_lista_residentes()

# Get attendance for the selected date range
asistencias_por_dia = asistencia_semana(fecha_inicio, fecha_fin)

# Create a copy of residentes to modify
residentes_editados = residentes.copy()

# Create a DataFrame to store daily attendance
attendance_data = []

# Get attendance for each date in the range
for fecha in pd.date_range(fecha_inicio, fecha_fin):
    fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}"
    asistentes_manana, asistentes_tarde = asistencia_dia(fecha_str)
    
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
