@echo off
start https://github.com/tutumomo/phidata
start https://github.com/tutumomo/phidata-docs
pause

git pull 

call ac
pip install -U phidata jupyter-ai ipywidgets ollama duckduckgo-search langchain-google-genai unstructured pyowm tools wikipedia yfinance sec-api tiktoken faiss-cpu python-dotenv langchain-community langchain-core openai arxiv

if not exist phidata-docs (
   git clone https://github.com/tutumomo/phidata-docs.git
) else (
   cd phidata-docs
   git pull
   cd ..
)

pause
