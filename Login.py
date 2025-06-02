import streamlit as st
import pyrebase
from config import auth, db
from datetime import datetime

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        /* max-width: 1000px; Remove or adjust if layout="wide" is preferred globally */
        /* margin: 0 auto; */
        padding: 1rem; /* Adjusted padding */
    }
    .login-container {
        max-width: 400px;
        margin: 3rem auto; /* Adjusted margin */
        padding: 2rem;
        border: 1px solid #ddd;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        background-color: #ffffff; /* Ensure background for better visibility if page bg changes */
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for login if not already present
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.user_token = None # To store Firebase token

def login_user(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        st.session_state.logged_in = True
        st.session_state.email = user['email']
        st.session_state.user_token = user['idToken'] # Store the token
        st.cache_data.clear()
        st.rerun()
    except Exception as e: # Catch generic Firebase errors or others
        st.error(f"Error de inicio de sesión: Usuario o contraseña incorrectos.")
        # st.error(f"Detalles del error: {e}") # For debugging, if needed

def logout_user():
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.user_token = None
    # Potentially clear other session state variables related to the user
    st.rerun()

# --- Page Logic ---
if not st.session_state.logged_in:

    st.markdown("<h2 style='text-align: center;'>Iniciar Sesión</h2>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input("Correo Electrónico", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        submitted = st.form_submit_button("Iniciar Sesión", type="primary")

        if submitted:
            if email and password:
                login_user(email, password)
            else:
                st.warning("Por favor, ingrese su correo y contraseña.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Hide sidebar when not logged in if desired (more complex, requires st_pages or similar)
    # For now, Streamlit will show 'index' in the sidebar.

else:
    user_name = "Usuario"
    if st.session_state.get('email'):
        try:
            name_part = st.session_state.email.split('@')[0]
            user_name = name_part.capitalize()
        except Exception:
            pass # Keep 'Usuario' if email format is unexpected

    st.sidebar.title(f"Bienvenido, {user_name}")
    if st.session_state.get('email'): # Check if email exists before writing
        st.sidebar.write(st.session_state.email)
    if st.sidebar.button("Cerrar Sesión"):
        logout_user()
    
    st.title("🎓 Sistema de Gestión Estudiantil")
    st.write("### ¡Bienvenido!")
    st.write("Seleccione una opción del menú lateral para continuar.")
    st.info("Recuerde que todas las operaciones se guardan automáticamente en la base de datos.")