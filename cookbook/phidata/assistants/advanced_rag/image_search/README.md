# Phidata Assistant Image Search with CLIP Embeddings stored in Pinecone

## Introduction

This project demonstrates a powerful AI stack that combines CLIP (Contrastive Language-Image Pre-training) for image and text embeddings with Pinecone vector database for efficient similarity search. It also integrates a Phidata Assistant powered by GPT-4 for intelligent query processing. This system enables semantic search on images using natural language queries, with the added intelligence of an AI assistant to interpret and refine search results.

The project consists of four main components:
1. Downloading and generating images using DALL-E
2. Creating image embeddings and upserting them to Pinecone
3. Generating text embeddings using CLIP
4. Querying Pinecone using text embeddings for similar images, enhanced by a Phidata Assistant

## Setup

1. Install Python 3.10 or higher

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
export PINECONE_API_KEY=YOUR_PINECONE_API_KEY
export OPENAI_API_KEY=YOUR_OPENAI_API_KEY
```

## Usage

Run the following scripts in order:

1. Generate and download images:
```bash
python 01_download_images.py
```

2. Create image embeddings and upsert to Pinecone:
```bash
python 02_upsert_pinecone.py
```

3. Run the Phidata Assistant for intelligent image search:
```bash
python 03_assistant_search.py
```

## Script Descriptions

- `01_download_images.py`: Uses DALL-E to generate images based on prompts and downloads them.
- `02_upsert_pinecone.py`: Creates CLIP embeddings for the downloaded images and upserts them to Pinecone.
- `03_assistant_search.py`: Implements the Phidata Assistant with integrated Pinecone search functionality.

## Phidata Assistant and Search Function

The `03_assistant_search.py` script includes:

- A `search` function that converts text queries to CLIP embeddings and searches the Pinecone index.
- Integration with the Phidata Assistant, which uses GPT-4 to process queries and interpret search results.

Example usage:

```python
assistant.print_response("Cheeseburger", markdown=True)
```

This will use the Phidata Assistant to search for images related to "Cheeseburger" and provide an intelligent interpretation of the results.

## Notes

- Ensure you have sufficient credits and permissions for the OpenAI API (for DALL-E image generation and GPT-4) and Pinecone.
- The Pinecone index should be set up with the correct dimensionality (512 for CLIP ViT-B/32 embeddings).
- Adjust the number and type of images generated in `01_download_images.py` as needed.
- The Phidata Assistant uses GPT-4 to provide intelligent responses. Adjust the model and parameters in `03_assistant_search.py` if needed.
- You can modify the search function or assistant integration for different use cases or to incorporate into other applications.