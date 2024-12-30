from phi.tools.openclip_embedder import OpenClipEmbedder
from phi.vectordb.chroma import ChromaDb
from phi.document import Document
from typing import List
import numpy as np

class ImageSearcher:
    def __init__(self):
        self.embeddings = OpenClipEmbedder()        
        self.vector_db = ChromaDb(
            collection="image_collection",
            embedder=self.embeddings,
            path="tmp/image_db",
            persistent_client=True
        )        
        self.vector_db.create()
    
    def add_images(self, image_urls: List[str], clear_existing: bool = False, show_progress: bool = False):
        """Add images to the vector database"""
        if clear_existing:
            self.vector_db.drop()
            self.vector_db.create()
        
        image_docs = []
        total = len(image_urls)
        
        for i, url in enumerate(image_urls):
            if show_progress:
                print(f"Processing image {i+1}/{total}: {url}")
            
            doc = Document(
                content=url,
                name=f"image_{i}",
                # meta_data={"type": url.split('/')[-1].split('_')[0]}
            )
            image_docs.append(doc)
        
        self.vector_db.insert(image_docs)
        print(f"Added {len(image_docs)} images to the database")
    
    def search_similar_images(self, query_image_url: str, limit: int = 5) -> List[dict]:
        """Search for similar images given a query image URL"""
        # Get embedding for query image
        self.embeddings.load_model()
        query_embedding = self.embeddings.get_image_embeddings(query_image_url)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)  # Normalize
        
        # Use ChromaDB's built-in query
        results = self.vector_db._collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=['embeddings', 'documents', 'distances']
        )
        
        # Process results
        similar_images = []
        for doc_content, distance in zip(results['documents'][0], results['distances'][0]):
            # Calculate similarity (ensure correct conversion)
            similarity = 1 - distance  # For normalized embeddings
            similar_images.append({
                'url': doc_content,
                'similarity': similarity,
                'type': doc_content.split('/')[-1].split('_')[0],
                'query_embedding': query_embedding,
                'doc_embedding': results['embeddings'][0][0]    
            })
        
        # Sort by similarity (higher is better)
        similar_images.sort(key=lambda x: x['similarity'], reverse=True)

        # Debugging: Print sorted results
        # for img in similar_images:
        #     print(f"URL: {img['url']}, Similarity: {img['similarity']:.4f}")
        
        return similar_images[:limit]
