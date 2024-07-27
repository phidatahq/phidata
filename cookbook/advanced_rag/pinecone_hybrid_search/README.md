# Phidata Pinecone Hybrid Search Example

## Introduction

A powerful AI stack that includes Phidata Assistant, LlamaIndex Advanced RAG, and Pinecone Vector Database.

This empowers the Phidata Assistant a way to search its knowledge base using keywords and semantic search.

## Setup

1. Install Python 3.10 or higher
2. Install the required packages using pip:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3. Set environment variables:
```bash
export PINECONE_API_KEY=YOUR_PINECONE_API_KEY
export OPENAI_API_KEY=YOUR_OPENAI_API_KEY
```
4. Run the following scripts in order:
```bash
python 01_download_text.py
python 02_upsert_pinecone.py
python 03_hybrid_search.py
```