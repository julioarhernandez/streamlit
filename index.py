import streamlit as st
import pyrebase
from config import auth, db
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Student Management System",
    page_icon="🎓",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        max-width: 1000px;
        margin: 0 auto;
        padding: 2rem;
    }
    .login-container {
        max-width: 400px;
        margin: 5rem auto;
        padding: 2rem;
        border: 1px solid #ddd;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = None

# If user is logged in, redirect to Students page
if st.session_state.logged_in:
    st.switch_page("pages/1_Students.py")

# Main title
st.title("🎓 Student Management System")
st.markdown("---")

# Create a centered container for the login form
with st.container():
    # Use columns to center the form (empty columns on sides)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Create a form container with custom CSS
        st.markdown("""
        <style>
            .stContainer > div {
                padding: 2rem;
                border: 1px solid #ddd;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .stButton > button {
                width: 100%;
                margin-top: 1rem;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Create the form container
        with st.container():
            st.header("Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    try:
                        user = auth.sign_in_with_email_and_password(email, password)
                        st.session_state.logged_in = True
                        st.session_state.email = email
                        st.rerun()  # This will trigger the redirect to Students page
                    except Exception as e:
                        error_str = str(e)
                        if "INVALID_PASSWORD" in error_str or "EMAIL_NOT_FOUND" in error_str:
                            st.error("Invalid email or password")
                        else:
                            st.error(f"An error occurred: {error_str}")
    
    # Add some space at the bottom
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666;'>"
                "© 2025 Student Management System. All rights reserved.</div>", 
                unsafe_allow_html=True)