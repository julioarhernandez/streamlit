import streamlit as st

st.title("Test Page")
st.write("If you can see this, Streamlit is working!")

name = st.text_input("Enter your name")
if name:
    st.write(f"Hello, {name}!")
