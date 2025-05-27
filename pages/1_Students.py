import streamlit as st
import pandas as pd
from config import setup_page, db

# Setup page
setup_page("Students Management")

def save_students(students_df):
    """Save students data to Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        data = {
            'filename': 'students.xlsx',
            'data': students_df.to_dict('records'),
            'timestamp': pd.Timestamp.now().isoformat()
        }
        db.child("students").child(user_email).set(data)
        return True
    except Exception as e:
        st.error(f"Error saving students: {str(e)}")
        return False

def load_students():
    """Load students data from Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        data = db.child("students").child(user_email).get().val()
        if data and 'data' in data:
            return pd.DataFrame(data['data']), data.get('filename', 'students.xlsx')
        return None, None
    except Exception as e:
        st.error(f"Error loading students: {str(e)}")
        return None, None

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
        
        # Show preview
        st.subheader("Preview")
        st.dataframe(df.head())
        
        if st.button("Save Students"):
            if save_students(df):
                st.success("Students data saved successfully!")
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

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
