from phi.tools import Toolkit
from PIL import Image
import requests
from io import BytesIO
import numpy as np

try:
    import open_clip
except ImportError:
    raise ImportError("`open-clip-torch` is not installed. Please install using `pip install open-clip-torch`")

class OpenClipEmbedder(Toolkit):
    def __init__(self, model: str = "hf-hub:laion/CLIP-ViT-g-14-laion2B-s12B-b42K"):
        super().__init__(name="openai_embeddings")
        self.model_name = model  # For storing the original model name for tokenizer to use.
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.register(self.load_model)
        self.register(self.get_text_embeddings)
        self.register(self.get_image_embeddings)

    def load_model(self):
        if self.model is None:
            self.model, self.preprocess = open_clip.create_model_from_pretrained(self.model_name)
            self.tokenizer = open_clip.get_tokenizer(self.model_name)

    def get_embedding_and_usage(self, text: str):
        """Required method for phi.document.Document compatibility"""
        if isinstance(text, str):
            embedding = self.get_text_embeddings(text)
        return embedding.tolist(), {"total_tokens": 0}  # Mock usage stats

    def get_embedding(self, text: str):
        """Required method for phi.vectordb compatibility"""
        embedding, _ = self.get_embedding_and_usage(text)
        return embedding

    def get_text_embeddings(self, text: str) -> np.ndarray:
        self.load_model()
        text_tokens = self.tokenizer([text])
        text_embeddings = self.model.encode_text(text_tokens)
        return text_embeddings.detach().cpu().numpy()[0]
    
    def get_image_embeddings(self, image_url: str) -> np.ndarray:
        self.load_model()
        # Load image from URL
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))
        # Preprocess and get embeddings
        image_input = self.preprocess(image).unsqueeze(0)
        image_embeddings = self.model.encode_image(image_input)
        return image_embeddings.detach().cpu().numpy()[0]
    
    