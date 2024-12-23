# Content Creator Agent Workflow

The Content Creator Agent Workflow is a multi-agent workflow designed to streamline the process of generating and managing social media content. It assists content creators in planning, creating, and scheduling posts across various platforms.

## Key Features

- **Scraping Blog Posts:** Scrape a blog post and convert it to understandable draft.

- **Automated Content Generation:** Draft engaging posts tailored to your audience.

- **Scheduling and Management:** Allows for efficient scheduling of posts, ensuring a consistent online presence.

- **Platform Integration:** Supports multiple social media platforms for broad outreach (Linkedin and X).

## Getting Started

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/phidatahq/phidata.git
   ```

2. **Navigate to the Workflow Directory:**

   ```bash
   cd phidata/examples/workflows/social-media-content-planner
   ```

3. **Create Virtual Environment**

  ```bash
  python3 -m venv ~/.venvs/aienv
  source ~/.venvs/aienv/bin/activate
  ```

4. **Install Dependencies:**

   Ensure you have Python installed, then run:

   ```bash
   pip install -r requirements.txt
   ```

5. **Set the environment variables**

    Create a .env file to set the API keys for OpenAI, Firecrawl API and Typefully API.

6. **Configure the Workflow:**

   Modify the `config.py` file to include your social media platform credentials and preferences.

7. **Run the Workflow:**

   Execute the main script to start the content creation process:

   ```bash
   python social_media_content_planner.py
   ```

## Customization

The workflow is designed to be flexible. You can adjust the model provider parameters, content templates, and scheduling settings within the configuration files to better suit your needs.
