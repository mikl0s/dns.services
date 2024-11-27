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
    print(
        "Error: DNS_SERVICES_USERNAME, DNS_SERVICES_PASSWORD, or DNS_SERVICES_BASE_URL not set in .env file."
    )
    sys.exit(1)


# ANSI color codes
class AnsiColors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"


# Function to print messages with optional icons and colors
def print_message(message, icon, color, no_color):
    if no_color:
        print(message)
    else:
        print(f"{color}{icon} {message}{AnsiColors.RESET}")


# Initialize argument parser
parser = argparse.ArgumentParser(description="DNS Services Gateway Script")
parser.add_argument("domain", type=str, help="Domain to manage")
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Enable verbose output"
)
parser.add_argument(
    "--no-color", action="store_true", help="Disable colored output and icons"
)
args = parser.parse_args()

no_color = args.no_color


# Verbose logging function
def log(message):
    if args.verbose:
        print_message(message, "", AnsiColors.YELLOW, no_color)


# Authenticate and get JWT token
def authenticate():
    url = f"{DNS_SERVICES_BASE_URL}/api/login"
    payload = {"username": DNS_SERVICES_USERNAME, "password": DNS_SERVICES_PASSWORD}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return {"status": "success", "token": response.json().get("token")}
    else:
        return {"status": "failure", "error": response.text}


# Headers for authentication
def get_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# List DNS records
def list_dns_records(domain_id, token):
    headers = {"Authorization": "Bearer " + token}
    response = requests.get(
        f"{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns", headers=headers
    )
    if response.status_code == 200:
        return {"status": "success", "records": response.json()}
    else:
        return {"status": "failure", "error": response.text}


# Create DNS record
def create_dns_record(domain_id, token, name, record_type, priority, content):
    headers = {"Authorization": "Bearer " + token}
    payload = {
        "name": name,
        "type": record_type,
        "priority": priority,
        "content": content,
        "ttl": 3600,
    }
    response = requests.post(
        f"{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns",
        json=payload,
        headers=headers,
    )
    if response.status_code == 201:
        return {"status": "success", "record_id": response.json().get("id")}
    else:
        return {"status": "failure", "error": response.text}


# Update DNS record
def update_dns_record(
    domain_id, record_index, token, name, record_type, priority, content
):
    headers = {"Authorization": "Bearer " + token}
    payload = {
        "name": name,
        "type": record_type,
        "priority": priority,
        "content": content,
        "ttl": 3600,
    }
    response = requests.put(
        f"{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns/{record_index}",
        json=payload,
        headers=headers,
    )
    if response.status_code == 200:
        return {"status": "success", "record_id": record_index}
    else:
        return {"status": "failure", "error": response.text}


# Delete DNS record
def delete_dns_record(domain_id, record_index, token):
    headers = {"Authorization": "Bearer " + token}
    response = requests.delete(
        f"{DNS_SERVICES_BASE_URL}/api/domain/{domain_id}/dns/{record_index}",
        headers=headers,
    )
    if response.status_code == 204:
        return {"status": "success"}
    else:
        return {"status": "failure", "error": response.text}


# Add DNS record
def add_dns_record(
    service_id, zone_id, token, name, ttl, priority, record_type, content
):
    headers = {"Authorization": "Bearer " + token}
    payload = {
        "name": name,
        "type": record_type,
        "priority": priority,
        "content": content,
        "ttl": ttl,
    }
    response = requests.post(
        f"{DNS_SERVICES_BASE_URL}/api/service/{service_id}/dns/{zone_id}/records",
        json=payload,
        headers=headers,
    )
    if response.status_code == 201:
        return {"status": "success", "record_id": response.json().get("id")}
    else:
        return {"status": "failure", "error": response.text}


# Edit DNS record
def edit_dns_record(
    service_id, zone_id, record_id, token, name, ttl, priority, record_type, content
):
    headers = {"Authorization": "Bearer " + token}
    payload = {
        "name": name,
        "type": record_type,
        "priority": priority,
        "content": content,
        "ttl": ttl,
    }
    response = requests.put(
        f"{DNS_SERVICES_BASE_URL}/api/service/{service_id}/dns/{zone_id}/records/{record_id}",
        json=payload,
        headers=headers,
    )
    if response.status_code == 200:
        return {"status": "success", "record_id": record_id}
    else:
        return {"status": "failure", "error": response.text}


