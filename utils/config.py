import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

# Vector database configuration
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))  # Depends on the embedding model

# Tender sources
TENDER_SOURCES = [
    {
        "name": "Tamil Nadu Tenders",
        "url": "https://tntenders.gov.in/nicgep/app",
        "selector": "table.list_table tr"
    },
    {
        "name": "Maharashtra Tenders", 
        "url": "https://mahatenders.gov.in/nicgep/app",
        "selector": "table.list_table tr"
    },
    {
        "name": "Central Public Procurement Portal",
        "url": "https://eprocure.gov.in/eprocure/app",
        "selector": "div.list-group-item"
    },
    {
        "name": "Government e-Marketplace",
        "url": "https://gem.gov.in/",
        "selector": "div.gem-bidding-card"
    },
    # Add more tender sites as needed
]

# Data schema models
class TenderSchema(BaseModel):
    id: str
    title: str
    description: str
    amount: Optional[float] = None
    deadline: Optional[str] = None
    source: str
    url: str
    category: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    publication_date: Optional[str] = None
    raw_text: str
    embedding: Optional[List[float]] = None

class CompanySchema(BaseModel):
    name: str
    description: str
    services: List[str]
    capabilities: List[str]
    expertise: List[str]
    embedding: Optional[List[float]] = None

class RecommendationSchema(BaseModel):
    tender_id: str
    tender_title: str
    similarity_score: float
    tender_details: TenderSchema

# App configuration
APP_NAME = "Government Tender Intelligent Matcher"
APP_DESCRIPTION = "Match your company profile with relevant government tenders using AI"
APP_VERSION = "0.1.0"

# File upload configuration
ALLOWED_EXTENSIONS = ["pdf", "txt", "docx"]
MAX_UPLOAD_SIZE_MB = 10