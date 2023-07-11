from pathlib import Path
from typing import List, Iterable

from phi.document.base import Document
from phi.utils.log import logger


def load_pdfs_from_dir(dir: Path) -> List[Document]:
    """Read data from a PDF and return a list of Documents"""

    logger.info(f"Reading PDFs in: {dir}")
    pdfs_to_read: List[Path] = []
    for pdf in dir.glob("*.pdf"):
        pdfs_to_read.append(pdf)
    logger.info(f"Found {len(pdfs_to_read)} PDFs to read")

    loaded_pdfs: List[Iterable[Document]] = []
    for pdf in pdfs_to_read:
        loader = PyPDFLoader(str(pdf))
        # Load the PDF document
        document = loader.load()
        # Add the loaded document to the list
        loaded_pdfs.append(document)
        logger.info(f"Loaded: {str(pdf)}")

    # Create list of chunked loaded pdfs
    chunked_pdfs: List[List[Document]] = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    for loaded_pdf in loaded_pdfs:
        # Chunk the loaded pdf
        texts = text_splitter.split_documents(loaded_pdf)
        # Add the chunks to chunked_pdfs
        chunked_pdfs.append(texts)
        logger.info(f"Chunked PDF length: {len(texts)}")

    flat_chunked_pdf = [item for sublist in chunked_pdfs for item in sublist]
    return flat_chunked_pdf
