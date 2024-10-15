from pathlib import Path
from shutil import rmtree

import httpx

# Set up the data directory
data_dir = Path(__file__).parent.parent.parent.joinpath("wip", "data", "paul_graham")
if data_dir.is_dir():
    rmtree(path=data_dir, ignore_errors=True)  # Remove existing directory if it exists
data_dir.mkdir(parents=True, exist_ok=True)  # Create the directory

# Download the text file
url = "https://raw.githubusercontent.com/run-llama/llama_index/main/docs/docs/examples/data/paul_graham/paul_graham_essay.txt"
file_path = data_dir.joinpath("paul_graham_essay.txt")
response = httpx.get(url)
if response.status_code == 200:
    with open(file_path, "wb") as file:
        file.write(response.content)  # Save the downloaded content to a file
    print(f"File downloaded and saved as {file_path}")
else:
    print("Failed to download the file")
