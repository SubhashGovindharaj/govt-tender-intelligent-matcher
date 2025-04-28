import os
from typing import Dict, List, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessagesState
import logging
from agents.tender_scraper_agent import TenderScraperAgent
from agents.company_scraper_agent import CompanyScraperAgent
from utils.config import CompanySchema, RecommendationSchema

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the state for our LangGraph
class GraphState(TypedDict):
    # User inputs
    input_type: str  # "company_profile" or "scrape_tenders"
    profile_text: str
    file_content: bytes
    file_type: str
    
    # Processing states
    scraping_status: Dict[str, Any]
    company_profile: Dict[str, Any]
    
    # Results
    recommendations: List[Dict[str, Any]]
    error: str

def initialize_agents() -> tuple:
    """Initialize the tender and company agents"""
    tender_agent = TenderScraperAgent()
    company_agent = CompanyScraperAgent()
    return tender_agent, company_agent

# Define graph nodes (functions)
def route_request(state: GraphState) -> str:
    """Route the request based on input type"""
    logger.info(f"Routing request with input_type: {state.get('input_type')}")
    
    if state.get("input_type") == "scrape_tenders":
        return "scrape_tenders"
    elif state.get("input_type") == "company_profile":
        return "process_company_profile"
    else:
        state["error"] = "Invalid input type. Must be 'scrape_tenders' or 'company_profile'."
        return END

def scrape_tenders(state: GraphState) -> GraphState:
    """Node for scraping tenders"""
    logger.info("Starting tender scraping process")
    tender_agent, _ = initialize_agents()
    
    try:
        result = tender_agent.scrape_and_store_tenders()
        state["scraping_status"] = result
        
        if result.get("status") == "error":
            state["error"] = result.get("message", "Unknown error during tender scraping")
    except Exception as e:
        logger.error(f"Error in scrape_tenders: {str(e)}")
        state["error"] = f"Error scraping tenders: {str(e)}"
        state["scraping_status"] = {"status": "error", "message": str(e)}
    
    return state

def process_company_profile(state: GraphState) -> GraphState:
    """Node for processing company profile and finding matching tenders"""
    logger.info("Processing company profile")
    _, company_agent = initialize_agents()
    
    try:
        result = company_agent.process_company_profile(
            profile_text=state.get("profile_text"),
            file_content=state.get("file_content"),
            file_type=state.get("file_type")
        )
        
        if result.get("status") == "success":
            state["company_profile"] = result.get("company_info", {})
            state["recommendations"] = result.get("recommendations", [])
        else:
            state["error"] = result.get("message", "Unknown error processing company profile")
    except Exception as e:
        logger.error(f"Error in process_company_profile: {str(e)}")
        state["error"] = f"Error processing company profile: {str(e)}"
    
    return state

# Build the LangGraph
def build_graph() -> StateGraph:
    """Build the LangGraph for the tender matching system"""
    # Initialize the graph
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("route_request", route_request)
    graph.add_node("scrape_tenders", scrape_tenders)
    graph.add_node("process_company_profile", process_company_profile)
    
    # Add conditional edges
    graph.add_conditional_edges(
        "route_request",
        lambda x: x,
        {
            "scrape_tenders": "scrape_tenders",
            "process_company_profile": "process_company_profile",
            END: END
        }
    )
    
    # Define terminal nodes (both paths end after processing)
    graph.add_edge("scrape_tenders", END)
    graph.add_edge("process_company_profile", END)
    
    # Set the entry point
    graph.set_entry_point("route_request")
    
    return graph

def get_tender_matching_graph() -> StateGraph:
    """Get the initialized LangGraph"""
    return build_graph()