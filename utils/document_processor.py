import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_file):
    """Extracts text from a loaded PDF file"""
    text = ""
    try:
        # Read bytes from the Streamlit UploadedFile
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None