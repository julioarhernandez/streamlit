import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Load the existing credentials
with open('credentials.yaml', 'r') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Hash all passwords
for username, user_data in config['credentials']['usernames'].items():
    if not user_data['password'].startswith('$2b$'):  # Check if password is not already hashed
        hashed_password = stauth.Hasher([user_data['password']])[0]
        user_data['password'] = hashed_password
        print(f"Hashed password for {username}")
    else:
        print(f"Password for {username} is already hashed")

# Save the hashed credentials to a new file
with open('hashed_credentials.yaml', 'w') as file:
    yaml.dump(config, file, default_flow_style=False)

print("\n✅ Hashed credentials saved to 'hashed_credentials.yaml'")
print("\n⚠️  Please rename 'hashed_credentials.yaml' to 'credentials.yaml' after verification")
