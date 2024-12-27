# PyPI Setup Instructions

1. Create a PyPI Account:
   - Go to https://pypi.org/account/register/
   - Create an account if you don't have one

2. Initial Manual Package Upload:
   - Build the package locally:
     ```bash
     python -m pip install --upgrade build twine
     python -m build
     ```
   - Upload to PyPI:
     ```bash
     python -m twine upload dist/*
     ```
   - This will prompt for your PyPI username and password
   - After successful upload, you'll be the package owner

3. Configure PyPI Trusted Publishing:
   - Go to PyPI project settings: https://pypi.org/manage/project/dns.services/settings/
   - Under "Publishing", click "Add pending publisher"
   - Fill out these exact fields:
     * PyPI Project Name: dns.services
     * Owner: mikl0s
     * Repository name: dns.services
     * Workflow name: ci.yml
     * Environment name: pypi
   - Click "Add"
   - Wait for PyPI administrators to approve the publisher

4. Configure GitHub Environment:
   - Go to your GitHub repository settings
   - Click Settings > Environments > New environment
   - Create environment named: pypi
   - No additional configuration needed
   - Click "Save"

5. Test the Setup:
   - Once the publisher is approved
   - Create a new release tag in GitHub
   - The GitHub Actions workflow will automatically:
     - Run tests
     - Build the package
     - Upload to PyPI using trusted publishing

Note: The package will be available at: https://pypi.org/project/dns.services/