import streamlit as st
import pandas as pd
from config import setup_page, db

# Setup page
setup_page("Modules Management")

def save_module(module_data):
    """Save module data to Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        module_id = module_data['module_id']
        db.child("modules").child(user_email).child(module_id).set(module_data)
        return True
    except Exception as e:
        st.error(f"Error saving module: {str(e)}")
        return False

def load_modules():
    """Load all modules for the current user"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        modules = db.child("modules").child(user_email).get().val()
        if modules:
            return pd.DataFrame(modules).T
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading modules: {str(e)}")
        return pd.DataFrame()

def delete_module(module_id):
    """Delete a module"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        db.child("modules").child(user_email).child(module_id).remove()
        return True
    except Exception as e:
        st.error(f"Error deleting module: {str(e)}")
        return False

# Main UI
st.header("Manage Modules")

# Add/Edit Module Form
with st.expander("Add/Edit Module", expanded=True):
    with st.form("module_form"):
        module_id = st.text_input("Module ID")
        module_name = st.text_input("Module Name")
        module_description = st.text_area("Description")
        module_credits = st.number_input("Credits", min_value=0, value=3, step=1)
        module_duration = st.number_input("Duration (weeks)", min_value=1, value=12, step=1)
        
        submitted = st.form_submit_button("Save Module")
        
        if submitted:
            if not module_id or not module_name:
                st.error("Module ID and Name are required")
            else:
                module_data = {
                    'module_id': module_id,
                    'name': module_name,
                    'description': module_description,
                    'credits': module_credits,
                    'duration_weeks': module_duration,
                    'created_at': pd.Timestamp.now().isoformat()
                }
                if save_module(module_data):
                    st.success(f"Module '{module_name}' saved successfully!")
                    st.rerun()

# Display existing modules
st.header("Current Modules")
modules_df = load_modules()

if not modules_df.empty:
    # Display as a nice table
    st.dataframe(
        modules_df[['name', 'description', 'credits', 'duration_weeks']],
        column_config={
            'name': 'Module Name',
            'description': 'Description',
            'credits': 'Credits',
            'duration_weeks': 'Duration (weeks)'
        },
        use_container_width=True
    )
    
    # Add delete button for each module
    for _, module in modules_df.iterrows():
        if st.button(f"Delete {module['name']}", key=f"del_{module['module_id']}"):
            if delete_module(module['module_id']):
                st.success(f"Module '{module['name']}' deleted successfully!")
                st.rerun()
else:
    st.info("No modules found. Add a new module using the form above.")

# Module Enrollment
st.header("Module Enrollment")

# Load students for enrollment
students_df, _ = load_students()

if not modules_df.empty and students_df is not None and not students_df.empty:
    with st.form("enrollment_form"):
        selected_module = st.selectbox(
            "Select Module",
            modules_df['name'].tolist(),
            format_func=lambda x: f"{x} ({modules_df[modules_df['name'] == x]['module_id'].iloc[0]})"
        )
        
        # Get module ID
        module_id = modules_df[modules_df['name'] == selected_module]['module_id'].iloc[0]
        
        # Display students for enrollment
        st.subheader("Enroll Students")
        
        # Create a multi-select for students
        student_options = [f"{row['Nombre']} {row['Apellido']} ({row['ID']})" for _, row in students_df.iterrows()]
        selected_students = st.multiselect(
            "Select students to enroll",
            student_options,
            key=f"enroll_{module_id}"
        )
        
        if st.form_submit_button("Save Enrollments"):
            # Here you would save the enrollments to Firebase
            st.success(f"Enrolled {len(selected_students)} students in {selected_module}")
else:
    if modules_df.empty:
        st.warning("No modules available. Please add modules first.")
    if students_df is None or students_df.empty:
        st.warning("No students available. Please add students first.")
