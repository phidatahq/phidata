from phi.tools.image_to_image_search import ImageSearcher
import pandas as pd


def load_images_to_vector_db(csv_file_path, limit=30):
    # Initialize the image searcher
    image_searcher = ImageSearcher()
    
    # Load the dataset
    df = pd.read_csv(csv_file_path)
    
    # Extract first 30 valid image URLs
    image_urls = df['img'].dropna().head(limit).tolist()
    
    # Add images to the vector database with progress tracking
    image_searcher.add_images(image_urls, clear_existing=True, show_progress=True)
    
    return image_searcher


def search_image():
    # Load images and get searcher
    image_searcher = ImageSearcher()

    # image_searcher = load_images_to_vector_db("FashionDataset.csv", limit=30)
    
    # Search with a query image
    query_image = "http://assets.myntassets.com/assets/images/12413214/2021/11/22/bb925efb-80d9-4cb6-838c-df86f1ba3c3e1637570416652-Varanga-Women-Mustard-Yellow-Floral-Yoke-Embroidered-Straigh-1.jpg"
    similar_images = image_searcher.search_similar_images(query_image, limit=10)
    
    # Print results
    print("\nSimilar images found:")
    for i, img in enumerate(similar_images, 1):
        print(f"\n{i}. URL: {img['url']}")
        print(f"   Type: {img['type']}")
        print(f"   Similarity: {img['similarity']:.4f}")


if __name__ == "__main__":
    search_image()
