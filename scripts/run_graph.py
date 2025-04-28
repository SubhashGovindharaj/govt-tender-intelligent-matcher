import sys
import os
import argparse
import json
import logging
from typing import Dict, Any, Optional
from graphs.main_graph import get_tender_matching_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run the Tender Matching System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Scrape tenders command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape tenders from government websites")
    
    # Match company profile command
    match_parser = subparsers.add_parser("match", help="Match company profile with tenders")
    match_parser.add_argument("--text", type=str, help="Company profile text")
    match_parser.add_argument("--file", type=str, help="Path to company profile file (PDF, TXT)")
    
    return parser.parse_args()

def read_file_content(file_path: str) -> tuple:
    """Read file content and detect file type"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Detect file type
    file_extension = os.path.splitext(file_path)[1].lower()[1:]
    if file_extension in ["pdf", "txt", "docx"]:
        return content, file_extension
    else:
        raise ValueError(f"Unsupported file type: {file_extension}. Supported types: pdf, txt, docx")

def run_scrape_tenders() -> Dict[str, Any]:
    """Run the tender scraping process"""
    logger.info("Running tender scraping process")
    
    # Initialize the graph
    graph = get_tender_matching_graph()
    
    # Prepare the initial state
    initial_state = {
        "input_type": "scrape_tenders",
        "profile_text": "",
        "file_content": b"",
        "file_type": "",
        "scraping_status": {},
        "company_profile": {},
        "recommendations": [],
        "error": ""
    }
    
    # Execute the graph
    result = graph.invoke(initial_state)
    
    return result

def run_match_company_profile(profile_text: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Run the company profile matching process"""
    logger.info("Running company profile matching process")
    
    # Initialize the graph
    graph = get_tender_matching_graph()
    
    # Process file if provided
    file_content = b""
    file_type = ""
    if file_path:
        try:
            file_content, file_type = read_file_content(file_path)
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return {"error": f"Error reading file: {str(e)}"}
    
    # Prepare the initial state
    initial_state = {
        "input_type": "company_profile",
        "profile_text": profile_text or "",
        "file_content": file_content,
        "file_type": file_type,
        "scraping_status": {},
        "company_profile": {},
        "recommendations": [],
        "error": ""
    }
    
    # Execute the graph
    result = graph.invoke(initial_state)
    
    return result

def display_results(result: Dict[str, Any]):
    """Display the results of the process"""
    if result.get("error"):
        print(f"Error: {result['error']}")
        return
    
    if result.get("scraping_status"):
        status = result["scraping_status"]
        print(f"\nScraping Status: {status.get('status', 'unknown')}")
        print(f"Message: {status.get('message', '')}")
        print(f"Tenders Scraped: {status.get('tender_count', 0)}")
    
    if result.get("company_profile"):
        company = result["company_profile"]
        print("\nCompany Profile:")
        print(f"Name: {company.get('name', '')}")
        print(f"Description: {company.get('description', '')[:100]}...")
        print(f"Services: {', '.join(company.get('services', []))}")
        print(f"Capabilities: {', '.join(company.get('capabilities', []))}")
        print(f"Expertise: {', '.join(company.get('expertise', []))}")
    
    if result.get("recommendations"):
        recs = result["recommendations"]
        print(f"\nFound {len(recs)} matching tenders:")
        for i, rec in enumerate(recs[:10], 1):  # Show top 10
            print(f"\n{i}. {rec.get('tender_title', '')}")
            print(f"   Similarity: {rec.get('similarity_score', 0):.2f}%")
            tender = rec.get("tender_details", {})
            print(f"   Amount: {tender.get('amount', 'N/A')}")
            print(f"   Deadline: {tender.get('deadline', 'N/A')}")
            print(f"   Source: {tender.get('source', 'N/A')}")

def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        if args.command == "scrape":
            result = run_scrape_tenders()
        elif args.command == "match":
            if not args.text and not args.file:
                print("Error: Either --text or --file must be provided")
                return
            result = run_match_company_profile(profile_text=args.text, file_path=args.file)
        else:
            print("Error: Invalid command. Use 'scrape' or 'match'")
            return
        
        display_results(result)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()