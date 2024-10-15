from pathlib import Path
from openai import OpenAI
import httpx

# Set up the OpenAI client
client = OpenAI()

# Set up the data directory
data_dir = Path(__file__).parent.parent.parent.joinpath("wip", "data", "generated_images")
data_dir.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist


def generate_and_download_image(prompt, filename):
    # Generate image
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    print(f"Generated image URL: {image_url}")

    # Download image
    if image_url is not None:
        image_response = httpx.get(image_url)
    else:
        # Handle the case where image_url is None
        return "No image URL available"

    if image_response.status_code == 200:
        file_path = data_dir.joinpath(filename)
        with open(file_path, "wb") as file:
            file.write(image_response.content)
        print(f"Image downloaded and saved as {file_path}")
    else:
        print("Failed to download the image")


# Example usage
generate_and_download_image("a white siamese cat", "siamese_cat.png")
generate_and_download_image("a saint bernard", "saint_bernard.png")
generate_and_download_image("a cheeseburger", "cheeseburger.png")
generate_and_download_image("a snowy mountain landscape", "snowy_mountain.png")
generate_and_download_image("a busy city street", "busy_city_street.png")
