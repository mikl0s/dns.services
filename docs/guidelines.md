# Development Guidelines

1. Always use virtual environment commands from `venv/bin/` (e.g., `venv/bin/python`, `venv/bin/pip`)
2. Create virtual environment with `python3 -m venv venv` before starting development if no virtual environment exists
3. Activate virtual environment: `. venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `venv/bin/pip install -r requirements-dev.txt`
5. Install pre-commit hooks: `venv/bin/pre-commit install`
6. Run tests with `venv/bin/pytest tests/`
7. Check type hints with `venv/bin/mypy src/`
8. Format code with `venv/bin/black src/ tests/`
9. Run linting with `venv/bin/flake8 src/ tests/`
10. Generate coverage report: `venv/bin/pytest --cov=dns_services_gateway tests/`
11. Keep functions focused and single-purpose
12. Add type hints to all function parameters and return values
13. Write docstrings for all public functions and classes
14. Include example usage in docstrings
15. Create unit tests for new functionality
16. Mock external API calls in tests
17. Verify API responses match expected schemas
18. Handle errors gracefully with meaningful messages
19. Use structured responses for all operations
20. Follow semantic versioning for releases
21. Update documentation when adding features
22. Run full test suite before committing
23. Keep commits focused and well-described
24. Branch from main for feature development
25. Submit pull requests with comprehensive descriptions
