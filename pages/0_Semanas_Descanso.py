import streamlit as st
import pandas as pd
import datetime
# Assuming 'config' module has 'setup_page' and 'db' (Firebase instance)
from config import setup_page, db 

# --- Page Setup and Login Check ---
setup_page("Semanas de Descanso")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

# --- Database Operations ---

def load_breaks():
    """
    Loads all 'breaks' data from the Firebase Realtime Database.
    Handles cases where data is empty or not in expected dictionary format.
    """
    try:
        # Create a fresh reference to the 'breaks' child node
        breaks_ref = db.child("breaks")
        breaks_data = breaks_ref.get().val() or {} # Get data, default to empty dict if None
        
        # Ensure the retrieved data is a dictionary
        if not isinstance(breaks_data, dict):
            st.warning(f"Se esperaba un diccionario para 'breaks', pero se obtuvo: {type(breaks_data)}. Retornando diccionario vacío.")
            return {}
        return breaks_data
    except Exception as e:
        st.error(f"Error al cargar las semanas de descanso: {e}")
        return {}

def save_break(break_id, break_data):
    """
    Saves a single break record to the Firebase Realtime Database.
    'break_id' is the unique key, 'break_data' is a dictionary of the break's attributes.
    """
    try:
        # Create a fresh reference to the specific break using its ID
        break_ref = db.child("breaks").child(break_id)
        break_ref.set(break_data) # Set (create or overwrite) the data
        return True
    except Exception as e:
        st.error(f"Error al guardar la semana de descanso: {e}")
        return False

def delete_break(break_id):
    """
    Deletes a specific break record from the Firebase Realtime Database.
    'break_id' is the unique key of the break to be deleted.
    """
    try:
        # Create a fresh reference to the specific break to be removed
        break_ref = db.child("breaks").child(break_id)
        
        # Verify the break exists before attempting to remove it
        if break_ref.get().val() is not None:
            break_ref.remove() # Remove the data
            return True
        else:
            st.warning(f"La semana de descanso con ID '{break_id}' no se encontró.")
            return False
    except Exception as e:
        st.error(f"Error al eliminar la semana de descanso: {e}")
        return False

# --- UI Components ---

def display_breaks_table(breaks_data):
    """
    Displays the loaded breaks data in a Streamlit dataframe.
    Calculates the 'Fecha Fin' dynamically for display.
    """
    if not breaks_data:
        st.info("No hay semanas de descanso configuradas.")
        return
    
    breaks_list = []
    for break_id, break_info in breaks_data.items():
        if isinstance(break_info, dict):
            start_date_str = break_info.get('start_date')
            start_date = None
            try:
                # Attempt to parse start_date from ISO format string
                if start_date_str:
                    start_date = datetime.datetime.fromisoformat(start_date_str).date()
            except ValueError:
                st.warning(f"Formato de fecha inválido para el ID '{break_id}': '{start_date_str}'. Se ignorará esta entrada o se mostrará como 'N/A'.")
                # start_date remains None, handled below
            
            duration_weeks = break_info.get('duration_weeks', 1)
            
            # Calculate end_date only if start_date was successfully parsed
            end_date = (start_date + datetime.timedelta(weeks=duration_weeks)) if start_date else None
            
            breaks_list.append({
                'ID': break_id,
                'Nombre': break_info.get('name', ''),
                'Fecha Inicio': start_date.strftime('%Y-%m-%d') if start_date else 'N/A',
                'Duración (semanas)': duration_weeks,
                'Fecha Fin': end_date.strftime('%Y-%m-%d') if end_date else 'N/A',
                'Descripción': break_info.get('description', '')
            })
    
    if not breaks_list:
        st.info("No hay semanas de descanso configuradas.")
        return
    
    df = pd.DataFrame(breaks_list)
    st.dataframe(
        df,
        column_config={
            'ID': None,  # Hide the internal ID column
            'Nombre': 'Nombre',
            'Fecha Inicio': 'Inicio',
            'Duración (semanas)': 'Semanas',
            'Fecha Fin': 'Fin',
            'Descripción': 'Descripción'
        },
        hide_index=True,  # Hide pandas DataFrame index
        use_container_width=True, # Make dataframe occupy full width
        column_order=['Nombre', 'Fecha Inicio', 'Duración (semanas)', 'Fecha Fin', 'Descripción']
    )

