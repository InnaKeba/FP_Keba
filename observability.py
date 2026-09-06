"""Налаштування Observability LangSmith для MAS"""
import os
from dotenv import load_dotenv

def setup_observability():
    load_dotenv()

    os.environ['LANGSMITH_TRACING'] = 'true'
    os.environ['LANGSMITH_PROJECT'] = os.getenv('LANGSMITH_PROJECT', 'HW3_MAS_Production')
    
    api_key = os.getenv('LANGSMITH_API_KEY')
    if api_key:
        os.environ['LANGSMITH_API_KEY'] = api_key
        print("Observability: LangSmith tracing is ENABLED.")
    else:
        print("Observability: LANGSMITH_API_KEY не знайдено. Трасування вимкнено.")

if __name__ == "__main__":
    setup_observability()