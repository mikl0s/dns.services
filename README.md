# 🌐 DNS Services Gateway

Welcome to the **DNS Services Gateway** project! This Python script allows you to interact with the DNS.services API to manage your DNS records and domains effortlessly.

---

## ✨ Features

- **🔐 Authentication**: Securely retrieve JWT tokens using environment variables for credentials.
- **🌍 Domain Management**: Fetch domain details and list domains with ease.
- **🛠️ DNS Record Management**: Seamlessly list, create, update, and delete DNS records.

---

## 📋 Prerequisites

- **Python 3.x**
- **`requests` library**
- **`python-dotenv` library**

---

## ⚙️ Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd dns-services-gateway
   ```

2. **Install the required Python libraries**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the root directory with the following variables:
   ```
   DNS_SERVICES_BASE_URL="https://dns.services"
   DNS_SERVICES_USERNAME="your-username"
   DNS_SERVICES_PASSWORD="your-password"
   ```

---

## 🚀 Usage

Run the script to manage DNS records:

```bash
python dsg.py <domain-name>
```

### Options

- `-v`, `--verbose`: Enable verbose output.
- `--no-color`: Disable colored output and icons.

---

## 📚 Example

To manage DNS records for `example.com`:

```bash
python dsg.py example.com -v
```

---

## 📝 Notes

- Ensure your credentials are correctly set in the `.env` file.
- The script uses JWT for authentication and manages DNS records through the DNS.services API.

---

## 📄 License

This project is licensed under the MIT License.

---
