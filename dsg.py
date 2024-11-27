import os
import sys
import requests
from dotenv import load_dotenv
import argparse

# Load environment variables from .env file
load_dotenv()

# Get credentials and base URL from environment variables
DNS_SERVICES_USERNAME = os.getenv("DNS_SERVICES_USERNAME")
DNS_SERVICES_PASSWORD = os.getenv("DNS_SERVICES_PASSWORD")
DNS_SERVICES_BASE_URL = os.getenv("DNS_SERVICES_BASE_URL")

if not DNS_SERVICES_USERNAME or not DNS_SERVICES_PASSWORD or not DNS_SERVICES_BASE_URL:
    print("Error: DNS_SERVICES_USERNAME, DNS_SERVICES_PASSWORD, or DNS_SERVICES_BASE_URL not set in .env file.")
    sys.exit(1)

# ANSI color codes
class AnsiColors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

# Function to print messages with optional icons and colors
def print_message(message, icon, color, no_color):
    if no_color:
        print(message)
    else:
        print(f"{color}{icon} {message}{AnsiColors.RESET}")

# Initialize argument parser
parser = argparse.ArgumentParser(description='DNS Services Gateway Script')
parser.add_argument('domain', type=str, help='Domain to manage')
parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
parser.add_argument('--no-color', action='store_true', help='Disable colored output and icons')
args = parser.parse_args()

no_color = args.no_color

# Verbose logging function
def log(message):
    if args.verbose:
        print_message(message, "", AnsiColors.YELLOW, no_color)