# Remove DNS record
def remove_dns_record(service_id, zone_id, record_id, token):
    headers = {"Authorization": "Bearer " + token}
    response = requests.delete(
        f"{DNS_SERVICES_BASE_URL}/api/service/{service_id}/dns/{zone_id}/records/{record_id}",
        headers=headers,
    )
    if response.status_code == 204:
        return {"status": "success"}
    else:
        return {"status": "failure", "error": response.text}


def main():
    domain = args.domain

    try:
        # Authenticate and get the token
        print_message("Authenticating...", "🔑", AnsiColors.BLUE, no_color)
        auth_response = authenticate()
        if auth_response["status"] != "success":
            print_message(
                f"Authentication failed: {auth_response['error']}",
                "❌",
                AnsiColors.RED,
                no_color,
            )
            sys.exit(1)
        token = auth_response["token"]
        print_message("Authentication successful.", "✅", AnsiColors.GREEN, no_color)

        # Fetch DNS zones to find the domain
        print_message("Fetching DNS zones...", "🌐", AnsiColors.BLUE, no_color)
        response = requests.get(
            f"{DNS_SERVICES_BASE_URL}/api/dns", headers=get_headers(token)
        )
        response.raise_for_status()
        dns_zones = response.json()["zones"]
        print_message(f"DNS zones retrieved.", "✅", AnsiColors.GREEN, no_color)

        domain_info = next((zone for zone in dns_zones if zone["name"] == domain), None)
        if not domain_info:
            print_message(
                f"Error: Domain {domain} not found.", "❌", AnsiColors.RED, no_color
            )
            sys.exit(1)

        zone_id = domain_info["domain_id"]
        service_id = domain_info["service_id"]
        print_message(
            f"Zone ID for domain {domain}: {zone_id}, Service ID: {service_id}",
            "🔍",
            AnsiColors.YELLOW,
            no_color,
        )

        # Example of creating a DNS record using the generic function
        txt_name = "test-record"
        txt_content = "Initial TXT record content"
        print_message(
            f"Creating TXT record: {txt_name}", "📝", AnsiColors.BLUE, no_color
        )
        record_response = add_dns_record(
            service_id, zone_id, token, txt_name, 3600, 0, "TXT", txt_content
        )
        if record_response["status"] != "success":
            print_message(
                f"Failed to create TXT record: {record_response['error']}",
                "❌",
                AnsiColors.RED,
                no_color,
            )
            sys.exit(1)
        record_id = record_response["record_id"]
        print_message(f"TXT record created.", "✅", AnsiColors.GREEN, no_color)

        # Update DNS record using the generic function
        updated_content = "Updated TXT record content"
        print_message(
            f"Updating TXT record ID: {record_id}", "🔄", AnsiColors.BLUE, no_color
        )
        updated_record_response = edit_dns_record(
            service_id,
            zone_id,
            record_id,
            token,
            txt_name,
            3600,
            0,
            "TXT",
            updated_content,
        )
        if updated_record_response["status"] != "success":
            print_message(
                f"Failed to update TXT record: {updated_record_response['error']}",
                "❌",
                AnsiColors.RED,
                no_color,
            )
            sys.exit(1)
        print_message("TXT record updated.", "✅", AnsiColors.GREEN, no_color)

        # Delete DNS record using the generic function
        print_message(
            f"Deleting TXT record ID: {record_id}", "🗑️", AnsiColors.BLUE, no_color
        )
        delete_status = remove_dns_record(service_id, zone_id, record_id, token)
        if delete_status["status"] != "success":
            print_message(
                f"Failed to delete TXT record: {delete_status['error']}",
                "❌",
                AnsiColors.RED,
                no_color,
            )
            sys.exit(1)
        print_message("TXT record deleted.", "✅", AnsiColors.GREEN, no_color)

    except requests.exceptions.RequestException as e:
        print_message(f"API request failed: {e}", "❌", AnsiColors.RED, no_color)
        sys.exit(1)


if __name__ == "__main__":
    main()
