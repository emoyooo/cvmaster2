import streamlit as st
from utils.document_processor import extract_text_from_pdf

st.set_page_config(page_title="AI Career Hub", layout="wide")

# Инициализация session_state для хранения текста CV
if "cv_text" not in st.session_state:
    st.session_state["cv_text"] = None

st.title("AI Career Hub")
st.write("Analyze your resume, find career matches, and prepare for interviews based on O*NET data.")

# Секция загрузки CV
st.subheader("Upload your Resume")
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("Extracting text from PDF..."):
        text = extract_text_from_pdf(uploaded_file)
        if text:
            st.session_state["cv_text"] = text
            st.success("CV uploaded and processed successfully!")
        else:
            st.error("Failed to extract text from PDF. Please try another file.")

# Навигационные кнопки
st.divider()
st.subheader("Fast Navigation")

col1, col2 = st.columns(2)

with col1:
    if st.button("Go to CV Analyzer", use_container_width=True):
        st.switch_page("pages/1_CV_Analyzer.py")

with col2:
    if st.button("Go to Interview Prep", use_container_width=True):
        st.switch_page("pages/2_Interview_Preparation.py")

if st.session_state["cv_text"]:
    with st.expander("Preview Extracted Text"):
        st.text(st.session_state["cv_text"][:1000] + "...")