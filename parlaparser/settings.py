import os
from datetime import datetime


API_AUTH = (os.getenv('PARSER_USER', 'parser'), os.getenv('PARSER_PASSWORD', 'parsernedela'))
API_URL = os.getenv('PARSER_PARLADATA_API_URL', 'http://localhost:8000/v3')
MAIN_ORG_ID = os.getenv('PARSER_MAIN_ORG_ID', '503')
MANDATE = os.getenv('PARSER_MANDATE_ID', '1')
