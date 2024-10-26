import os
from phi.document.reader.firecrawl_reader import FirecrawlReader


api_key = os.getenv("FIRECRAWL_API_KEY")
if not api_key:
    raise ValueError("FIRECRAWL_API_KEY environment variable is not set")


reader = FirecrawlReader(
    api_key=api_key,
    mode="scrape",
    chunk=True,
    # params={
    #     # "timeout": 30000  # Just timeout for now
    #     'limit': 5,
    #     'scrapeOptions': {'formats': ['markdown']}
    # }
    params={"formats": ["markdown"]},
)

try:
    print("Starting scrape...")
    documents = reader.read("https://github.com/phidatahq/phidata")

    if documents:
        for doc in documents:
            print(doc.name)
            print(doc.content)
            print(f"Content length: {len(doc.content)}")
            print("-" * 80)
    else:
        print("No documents were returned")

except Exception as e:
    print(f"Error type: {type(e)}")
    print(f"Error occurred: {str(e)}")
