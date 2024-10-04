import os
from pathlib import Path
from typing import List, Tuple, Dict, Any

import torch
from PIL import Image
from pinecone import Pinecone, ServerlessSpec, Index
import clip

# Load the CLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# Set up the data directory
data_dir = Path(__file__).parent.parent.parent.joinpath("wip", "data", "generated_images")


def create_index_if_not_exists(index_name: str, dimension: int = 512) -> None:
    """Create Pinecone index if it doesn't exist."""
    try:
        pc.describe_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception:
        print(f"Index '{index_name}' does not exist. Creating...")
        pc.create_index(
            name=index_name, dimension=dimension, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-west-2")
        )
        print(f"Index '{index_name}' created successfully.")


def load_image(image_path: Path) -> Image.Image:
    """Load and preprocess the image."""
    return Image.open(image_path)


def get_image_embedding(image_path: Path) -> torch.Tensor:
    """Get embedding for the image."""
    image = preprocess(load_image(image_path)).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image)

    return image_features.cpu().numpy()[0]


def upsert_to_pinecone(index: Index, image_path: Path, id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Get image embedding and upsert to Pinecone."""
    image_embedding = get_image_embedding(image_path)

    # Upsert to Pinecone
    upsert_response = index.upsert(vectors=[(id, image_embedding.tolist(), metadata)], namespace="image-embeddings")
    return upsert_response


# Example usage
if __name__ == "__main__":
    index_name = "my-image-index"
    create_index_if_not_exists(index_name, dimension=512)  # CLIP ViT-B/32 produces 512-dimensional embeddings

    # Get the index after ensuring it exists
    index = pc.Index(index_name)

    # Define image-text pairs (text is now used as metadata)
    image_text_pairs: List[Tuple[str, str]] = [
        ("siamese_cat.png", "a white siamese cat"),
        ("saint_bernard.png", "a saint bernard"),
        ("cheeseburger.png", "a cheeseburger"),
        ("snowy_mountain.png", "a snowy mountain landscape"),
        ("busy_city_street.png", "a busy city street"),
    ]

    for i, (image_filename, description) in enumerate(image_text_pairs):
        image_path = data_dir.joinpath(image_filename)
        id = f"img_{i}"
        metadata = {"description": description, "filename": image_filename}
        try:
            if image_path.exists():
                response = upsert_to_pinecone(index, image_path, id, metadata)
                print(f"Upserted embedding for '{image_filename}' with ID {id}. Response: {response}")
            else:
                print(f"Image file not found: {image_path}")
        except Exception as e:
            print(f"Error processing '{image_filename}': {str(e)}")