# Authenticate and get JWT token
def authenticate():
    url = f"{DNS_SERVICES_BASE_URL}/api/login"
    payload = {
        "username": DNS_SERVICES_USERNAME,
        "password": DNS_SERVICES_PASSWORD
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["token"]

# Headers for authentication
def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

# Create a TXT record
def create_txt_record(token, zone_id, name, content):
    url = f"{DNS_SERVICES_BASE_URL}/api/zones/{zone_id}/records"
    payload = {
        "type": "TXT",
        "name": name,
        "content": content,
        "ttl": 3600
    }
    response = requests.post(url, headers=get_headers(token), json=payload)
    response.raise_for_status()
    return response.json()

# Update a TXT record
def update_txt_record(token, zone_id, record_id, new_content):
    url = f"{DNS_SERVICES_BASE_URL}/api/zones/{zone_id}/records/{record_id}"
    payload = {
        "content": new_content,
        "ttl": 3600
    }
    response = requests.put(url, headers=get_headers(token), json=payload)
    response.raise_for_status()
    return response.json()

# Delete a TXT record
def delete_txt_record(token, zone_id, record_id):
    url = f"{DNS_SERVICES_BASE_URL}/api/zones/{zone_id}/records/{record_id}"
    response = requests.delete(url, headers=get_headers(token))
    response.raise_for_status()
    return response.status_code

# List DNS records
def list_dns_records(domain_id, token):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    response = requests.get(f'{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns', headers=headers)
    return response.json()

# Create DNS record
def create_dns_record(domain_id, token, name, record_type, priority, content):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    payload = {
        'name': name,
        'type': record_type,
        'priority': priority,
        'content': content
    }
    response = requests.post(f'{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns', json=payload, headers=headers)
    return response.json()

# Update DNS record
def update_dns_record(domain_id, record_index, token, name, record_type, priority, content):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    payload = {
        'name': name,
        'type': record_type,
        'priority': priority,
        'content': content
    }
    response = requests.put(f'{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns/{record_index}', json=payload, headers=headers)
    return response.json()

# Delete DNS record
def delete_dns_record(domain_id, record_index, token):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    response = requests.delete(f'{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns/{record_index}', headers=headers)
    return response.json()

def add_dns_record(service_id, zone_id, token, name, ttl, priority, record_type, content):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    payload = {
        'name': name,
        'ttl': ttl,
        'priority': priority,
        'type': record_type,
        'content': content
    }
    response = requests.post(f'{DNS_SERVICES_BASE_URL}/api/service/{service_id}/dns/{zone_id}/records', json=payload, headers=headers)
    return response.json()

def edit_dns_record(service_id, zone_id, record_id, token, name, ttl, priority, record_type, content):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    payload = {
        'name': name,
        'ttl': ttl,
        'priority': priority,
        'type': record_type,
        'content': content
    }
    response = requests.put(f'{DNS_SERVICES_BASE_URL}/api/service/{service_id}/dns/{zone_id}/records/{record_id}', json=payload, headers=headers)
    return response.json()

def remove_dns_record(service_id, zone_id, record_id, token):
    headers = {
        'Authorization': 'Bearer ' + token
    }
    response = requests.delete(f'{DNS_SERVICES_BASE_URL}/api/service/{service_id}/dns/{zone_id}/records/{record_id}', headers=headers)
    return response.json()

def main():
    domain = args.domain

    try:
        # Authenticate and get the token
        print_message("Authenticating...", "🔑", AnsiColors.BLUE, no_color)
        token = authenticate()
        print_message("Authentication successful.", "✅", AnsiColors.GREEN, no_color)

        # Fetch DNS zones to find the domain
        print_message("Fetching DNS zones...", "🌐", AnsiColors.BLUE, no_color)
        response = requests.get(f"{DNS_SERVICES_BASE_URL}/api/dns", headers=get_headers(token))
        response.raise_for_status()
        dns_zones = response.json()["zones"]
        print_message(f"DNS zones retrieved.", "✅", AnsiColors.GREEN, no_color)

        domain_info = next((zone for zone in dns_zones if zone["name"] == domain), None)
        if not domain_info:
            print_message(f"Error: Domain {domain} not found.", "❌", AnsiColors.RED, no_color)
            sys.exit(1)

        zone_id = domain_info["domain_id"]
        service_id = domain_info["service_id"]
        print_message(f"Zone ID for domain {domain}: {zone_id}, Service ID: {service_id}", "🔍", AnsiColors.YELLOW, no_color)

        # Step 1: Create TXT record using the correct endpoint
        txt_name = "test-record"
        txt_content = "Initial TXT record content"
        print_message(f"Creating TXT record: {txt_name}", "📝", AnsiColors.BLUE, no_color)
        record = add_dns_record(service_id, zone_id, token, txt_name, 3600, 0, "TXT", txt_content)
        print_message(f"TXT record created.", "✅", AnsiColors.GREEN, no_color)

        # Fetch DNS details to find the record ID
        response = requests.get(f'{DNS_SERVICES_BASE_URL}/api/service/{service_id}/dns/{zone_id}', headers=get_headers(token))
        response.raise_for_status()
        dns_details = response.json()
        record_info = next((r for r in dns_details["records"] if r["name"] == f"{txt_name}.{domain}" and r["content"] == f'"{txt_content}"'), None)
        if not record_info:
            print_message("Error: Failed to find the created TXT record.", "❌", AnsiColors.RED, no_color)
            sys.exit(1)

        record_id = record_info["id"]
        print_message(f"TXT record created with ID: {record_id}", "🔍", AnsiColors.YELLOW, no_color)

        # Step 2: Update TXT record
        updated_content = "Updated TXT record content"
        print_message(f"Updating TXT record ID: {record_id}", "🔄", AnsiColors.BLUE, no_color)
        updated_record = edit_dns_record(service_id, zone_id, record_id, token, txt_name, 3600, 0, "TXT", updated_content)
        print_message("TXT record updated.", "✅", AnsiColors.GREEN, no_color)

        # Step 3: Delete TXT record
        print_message(f"Deleting TXT record ID: {record_id}", "🗑️", AnsiColors.BLUE, no_color)
        delete_status = remove_dns_record(service_id, zone_id, record_id, token)
        print_message("TXT record deleted.", "✅", AnsiColors.GREEN, no_color)

    except requests.exceptions.RequestException as e:
        print_message(f"API request failed: {e}", "❌", AnsiColors.RED, no_color)
        sys.exit(1)

if __name__ == "__main__":
    main()
