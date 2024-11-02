"""Example for Qdrant FastEmbed"""

from fastembed import TextEmbedding # type: ignore
from typing import List

documents: List[str] = [
    "This classic spaghetti carbonara combines perfectly cooked al dente pasta",
    "with crispy pancetta, which adds a savory crunch and depth of flavor,",
    "creamy eggs that create a luscious sauce when mixed with the hot pasta,",
    "and a generous sprinkle of freshly grated Parmesan cheese",
    "for a comforting, flavorful dish that's sure to impress any pasta lover.",
    "Finish with a dash of black pepper and a garnish of parsley for a touch of freshness.",
]

"""FastEmbed supported models can be found here: https://qdrant.github.io/fastembed/examples/Supported_Models/"""

# Initialize the TextEmbedding model
model = TextEmbedding(model="BAAI/bge-small-en-v1.5")

embeddings = list(model.embed(documents))
print(embeddings[0])
