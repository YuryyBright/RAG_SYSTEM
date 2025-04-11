# app/core/templates.py
import os
from fastapi.templating import Jinja2Templates

# Move two levels up from the current file (__file__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
