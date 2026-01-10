import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain.embeddings import OpenAIEmbeddings

load_dotenv()
api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key)

# Set your index name
index_name = "dispatch"

# Create or connect to index
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,  # Adjust based on your embedding model
        metric="cosine",
        spec={
            "serverless": {
                "cloud": "aws",
                "region": "us-east-1"
            }
        }
    )

index = pc.Index(index_name)

# Initialize embeddings (you may need to add OpenAI API key to .env)
embeddings = OpenAIEmbeddings()

# Create vector store
vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings,
    text_key="text"
)