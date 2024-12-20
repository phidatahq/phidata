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

3. **Install Dependencies:**

   Ensure you have Python installed, then run:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the Workflow:**

   Modify the `config.yaml` file to include your social media platform credentials and preferences.

5. **Run the Workflow:**

   Execute the main script to start the content creation process:

   ```bash
   python social_media_content_planner.py
   ```

## Customization

The workflow is designed to be flexible. You can adjust the llm model parameters, content templates, and scheduling settings within the configuration files to better suit your needs.

## Contributing

We welcome contributions to enhance this workflow. Please fork the repository, create a new branch for your feature or bug fix, and submit a pull request for review.
