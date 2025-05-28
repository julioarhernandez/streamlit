import streamlit as st
import pyrebase

# Firebase configuration
firebaseConfig = {
    "apiKey": "AIzaSyCjB9UI5Soj6dHlbzCnrbBuzIfeWKEPMvw",
    "databaseURL": "https://attendance-bfa78-default-rtdb.firebaseio.com",
    "authDomain": "attendance-bfa78.firebaseapp.com",
    "projectId": "attendance-bfa78",
    "storageBucket": "attendance-bfa78.firebasestorage.app",
    "messagingSenderId": "13347487257",
    "appId": "1:13347487257:web:eadf04fb63d40086d4f488",
    "measurementId": "G-K8KWGGWRX4"
}

# Initialize Firebase
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

def check_auth():
    """Check if user is logged in, redirect to login if not"""
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.switch_page("Home.py")

def setup_page(title):
    """Common page setup with title."""
    st.set_page_config(page_title=title, layout="centered")
    st.title(title)
