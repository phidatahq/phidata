# Import necessary modules
from phi.assistant import Assistant
from phi.knowledge.langchain import LangChainKnowledgeBase
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
import pathlib

# Define the directory where the Chroma database is located
chroma_db_dir = pathlib.Path("./chroma_db")

# Define the path to the document to be loaded into the knowledge base
state_of_the_union = pathlib.Path("data/demo/state_of_the_union.txt")

# Load the document
raw_documents = TextLoader(str(state_of_the_union)).load()

# Split the document into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
documents = text_splitter.split_documents(raw_documents)

# Embed each chunk and load it into the vector store
Chroma.from_documents(documents, OpenAIEmbeddings(), persist_directory=str(chroma_db_dir))

# Get the vector database
db = Chroma(embedding_function=OpenAIEmbeddings(), persist_directory=str(chroma_db_dir))

# Create a retriever from the vector store
retriever = db.as_retriever()

# Create a knowledge base from the vector store
knowledge_base = LangChainKnowledgeBase(retriever=retriever)

# Create an assistant with the knowledge base
assistant = Assistant(knowledge_base=knowledge_base, add_references_to_prompt=True)

# Use the assistant to ask a question and print a response.
assistant.print_response("What did the president say about technology?", markdown=True)
