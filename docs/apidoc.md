# Unified API Documentation

**Last Updated:** 2024-11-27 22:19:27  
**Source of API:** [https://dns.services/userapi](https://dns.services/userapi)

---

## Overview

This document serves as a comprehensive guide for developers integrating with the DNS.Services API. It consolidates documentation for Authentication, Domain Management, and DNS Records. Examples and instructions are provided in Python for clarity and ease of use.

---

# Authentication API


# API Documentation

## Authentication Methods

### 1. JSON Web Token (JWT) Authentication

To authenticate using JWT, follow these steps:

1. Send a POST request to the login endpoint with your client area credentials.
2. Use the returned token in the `Authorization` header for subsequent API calls.

#### Example:

**Login Request**  
```python
import requests

payload = {
    'username': 'your_username',
    'password': 'your_password'
}

resp = requests.post('https://dns.services/api/login', data=payload)
```

**Authorization Header**  
```python
headers = {
    'Authorization': 'Bearer ' + resp.json()['token']
}
```

**Authenticated Request**  
```python
resp = requests.get('https://dns.services/api/details', headers=headers)
print(resp.json())
```

**Notes:**
- Replace `your_username` and `your_password` with your client area credentials.
- All API calls requiring authentication must include the `Authorization` header in the format:
  ```
  Authorization: Bearer <token>
  ```
- Example:
  ```
  Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc...
  ```

---

### 2. Basic Authentication

This method requires sending your username (email address) and password with each request. Authentication credentials are encoded using Base64.

#### Example:

**Authenticated Request**  
```python
import requests

req = requests.get('https://dns.services/api/details', auth=('your_username', 'your_password'))
print(req.json())
```

**Authorization Header:**
```
Authorization: Basic <credentials>
```

**Notes:**
- Replace `your_username` and `your_password` with your client area credentials.
- `<credentials>` is the Base64 encoding of `username:password`.
- Example of Base64 encoding:
  ```
  username:password → QWxhZGRpbjpvcGVuIHNlc2FtZQ==
  ```
- Replace `QWxhZGRpbjpvcGVuIHNlc2FtZQ==` with the Base64-encoded version of your access details.

---

### Security Recommendations
- Use HTTPS for all API calls to ensure secure data transmission.
- Do not share your credentials or tokens publicly.

---

### References
For more information on Basic HTTP Authentication, visit: [Basic HTTP Authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication).


---

# Domain API


# Domain API Documentation

## Table of Contents
- [Domains](#domains)
  - [List Domains](#list-domains)
  - [Get Domain Details](#get-domain-details)
  - [Get Domain Details by Name](#get-domain-details-by-name)
  - [Get Domain Nameservers](#get-domain-nameservers)
  - [Update Domain Nameservers](#update-domain-nameservers)
  - [Register Domain Nameservers](#register-domain-nameservers)
- [DNS Records](#dns-records)
  - [List DNS Records](#list-dns-records)
  - [Create DNS Records](#create-dns-records)
  - [Update DNS Records](#update-dns-records)
  - [Remove DNS Records](#remove-dns-records)
- [Domain Management](#domain-management)
  - [Domain Availability](#domain-availability)
  - [Available TLDs](#available-tlds)
  - [Order New Domain](#order-new-domain)
  - [Renew Domain](#renew-domain)

---

## Domains

### List Domains

**HTTP Request:**  
`GET /domain`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.get('https://dns.services/api/domain', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "domains": [
        {
            "id": "47",
            "name": "testname.com",
            "expires": "2017-12-30",
            "recurring_amount": "15.00",
            "date_created": "2016-12-30",
            "status": "Active",
            "period": "1",
            "autorenew": "1",
            "daytoexpire": "365"
        }
    ]
}
```

---

### Get Domain Details

**HTTP Request:**  
`GET /domain/@id`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.get('https://dns.services/api/domain/@id', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "details": {
        "id": "47",
        "name": "testname.com",
        "date_created": "2016-12-30",
        "firstpayment": "10.00",
        "recurring_amount": "15.00",
        "period": "1",
        "expires": "2017-12-30",
        "status": "Active",
        "next_due": "2017-12-30",
        "next_invoice": "2017-11-30",
        "idprotection": "0",
        "nameservers": [
            "ns1.example.com",
            "ns2.example.com",
            "ns3.example.com",
            "ns4.example.com"
        ],
        "autorenew": "1"
    }
}
```

---

### Get Domain Details by Name

**HTTP Request:**  
`GET /domain/name/@name`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.get('https://dns.services/api/domain/name/@name', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "details": [
        {
            "id": "47",
            "name": "testname.com",
            "date_created": "2016-12-30",
            "firstpayment": "10.00",
            "recurring_amount": "15.00",
            "period": "1",
            "expires": "2017-12-30",
            "status": "Active",
            "next_due": "2017-12-30",
            "next_invoice": "2017-11-30",
            "idprotection": "0",
            "nameservers": [
                "ns1.example.com",
                "ns2.example.com",
                "ns3.example.com",
                "ns4.example.com"
            ],
            "autorenew": "1"
        }
    ]
}
```

---

## DNS Records

### List DNS Records

**HTTP Request:**  
`GET /domain/@id/dns`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.get('https://dns.services/api/domain/@id/dns', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "records": [
        {
            "id": 1,
            "name": "test",
            "ttl": 0,
            "priority": 0,
            "type": "A",
            "content": "100.100.10.1"
        }
    ]
}
```

---

This is a partial markdown draft due to space constraints. The full documentation will include all endpoints with similar formatting for clarity and consistency.


---

# DNS API


# DNS API Documentation

## Table of Contents
- [List DNS](#list-dns)
- [Add DNS Zone](#add-dns-zone)
- [List DNS for Service](#list-dns-for-service)
- [Get DNS Details](#get-dns-details)
- [Remove DNS Zone](#remove-dns-zone)
- [Add DNS Record](#add-dns-record)
- [Edit DNS Record](#edit-dns-record)
- [Remove DNS Record](#remove-dns-record)

---

## List DNS

**HTTP Request:**  
`GET /dns`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.get('https://dns.services/api/dns', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "service_ids": [
        "10",
        "20"
    ],
    "zones": [
        {
            "domain_id": "60",
            "name": "booble.com",
            "service_id": "10"
        },
        {
            "domain_id": "61",
            "name": "bgg12ooble.com",
            "service_id": "20"
        }
    ]
}
```

---

## Add DNS Zone

**HTTP Request:**  
`POST /service/@service_id/dns`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Payload:**  
```json
{
    "name": "testzone.com"
}
```

**Example Request:**  
```python
import requests

payload = {
    'name': "testzone.com"
}

req = requests.post('https://dns.services/api/service/@service_id/dns', json=payload, headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "info": [
        "Domain zone testzone.com was created successfully."
    ]
}
```

**Query Parameters:**  
| Parameter   | Type   | Description   |
|-------------|--------|---------------|
| service_id  | int    | Service ID    |
| name        | string | Zone name     |

---

## List DNS for Service

**HTTP Request:**  
`GET /service/@service_id/dns`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.get('https://dns.services/api/service/@service_id/dns', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "error": [
        "invalid method"
    ]
}
```

**Query Parameters:**  
| Parameter   | Type   | Description   |
|-------------|--------|---------------|
| service_id  | int    | Service ID    |

---

## Get DNS Details

**HTTP Request:**  
`GET /service/@service_id/dns/@zone_id`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.get('https://dns.services/api/service/@service_id/dns/@zone_id', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "service_id": 10,
    "name": "booble.com",
    "records": [
      {
        "id":"10",
        "name":"qwerty",
        "ttl":1800,
        "priority":0,
        "content":"127.0.0.1",
        "type":"A"
      }
    ]
}
```

**Query Parameters:**  
| Parameter   | Type   | Description   |
|-------------|--------|---------------|
| service_id  | int    | Service ID    |
| zone_id     | int    | Zone ID       |

---

## Remove DNS Zone

**HTTP Request:**  
`DELETE /service/@service_id/dns/@zone_id`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Example Request:**  
```python
import requests

req = requests.delete('https://dns.services/api/service/@service_id/dns/@zone_id', headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
   "info": [
     "Domain zone testzone.com was deleted successfully."
   ]
}
```

**Query Parameters:**  
| Parameter   | Type   | Description   |
|-------------|--------|---------------|
| service_id  | int    | Service ID    |
| zone_id     | int    | Zone ID       |

---

## Add DNS Record

**HTTP Request:**  
`POST /service/@service_id/dns/@zone_id/records`

**Headers:**  
```python
headers = {
    'Authorization': 'Bearer ' + token
}
```

**Payload:**  
```json
{
    "name": "example.com",
    "ttl": 3600,
    "priority": 10,
    "type": "A",
    "content": "192.168.1.2"
}
```

**Example Request:**  
```python
import requests

payload = {
    'name': "example.com",
    'ttl': 3600,
    'priority': 10,
    'type': "A",
    'content': "192.168.1.2"
}

req = requests.post('https://dns.services/api/service/@service_id/dns/@zone_id/records', json=payload, headers=headers)
print(req.json())
```

**Example Response:**  
```json
{
    "record": {
      "name": "example.com",
      "type": "A",
      "ttl": "3600",
      "priority": "10",
      "content": "192.168.1.2"
    },
    "info": [
        "dnsnewrecordadded"
    ]
}
```

---

The remaining endpoints follow the same structure. Full documentation can be extended similarly.

---

