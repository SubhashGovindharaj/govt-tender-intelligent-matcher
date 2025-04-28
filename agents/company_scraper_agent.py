import os
import numpy as np
from typing import List, Dict, Any, Optional, Union
import json
import logging
import requests
from PyPDF2 import PdfReader
import faiss
import pickle
from utils.config import (
    CompanySchema, 
    TenderSchema, 
    RecommendationSchema,
    VECTOR_DB_PATH, 
    OLLAMA_HOST, 
    OLLAMA_MODEL,
    OLLAMA_EMBEDDING_MODEL
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompanyScraperAgent:
    """Agent for processing company profiles and finding matching tenders"""
    
    def __init__(self):
        self.ollama_host = OLLAMA_HOST
        self.llm_model = OLLAMA_MODEL
        self.embedding_model = OLLAMA_EMBEDDING_MODEL
        
        # Load index and tenders
        self._load_index_and_tenders()
    
    def _load_index_and_tenders(self):
        """Load the FAISS index and tenders"""
        index_path = os.path.join(VECTOR_DB_PATH, "faiss_index.bin")
        tenders_path = os.path.join(VECTOR_DB_PATH, "tenders.pkl")
        
        # Load tenders
        if os.path.exists(tenders_path):
            try:
                with open(tenders_path, 'rb') as f:
                    self.tenders = pickle.load(f)
                logger.info(f"Loaded {len(self.tenders)} tenders")
            except Exception as e:
                logger.error(f"Error loading tenders: {str(e)}")
                self.tenders = []
        else:
            logger.warning("No tenders file found")
            self.tenders = []
        
        # Load FAISS index
        if os.path.exists(index_path):
            try:
                self.index = faiss.read_index(index_path)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error loading FAISS index: {str(e)}")
                self.index = None
        else:
            logger.warning("No FAISS index found")
            self.index = None
    
    def process_company_profile(self, 
                               profile_text: str = None, 
                               file_content: bytes = None, 
                               file_type: str = None) -> Dict[str, Any]:
        """Process company profile from text or file and find matching tenders"""
        try:
            # Extract company information
            company_info = self._extract_company_info(profile_text, file_content, file_type)
            
            # Generate embedding for the company profile
            company_embedding = self.get_embedding(company_info.description)
            company_info.embedding = company_embedding
            
            # Find matching tenders
            recommendations = self._find_matching_tenders(company_info)
            
            return {
                "status": "success",
                "company_info": company_info.model_dump(exclude={"embedding"}),
                "recommendations": [rec.model_dump(exclude={"tender_details.embedding"}) for rec in recommendations]
            }
        
        except Exception as e:
            logger.error(f"Error processing company profile: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing company profile: {str(e)}",
                "recommendations": []
            }
    
    def _extract_company_info(self, 
                             profile_text: Optional[str] = None, 
                             file_content: Optional[bytes] = None,
                             file_type: Optional[str] = None) -> CompanySchema:
        """Extract company information from text or uploaded file"""
        text = ""
        
        # Extract text from file if provided
        if file_content and file_type:
            if file_type == "pdf":
                # Extract text from PDF
                reader = PdfReader(file_content)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            elif file_type == "txt":
                # Extract text from TXT
                text = file_content.decode("utf-8")
            elif file_type == "docx":
                # Would need python-docx library for DOCX files
                raise NotImplementedError("DOCX processing not implemented")
        elif profile_text:
            text = profile_text
        else:
            raise ValueError("No company profile provided")
        
        # Use Ollama to extract structured company information
        prompt = f"""
        Extract key company information from the following text:
        
        {text}
        
        Output the following fields in JSON format:
        1. name: Company name
        2. description: Comprehensive company description
        3. services: List of services offered
        4. capabilities: List of company capabilities
        5. expertise: List of company expertise areas
        
        JSON format only, no explanation.
        """
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={"model": self.llm_model, "prompt": prompt, "stream": False}
            )
            
            if response.status_code != 200:
                logger.error(f"Error extracting company info: {response.text}")
                # Fallback to basic extraction
                return self._basic_company_extraction(text)
            
            result = response.json()
            company_json_text = result.get("response", "")
            
            # Extract JSON from the response
            import re
            json_match = re.search(r'```json(.*?)```', company_json_text, re.DOTALL)
            if json_match:
                company_json_text = json_match.group(1).strip()
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'({.*})', company_json_text, re.DOTALL)
                if json_match:
                    company_json_text = json_match.group(1).strip()
            
            # Parse JSON
            company_data = json.loads(company_json_text)
            
            # Create CompanySchema
            return CompanySchema(
                name=company_data.get("name", "Unknown Company"),
                description=company_data.get("description", text[:500]),
                services=company_data.get("services", []),
                capabilities=company_data.get("capabilities", []),
                expertise=company_data.get("expertise", [])
            )
        
        except Exception as e:
            logger.error(f"Error processing company info with LLM: {str(e)}")
            # Fallback to basic extraction
            return self._basic_company_extraction(text)
    
    def _basic_company_extraction(self, text: str) -> CompanySchema:
        """Basic extraction of company information when LLM extraction fails"""
        # Simple extraction of company name (first line or "Unknown")
        lines = text.strip().split('\n')
        name = lines[0] if lines else "Unknown Company"
        
        # Use first 500 chars as description
        description = text[:500] if len(text) > 500 else text
        
        # Basic keyword extraction for services (very simplistic)
        keywords = ["service", "provide", "offer", "solution", "product", "capability", "expertise"]
        services = []
        capabilities = []
        expertise = []
        
        for line in lines:
            line = line.lower()
            if any(keyword in line for keyword in keywords):
                if "service" in line or "provide" in line or "offer" in line:
                    services.append(line.strip())
                elif "capability" in line:
                    capabilities.append(line.strip())
                elif "expertise" in line or "specialize" in line:
                    expertise.append(line.strip())
        
        return CompanySchema(
            name=name,
            description=description,
            services=services[:5] if services else ["General services"],
            capabilities=capabilities[:5] if capabilities else ["General capabilities"],
            expertise=expertise[:5] if expertise else ["General expertise"]
        )
    
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
                return [0.0] * 384  # Default embedding size
                
            result = response.json()
            return result.get("embedding", [0.0] * 384)
        except Exception as e:
            logger.error(f"Error in get_embedding: {str(e)}")
            return [0.0] * 384
    
    def _find_matching_tenders(self, company_info: CompanySchema, top_k: int = 10) -> List[RecommendationSchema]:
        """Find matching tenders for a company profile using similarity search"""
        if not self.index or not self.tenders or self.index.ntotal == 0:
            logger.warning("No tenders or index available for matching")
            return []
        
        try:
            # Convert embedding to numpy array
            query_vector = np.array([company_info.embedding]).astype('float32')
            
            # Perform similarity search
            distances, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
            
            # Create recommendation objects
            recommendations = []
            for i in range(len(indices[0])):
                idx = indices[0][i]
                distance = distances[0][i]
                
                if idx < len(self.tenders):
                    tender = self.tenders[idx]
                    
                    # Convert distance to similarity score (0-100%)
                    # Lower distance = higher similarity
                    similarity_score = max(0, min(100, (1.0 - distance/10) * 100))
                    
                    recommendation = RecommendationSchema(
                        tender_id=tender.id,
                        tender_title=tender.title,
                        similarity_score=similarity_score,
                        tender_details=tender
                    )
                    recommendations.append(recommendation)
            
            # Sort by similarity score (highest first)
            recommendations.sort(key=lambda x: x.similarity_score, reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error finding matching tenders: {str(e)}")
            return []