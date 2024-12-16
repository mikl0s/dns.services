# Development Guidelines

1. Activate the virtual environment before running any commands: `. .venv/bin/activate`
2. Create the virtual environment if it does not exist using: `python3 -m venv .venv`
3. Install dependencies with `pip install -r requirements-dev.txt`
4. Install pre-commit hooks using `pre-commit install`
5. Run tests with `pytest tests/`
6. Check type hints using `mypy src/`
7. Format code with `black src/ tests/`
8. Perform linting with `flake8 src/ tests/`
9. Generate a coverage report using: `pytest --cov=src tests/ --cov-report=term-missing -v`
10. Ensure all functions are focused and single-purpose
11. Add type hints to all function parameters and return values
12. Write docstrings for all public functions and classes
13. Include example usage in docstrings
14. Create unit tests for new functionality
15. Mock external API calls in tests
16. Verify that API responses match expected schemas
17. Handle errors gracefully with meaningful messages
18. Use structured responses for all operations
19. Follow semantic versioning for releases
20. Update documentation when adding features
21. Run the full test suite before committing changes
22. Keep commits focused and well-described
23. Branch from the main branch for feature development
24. Submit pull requests with comprehensive descriptions
