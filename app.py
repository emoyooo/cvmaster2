import streamlit as st
from utils.document_processor import extract_text_from_pdf

st.set_page_config(page_title="cvMaster!", layout="wide")

if "cv_text" not in st.session_state:
    st.session_state["cv_text"] = None

st.title("cvMaster!")

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


col1, col2 = st.columns(2)

with col1:
    if st.button("Analyze your CV", use_container_width=True):
        st.switch_page("pages/1_CV_Analyzer.py")
