"""
This script demonstrates how to load knowledge from a PDF document and query it using an agent, with MongoDB Atlas as the vector database.  
To use MongoDB Atlas Vector Search, follow these steps:
1. Sign Up for MongoDB Atlas:
   - Visit the MongoDB Atlas website and sign up for a free account.
2. Create a New Cluster:
   - Log in and click "Build a Cluster".
   - Choose the Free Shared Clusters (M0) option.
   - Select your preferred cloud provider and region.
   - Click "Create Cluster".
3. Configure Network Access:
   - Go to "Network Access" in the left-hand menu.
   - Click "Add IP Address". Make sure you can connect to MongoDB Atlas from your local network.
4. Create a Database User:
   - Navigate to "Database Access" in the left-hand menu.
   - Click "Add New Database User".
   - Choose "Password" as the authentication method.
   - Enter a username and password.
   - Assign "Read and write to any database" role.
   - Click "Add User".
5. Obtain the Database Connection URL:
   - Go to "Clusters" and click "Connect" for your cluster.
   - Select "Connect your application".
   - Choose Python as your driver and select your version.
   - Copy the provided connection string and replace `<username>` and `<password>` with your credentials.

Example connection string:
"mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority"

For local development, you can use:
- docker pull mongodb/mongodb-atlas-local
- docker run -p 27017:27017 mongodb/mongodb-atlas-local
- connection string will be "mongodb://localhost/?directConnection=true"
"""
from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
import os
#os.environ["OPENAI_API_KEY"] = ""
from phi.vectordb.mongodb import MongoDBVector
db_url = ""
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=MongoDBVector(collection_name="recipes", db_url=db_url, wait_until_index_ready=60, wait_after_insert=300),
) #adjust wait_after_insert and wait_until_index_ready to your needs
knowledge_base.load(recreate=True)  
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("How to make Thai curry?", markdown=True)