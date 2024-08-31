import os
from typing import List
import streamlit as st
import nest_asyncio
from phi.document.reader.pdf import PDFReader
from phi.document.reader.text import TextReader
from phi.document.reader.docx import DocxReader
from phi.document.reader.csv_reader import CSVReader
from pathlib import Path

# Initialize necessary configurations
nest_asyncio.apply()

# Streamlit app setup
st.set_page_config(page_title="Document Viewer")
st.title("Document Viewer")

def display_document_content(documents: List):
    for document in documents:
        st.text_area(label="Document Contents", value=document, height=300)

def read_document(file_path: Path):
    file_type = file_path.suffix.lower()
    reader = None

    if file_type == ".pdf":
        reader = PDFReader()
    elif file_type == ".csv":
        reader = CSVReader()
    elif file_type == ".txt":
        reader = TextReader()
    elif file_type == ".docx":
        reader = DocxReader()

    if reader:
        return reader.read(file_path)
    else:
        st.error(f"Unsupported file type: {file_type}")
        return None

def main() -> None:
    st.sidebar.markdown("### Upload a Document or Enter a File Path")
    
    # File uploader option
    uploaded_files = st.sidebar.file_uploader(
        "Add Documents", type=["pdf", "csv", "txt", "docx"], accept_multiple_files=True
    )

    # File path option
    file_path = st.sidebar.text_input("Or enter a file path:")

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_type = uploaded_file.name.split(".")[-1].lower()
            reader = None
            content = None
            
            if file_type == "pdf":
                reader = PDFReader()
            elif file_type == "csv":
                reader = CSVReader()
            elif file_type == "txt":
                reader = TextReader()
            elif file_type == "docx":
                reader = DocxReader()

            if reader:
                documents = reader.read(uploaded_file)
                if documents:
                    content = "\n\n".join([doc.content for doc in documents])
                else:
                    st.sidebar.error(f"Could not read {file_type} file")

            if content:
                st.subheader(f"Contents of {uploaded_file.name}:")
                st.text_area(label="Document Contents", value=content, height=300)

    elif file_path:
        path = Path(file_path)
        if path.exists() and path.is_file():
            documents = read_document(path)
            if documents:
                content = "\n\n".join([doc.content for doc in documents])
                st.subheader(f"Contents of {path.name}:")
                st.text_area(label="Document Contents", value=content, height=300)
        else:
            st.error("File not found or path is invalid.")

main()
