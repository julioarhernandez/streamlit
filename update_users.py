import streamlit_authenticator as stauth
import yaml

# Define the new users with their details
new_users = [
    {
        'username': 'julio',
        'name': 'Julio Rodriguez',
        'email': 'julio@example.com',
        'password': 'julio123'
    },
    {
        'username': 'maria',
        'name': 'Maria Garcia',
        'email': 'maria@example.com',
        'password': 'maria123'
    },
    {
        'username': 'carlos',
        'name': 'Carlos Lopez',
        'email': 'carlos@example.com',
        'password': 'carlos123'
    },
    {
        'username': 'ana',
        'name': 'Ana Martinez',
        'email': 'ana@example.com',
        'password': 'ana123'
    }
]

def main():
    # Load existing credentials
    with open('credentials.yaml', 'r') as file:
        credentials = yaml.safe_load(file)
    
    # Add new users to credentials
    for user in new_users:
        credentials['credentials']['usernames'][user['username']] = {
            'email': user['email'],
            'name': user['name'],
            'password': user['password']  # Will be hashed automatically
        }
    
    # Save updated credentials
    with open('credentials.yaml', 'w') as file:
        yaml.dump(credentials, file, default_flow_style=False)
    
    print("Successfully updated credentials.yaml with new users!")
    print("\nNew users added:")
    for user in new_users:
        print(f"- {user['name']} (Username: {user['username']}, Password: {user['password']})")

if __name__ == "__main__":
    main()
