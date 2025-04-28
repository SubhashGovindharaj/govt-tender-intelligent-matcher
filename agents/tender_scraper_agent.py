import os
import numpy as np
import faiss
import pickle
import json
import logging
from typing import List, Dict, Any, Optional
from utils.config import TenderSchema, VECTOR_DB_PATH, VECTOR_DIMENSION, OLLAMA_HOST, OLLAMA_EMBEDDING_MODEL
from utils.firecrawl_wrapper import FirecrawlWrapper
import time
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TenderScraperAgent:
    """Agent for scraping tenders from government websites and storing them in a vector database"""
    
    def __init__(self):
        self.scraper = FirecrawlWrapper()
        self.index = None
        self.tenders = []
        self.embedding_model = OLLAMA_EMBEDDING_MODEL
        self.ollama_host = OLLAMA_HOST
        
        # Create data directories if they don't exist
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        os.makedirs(os.path.join(VECTOR_DB_PATH, "raw_tenders"), exist_ok=True)
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama API"""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text}
            )
            
            if response.status_code != 200:
                logger.error(f"Error getting embedding: {response.text}")
                # Return a zero vector as fallback
                return [0.0] * VECTOR_DIMENSION
                
            result = response.json()
            return result.get("embedding", [0.0] * VECTOR_DIMENSION)
        except Exception as e:
            logger.error(f"Error in get_embedding: {str(e)}")
            return [0.0] * VECTOR_DIMENSION
    
    def scrape_and_store_tenders(self) -> Dict[str, Any]:
        """Scrape tenders and store them in vector database"""
        try:
            # Scrape tenders from all sources
            logger.info("Starting tender scraping process")
            scraped_tenders = self.scraper.scrape_all_sources()
            logger.info(f"Scraped {len(scraped_tenders)} tenders")
            
            # Generate embeddings and store tenders
            self._process_and_store_tenders(scraped_tenders)
            
            return {
                "status": "success",
                "message": f"Successfully scraped and stored {len(scraped_tenders)} tenders",
                "tender_count": len(scraped_tenders)
            }
        except Exception as e:
            logger.error(f"Error in scrape_and_store_tenders: {str(e)}")
            return {
                "status": "error",
                "message": f"Error scraping tenders: {str(e)}",
                "tender_count": 0
            }
    
    def _process_and_store_tenders(self, tenders: List[TenderSchema]):
        """Process tenders and store them in vector database"""
        # Load existing index and tenders if they exist
        self._load_index_and_tenders()
        
        embeddings = []
        new_tenders = []
        
        for tender in tenders:
            try:
                # Generate embedding for the tender
                text_for_embedding = f"{tender.title} {tender.description}"
                embedding = self.get_embedding(text_for_embedding)
                
                # Store the embedding in the tender object
                tender.embedding = embedding
                new_tenders.append(tender)
                embeddings.append(embedding)
                
                # Save raw tender data
                self._save_raw_tender(tender)
                
            except Exception as e:
                logger.error(f"Error processing tender {tender.id}: {str(e)}")
        
        if new_tenders:
            # Update the tenders list
            self.tenders.extend(new_tenders)
            
            # Update or create the FAISS index
            self._update_index(embeddings)
            
            # Save updated index and tenders
            self._save_index_and_tenders()
            
            logger.info(f"Processed and stored {len(new_tenders)} new tenders")
    
    def _load_index_and_tenders(self):
        """Load existing index and tenders if they exist"""
        index_path = os.path.join(VECTOR_DB_PATH, "faiss_index.bin")
        tenders_path = os.path.join(VECTOR_DB_PATH, "tenders.pkl")
        
        # Load tenders
        if os.path.exists(tenders_path):
            try:
                with open(tenders_path, 'rb') as f:
                    self.tenders = pickle.load(f)
                logger.info(f"Loaded {len(self.tenders)} existing tenders")
            except Exception as e:
                logger.error(f"Error loading tenders: {str(e)}")
                self.tenders = []
        
        # Load index
        if os.path.exists(index_path):
            try:
                self.index = faiss.read_index(index_path)
                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error loading FAISS index: {str(e)}")
                self.index = None
    
    def _update_index(self, new_embeddings: List[List[float]]):
        """Update the FAISS index with new embeddings"""
        if not new_embeddings:
            return
        
        embeddings_array = np.array(new_embeddings).astype('float32')
        
        if self.index is None:
            # Create a new index
            self.index = faiss.IndexFlatL2(VECTOR_DIMENSION)
            
        # Add new embeddings to the index
        self.index.add(embeddings_array)
        logger.info(f"Updated FAISS index, now contains {self.index.ntotal} vectors")
    
    def _save_index_and_tenders(self):
        """Save the FAISS index and tenders"""
        index_path = os.path.join(VECTOR_DB_PATH, "faiss_index.bin")
        tenders_path = os.path.join(VECTOR_DB_PATH, "tenders.pkl")
        
        # Save FAISS index
        if self.index is not None:
            try:
                faiss.write_index(self.index, index_path)
                logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error saving FAISS index: {str(e)}")
        
        # Save tenders
        try:
            with open(tenders_path, 'wb') as f:
                pickle.dump(self.tenders, f)
            logger.info(f"Saved {len(self.tenders)} tenders")
        except Exception as e:
            logger.error(f"Error saving tenders: {str(e)}")
    
    def _save_raw_tender(self, tender: TenderSchema):
        """Save raw tender data as JSON"""
        try:
            file_path = os.path.join(VECTOR_DB_PATH, "raw_tenders", f"{tender.id}.json")
            
            # Convert TenderSchema to dict
            tender_dict = tender.model_dump()
            # Remove embedding to save space
            tender_dict.pop("embedding", None)
            
            with open(file_path, 'w') as f:
                json.dump(tender_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving raw tender {tender.id}: {str(e)}")