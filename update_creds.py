import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Hash the password
hashed_password = stauth.Hasher(['password']).generate()

# Create the credentials dictionary
credentials = {
    'credentials': {
        'usernames': {
            'admin': {
                'email': 'admin@example.com',
                'name': 'Admin User',
                'password': hashed_password[0]  # Get the first (and only) hashed password
            }
        }
    },
    'cookie': {
        'expiry_days': 30,
        'key': 'some_signature_key',
        'name': 'some_cookie_name'
    }
}

# Save to YAML file
with open('credentials.yaml', 'w') as file:
    yaml.dump(credentials, file, default_flow_style=False)

print("Credentials file updated successfully!")