def add_break_form():
    """
    Displays a form to add a new break.
    The 'Período' caption updates reactively with user input.
    """
    # Initialize default values for the form fields for consistent behavior on first load
    # or after a form submission (if clear_on_submit is True)
    default_name = ''
    default_description = ''
    default_start_date = datetime.date.today()
    default_duration_weeks = 1

    # Use unique keys for each widget to ensure Streamlit manages their state correctly.
    # The 'value' parameter can directly use the widget's current return if we want
    # reactive updates. However, for initial values or to reset after submission,
    # it's better to store them in session_state and update them when needed.

    # Initialize session state for form fields if they don't exist
    if 'add_break_name' not in st.session_state:
        st.session_state.add_break_name = default_name
    if 'add_break_description' not in st.session_state:
        st.session_state.add_break_description = default_description
    if 'add_break_start_date' not in st.session_state:
        st.session_state.add_break_start_date = default_start_date
    if 'add_break_duration_weeks' not in st.session_state:
        st.session_state.add_break_duration_weeks = default_duration_weeks

    # Use a unique key for the form itself and set clear_on_submit to True
    # This automatically clears the form fields after successful submission.
    with st.form("add_break_form_key", clear_on_submit=True):
        st.subheader("Agregar Semana de Descanso")
        
        col1, col2 = st.columns(2)
        
        # Text input for the break name
        # The on_change callback will update session_state, making it reactive
        name = col1.text_input(
            "Nombre de la Semana de Descanso",
            value=st.session_state.add_break_name,
            key="break_name_input",
            on_change=lambda: setattr(st.session_state, 'add_break_name', st.session_state.break_name_input)
        )
        
        # Text area for the description
        description = col2.text_area(
            "Descripción (opcional)",
            value=st.session_state.add_break_description,
            key="break_description_input",
            on_change=lambda: setattr(st.session_state, 'add_break_description', st.session_state.break_description_input)
        )
        
        col1, col2 = st.columns(2)
        
        # Date input for the start date
        start_date = col1.date_input(
            "Fecha de Inicio",
            value=st.session_state.add_break_start_date,
            key="break_start_date_input",
            on_change=lambda: setattr(st.session_state, 'add_break_start_date', st.session_state.break_start_date_input)
        )
        
        # Number input for duration in weeks
        duration_weeks = col2.number_input(
            "Duración (semanas)",
            min_value=1,
            value=st.session_state.add_break_duration_weeks,
            step=1,
            key="break_duration_input",
            on_change=lambda: setattr(st.session_state, 'add_break_duration_weeks', st.session_state.break_duration_input)
        )
        
        # Calculate and display the date range dynamically.
        # This caption will update immediately because start_date and duration_weeks
        # directly reflect the current widget values on each re-run.
        end_date_display = start_date + datetime.timedelta(weeks=duration_weeks)
        st.caption(f"Período: {start_date.strftime('%Y-%m-%d')} al {end_date_display.strftime('%Y-%m-%d')}")
        
        # Form submit button
        submitted = st.form_submit_button("Guardar Semana de Descanso")
        
        if submitted:
            if not name:
                st.error("El nombre es obligatorio.")
                return None # Stop processing if name is missing
            
            # Reset session state variables after successful submission
            st.session_state.add_break_name = default_name
            st.session_state.add_break_description = default_description
            st.session_state.add_break_start_date = default_start_date
            st.session_state.add_break_duration_weeks = default_duration_weeks

            # Return the data to be saved
            return {
                'name': name,
                'description': description,
                'start_date': start_date.isoformat(), # Convert date object to ISO format string
                'duration_weeks': duration_weeks,
                'created_at': datetime.datetime.now().isoformat(), # Record creation timestamp
                'created_by': st.session_state.get('email', 'system') # Record creator's email
            }
    
    return None # Return None if the form has not been submitted

# --- Main App ---

def main():
    """
    Main function to run the Streamlit application for managing break weeks.
    Displays existing breaks, provides a form to add new ones, and a section to delete them.
    """
    
    st.markdown("""
    Administre las semanas de descanso que se aplicarán a todos los módulos.
    Estas fechas se utilizarán para saltar días no hábiles en los cálculos de programación.
    """)
    
    # Load existing breaks data from the database
    breaks_data = load_breaks()
    
    # Display the table of configured break weeks
    st.subheader("Semanas de Descanso Configuradas")
    display_breaks_table(breaks_data)
    
    # Section to add a new break, wrapped in an expander
    with st.expander("Agregar Nueva Semana de Descanso", expanded=False):
        break_data = add_break_form() # Call the form function to get submitted data
        if break_data:
            # Generate a unique ID for the new break based on current timestamp
            break_id = f"break_{datetime.datetime.now().strftime('%Y%m%d%H%M%S_%f')}" # Added microsecond for more uniqueness
            if save_break(break_id, break_data):
                st.success("¡Semana de descanso guardada exitosamente!")
                st.rerun() # Re-run the app to update the displayed table
            else:
                st.error("Error al guardar la semana de descanso.")
    
    # Section to delete existing breaks, only displayed if there are breaks to delete
    if breaks_data:
        st.subheader("Eliminar Semanas de Descanso")
        
        # Prepare options for the selectbox, calculating end_date for display
        break_options = {}
        for k, v in breaks_data.items():
            start_date_str = v.get('start_date')
            start_date_obj = None
            try:
                if start_date_str:
                    start_date_obj = datetime.datetime.fromisoformat(start_date_str).date()
            except ValueError:
                pass # start_date_obj remains None if parsing fails

            duration_weeks = v.get('duration_weeks', 1)
            # Calculate end_date string for display in the selectbox
            end_date_str = (start_date_obj + datetime.timedelta(weeks=duration_weeks)).strftime('%Y-%m-%d') if start_date_obj else 'N/A'
            
            break_name = v.get('name', 'Sin nombre')
            # Create a user-friendly string for the selectbox option
            break_options[f"{break_name} ({v.get('start_date', 'N/A')} - {end_date_str})"] = k
        
        if break_options:
            # Selectbox to choose a break to delete
            break_to_delete_display = st.selectbox(
                "Seleccione una semana de descanso para eliminar:",
                options=list(break_options.keys()),
                key="delete_break_select"
            )
            
            # Button to trigger deletion
            if st.button("Eliminar Semana de Descanso", type="primary"):
                # Get the actual break_id from the selected display string
                break_id_to_delete = break_options[break_to_delete_display]
                if delete_break(break_id_to_delete):
                    st.success("¡Semana de descanso eliminada exitosamente!")
                    st.rerun() # Re-run to update the table and selectbox
                else:
                    st.error("Error al eliminar la semana de descanso.")
        else:
            st.info("No hay semanas de descanso para eliminar.")

# Entry point of the Streamlit application
if __name__ == "__main__":
    main()
