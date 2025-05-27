import streamlit as st
import pandas as pd
from config import db

def load_students():
    """Load students data from Firebase"""
    try:
        user_email = st.session_state.email.replace('.', ',')
        data = db.child("students").child(user_email).get().val()
        if data and 'data' in data:
            df = pd.DataFrame(data['data'])
            # Normalize column names
            df.columns = df.columns.str.lower()
            # Ensure 'id' column is string and other required columns are present and stripped
            if 'id' in df.columns:
                df['id'] = df['id'].astype(str).str.strip()
            if 'nombre' in df.columns:
                df['nombre'] = df['nombre'].astype(str).str.strip()
            if 'apellido' in df.columns:
                df['apellido'] = df['apellido'].astype(str).str.strip()
            return df, data.get('filename', 'students.xlsx')
        return None, None
    except Exception as e:
        st.error(f"Error loading students: {str(e)}")
        return None, None

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
