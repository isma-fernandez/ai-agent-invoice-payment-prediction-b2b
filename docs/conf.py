import os
import sys

# Evitar errores de importación para módulos externos no instalados
autodoc_mock_imports = [
    "pandas",
    "numpy",
    "joblib",
    "pydantic",
    "pydantic_settings",
    "email_validator",  
    "mcp_odoo",
    "langgraph", 
    "langchain_core"
]

# Definir variables de entorno dummy para que Pydantic no falle al importar
os.environ['ODOO_URL'] = 'http://dummy-url'
os.environ['ODOO_DB'] = 'dummy-db'
os.environ['ODOO_USERNAME'] = 'dummy-user'
os.environ['ODOO_PASSWORD'] = 'dummy-password'
# -------------------------------
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

# comando para actualizar: sphinx-apidoc -f -o docs src

sys.path.insert(0, os.path.abspath('..')) # Directorio del código fuente

project = 'B2B invoice prediction AI agent'
copyright = '2025, Ismael Fernandez Zarza'
author = 'Ismael Fernandez Zarza'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Necesario para Google style docstrings
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'es'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme' # Cambiado
html_static_path = ['_static']
