import streamlit as st

st.set_page_config(page_title="Interview Prep", layout="wide")

st.title("Interview Preparation")

if not st.session_state.get("cv_text"):
    st.warning("Please upload your CV on the Home page first to personalize your interview prep.")
    if st.button("Go to Home"):
        st.switch_page("app.py")
else:
    st.info("CV context loaded. Generating mock interview questions...")
    # Здесь будет логика генерации вопросов на основе опыта в CV