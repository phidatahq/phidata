from pathlib import Path
from phi.assistant import Assistant
from phi.knowledge.langchain import LangChainKnowledgeBase

from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma

cookbook_dir = Path("__file__").parent
chroma_db_dir = cookbook_dir.joinpath("storage/chroma_db")


def load_vector_store():
    state_of_the_union = cookbook_dir.joinpath("data/demo/state_of_the_union.txt")
    # -*- Load the document
    raw_documents = TextLoader(str(state_of_the_union)).load()
    # -*- Split it into chunks
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    documents = text_splitter.split_documents(raw_documents)
    # -*- Embed each chunk and load it into the vector store
    Chroma.from_documents(documents, OpenAIEmbeddings(), persist_directory=str(chroma_db_dir))


# -*- Load the vector store
load_vector_store()
# -*- Get the vectordb
db = Chroma(embedding_function=OpenAIEmbeddings(), persist_directory=str(chroma_db_dir))
# -*- Create a retriever from the vector store
retriever = db.as_retriever()

# -*- Create a knowledge base from the vector store
knowledge_base = LangChainKnowledgeBase(retriever=retriever)

conv = Assistant(knowledge_base=knowledge_base, debug_mode=True, add_references_to_prompt=True)
conv.print_response("What did the president say about technology?", markdown=True)
