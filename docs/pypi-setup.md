# PyPI Setup Instructions

1. Create a PyPI Account:
   - Go to https://pypi.org/account/register/
   - Create an account if you don't have one

2. Generate an API Token:
   - Log in to PyPI
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Name: "dns-services-gateway-github-actions"
   - Set scope to: "Project: dns-services-gateway"
   - Copy the token immediately (you won't see it again)

3. Add Environment to GitHub:
   - Go to your GitHub repository
   - Click Settings > Environments > New environment
   - Fill out these exact fields:
     * Owner: mikl0s
     * Repository name: dns.services
     * Workflow name: ci.yml
     * Environment name: release
   - Click "Add"
   - In the environment settings:
     * Click "Add secret"
     * Name: PYPI_API_TOKEN
     * Value: (paste the token you copied from PyPI)
     * Click "Add secret"

4. Test the Setup:
   - Create a new release tag in GitHub
   - The GitHub Actions workflow will automatically:
     - Run tests across all supported Python versions
     - Build the package
     - Upload to PyPI if all tests pass

Note: The package will be available at: https://pypi.org/project/dns-services-gateway/