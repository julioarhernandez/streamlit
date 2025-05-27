import streamlit as st
import pandas as pd
from config import setup_page
from utils import save_students, load_students

# Setup page
setup_page("Students Management")

# Main UI
st.header("Manage Students")

# File upload section
uploaded_file = st.file_uploader("Upload Students File (CSV or Excel)", 
                               type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)
        
        # Normalize column names (convert to lowercase)
        df.columns = df.columns.str.lower().str.strip()
        
        # Check for required columns
        required_columns = {'id', 'nombre', 'apellido'}
        missing_columns = required_columns - set(df.columns)
        
        if missing_columns:
            st.error(f"Error: The uploaded file is missing required columns: {', '.join(missing_columns)}. "
                    f"Please make sure your file includes these columns: id, nombre, apellido")
        else:
            # Ensure ID is string and trim whitespace from string columns
            df['id'] = df['id'].astype(str).str.strip()
            df['nombre'] = df['nombre'].str.strip()
            df['apellido'] = df['apellido'].str.strip()
            
            # Show preview
            st.subheader("Preview")
            st.dataframe(df.head())
            
            # Show column mapping information
            st.info("Make sure your columns are mapped correctly:")
            st.json({
                "id": "Student ID (must be unique)",
                "nombre": "First Name",
                "apellido": "Last Name"
            })
            
            if st.button("Save Students"):
                if save_students(df):
                    st.success("Students data saved successfully!")
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        st.error("Please make sure the file is not open in another program and try again.")

# Show existing data
df, filename = load_students()
if df is not None:
    st.subheader("Current Students")
    st.dataframe(df)
    
    # Export options
    st.download_button(
        label="Download as CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=filename or 'students.csv',
        mime='text/csv',
    )
else:
    st.info("No students data found. Please upload a file to get started.")
