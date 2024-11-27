import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DNS_SERVICES_BASE_URL = os.getenv('DNS_SERVICES_BASE_URL')
DNS_SERVICES_USERNAME = os.getenv('DNS_SERVICES_USERNAME')
DNS_SERVICES_PASSWORD = os.getenv('DNS_SERVICES_PASSWORD')

def authenticate():
    # Authenticate and get JWT token
    response = requests.post(f"{DNS_SERVICES_BASE_URL}/api/login", json={
        'username': DNS_SERVICES_USERNAME,
        'password': DNS_SERVICES_PASSWORD
    })
    response.raise_for_status()
    return response.json()['token']


def list_dns(token):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    response = requests.get(f'{DNS_SERVICES_BASE_URL}/api/dns', headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    # Authenticate and get the token
    print("Authenticating...")
    token = authenticate()
    print("Authentication successful. Token retrieved.")

    # List DNS
    print("Listing all DNS...")
    dns_list = list_dns(token)
    print("DNS List:", dns_list)


if __name__ == "__main__":
    main()
