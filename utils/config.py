import pathlib
import streamlit as st

try:
    import tomllib
except ImportError:
    import tomli as tomllib

def get_secrets():
    try:
        if st.secrets and "OPENAI_API_KEY" in st.secrets:
            return st.secrets
    except:
        pass
    path = pathlib.Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if path.exists():
        with open(path, "rb") as f:
            return tomllib.load(f)
    raise FileNotFoundError("Secrets not found")

secrets = get_secrets()

OPENAI_API_KEY = secrets["OPENAI_API_KEY"]
SUPABASE_URL = secrets["SUPABASE_URL"]
SUPABASE_KEY = secrets["SUPABASE_KEY"]

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"