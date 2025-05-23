import streamlit_authenticator as stauth

# Hash the password
hashed_password = stauth.Hasher(['password']).generate()[0]
print(f"Hashed password: {hashed_password}")
