import torch  # type: ignore
import clip  # type: ignore
from pinecone import Pinecone  # type: ignore
import os
import json

from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

# Load the CLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = "my-image-index"  # Make sure this matches your Pinecone index name in 02_upsert_pinecone.py
index = pc.Index(index_name)


def get_text_embedding(text):
    """Get embedding for the text."""
    text_input = clip.tokenize([text]).to(device)

    with torch.no_grad():
        text_features = model.encode_text(text_input)

    return text_features.cpu().numpy()[0]


def search(query_text, top_k=5):
    """
    Search for an image using keywords

    query_text: str
    top_k: int

    Returns:
    json: a list of dictionaries with the filename and score

    Example:
    search("Cheesburger")
    """
    query_embedding = get_text_embedding(query_text)

    query_response = index.query(
        namespace="image-embeddings",
        vector=query_embedding.tolist(),
        top_k=top_k,
        include_values=False,
        include_metadata=True,
    )
    res = query_response["matches"]
    location = [i["metadata"]["filename"] for i in res]
    score = [i["score"] for i in res]
    return json.dumps([dict(zip(location, score))])


assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o", max_tokens=500, temperature=0.3),
    tools=[search],
    instructions=[
        "Query the Pinecone index for images related to the given text. Which image best matches what the user is looking for? Provide the filename and score."
    ],
    show_tool_calls=True,
)

assistant.print_response("Cheesburger", markdown=True)
