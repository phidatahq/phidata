from phi.tools.image_to_image_search import ImageSearcher

def search_image():
    # Initialize the image searcher
    image_searcher = ImageSearcher()
    
    # Add test images
    image_urls = [
        "http://images.cocodataset.org/val2017/000000039769.jpg",  # cat
        "https://cdn.pixabay.com/photo/2023/08/18/15/02/dog-8198719_1280.jpg",  # dog
    ]
    
    # Add images to database
    image_searcher.add_images(image_urls, clear_existing=True)
    
    # Search with a query image
    query_image = "https://static.vecteezy.com/system/resources/thumbnails/024/646/930/small_2x/ai-generated-stray-cat-in-danger-background-animal-background-photo.jpg"
    similar_images = image_searcher.search_similar_images(query_image, limit=2)
    
    # Print results
    print("\nSimilar images found:")
    for i, img in enumerate(similar_images, 1):
        print(f"\n{i}. URL: {img['url']}")
        print(f"   Type: {img['type']}")
        print(f"   Distance: {img['distance']:.4f}")

if __name__ == "__main__":
    search_image()
