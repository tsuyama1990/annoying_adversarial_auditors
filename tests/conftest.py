import os

# Set dummy API keys before any tests run, to prevent pydantic-ai from complaining
# during module import and inspection.
os.environ["ANTHROPIC_API_KEY"] = "dummy_key_for_test"
os.environ["GEMINI_API_KEY"] = "dummy_key_for_test"
os.environ["OPENROUTER_API_KEY"] = "dummy_key_for_test"
os.environ["JULES_API_KEY"] = "dummy_key_for_test"
os.environ["E2B_API_KEY"] = "dummy_key_for_test"

# Also set models to dummy values to prevent provider resolution errors
os.environ["AC_CDD_AUDITOR_MODEL"] = "openai:gpt-4o"
os.environ["AC_CDD_QA_ANALYST_MODEL"] = "openai:gpt-4o"
os.environ["AC_CDD_REVIEWER__SMART_MODEL"] = "openai:gpt-4o"
os.environ["AC_CDD_REVIEWER__FAST_MODEL"] = "openai:gpt-3.5-turbo"
