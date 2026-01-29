import os
import sys

sys.path.insert(0, os.path.abspath('..'))

# Variables de entorno dummy para que Pydantic no falle
os.environ.setdefault('ODOO_URL', 'http://dummy')
os.environ.setdefault('ODOO_DB', 'dummy')
os.environ.setdefault('ODOO_USERNAME', 'dummy')
os.environ.setdefault('ODOO_PASSWORD', 'dummy')
os.environ.setdefault('API_MISTRAL_KEY', 'dummy')

# Módulos externos a mockear
autodoc_mock_imports = [
    "pandas", "numpy", "joblib", "plotly",
    "pydantic", "pydantic_settings",
    "langgraph", "langchain_core", "langchain_mistralai",
    "fastmcp", "mcp", "a2a", "tenacity",
    "odoorpc", "psycopg2", "httpx",
    "streamlit", "uvicorn", "fastapi",
]

# -- Project information -----------------------------------------------------
project = 'B2B Invoice Payment Prediction Agent'
copyright = '2025, Ismael Fernandez Zarza'
author = 'Ismael Fernandez Zarza'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
language = 'es'

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

# -- Options for HTML output -------------------------------------------------
html_theme = 'furo'
html_static_path = ['_static']
