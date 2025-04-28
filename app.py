import streamlit as st
import os
import sys
import time
import logging
import json
from typing import List, Dict, Any, Optional
from io import BytesIO
import tempfile
from scripts.run_graph import run_scrape_tenders, run_match_company_profile
from utils.config import APP_NAME, APP_DESCRIPTION, VECTOR_DB_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_system_status() -> Dict[str, Any]:
    """Check the system status - e.g., if tenders are available"""
    status = {
        "system_ready": True,
        "tender_count": 0,
        "error": None
    }
    
    # Check if vector database exists
    if not os.path.exists(os.path.join(VECTOR_DB_PATH, "faiss_index.bin")) or \
       not os.path.exists(os.path.join(VECTOR_DB_PATH, "tenders.pkl")):
        status["system_ready"] = False
        status["error"] = "No tender database found. Please scrape tenders first."
        return status
    
    # Count tenders in raw_tenders directory
    try:
        tender_dir = os.path.join(VECTOR_DB_PATH, "raw_tenders")
        if os.path.exists(tender_dir):
            tenders = [f for f in os.listdir(tender_dir) if f.endswith('.json')]
            status["tender_count"] = len(tenders)
    except Exception as e:
        logger.error(f"Error counting tenders: {str(e)}")
    
    return status

def run_tender_scraping():
    """Run the tender scraping process"""
    with st.spinner("Scraping government tenders... This may take a few minutes..."):
        try:
            result = run_scrape_tenders()
            return result
        except Exception as e:
            logger.error(f"Error scraping tenders: {str(e)}")
            return {"error": f"Error scraping tenders: {str(e)}"}

def run_company_matching(profile_text: Optional[str] = None, uploaded_file = None):
    """Run the company matching process"""
    file_content = None
    file_type = None
    
    # Handle uploaded file
    if uploaded_file is not None:
        try:
            file_type = uploaded_file.name.split('.')[-1].lower()
            file_content = uploaded_file.getvalue()
        except Exception as e:
            logger.error(f"Error processing uploaded file: {str(e)}")
            return {"error": f"Error processing uploaded file: {str(e)}"}
    
    with st.spinner("Matching your company profile with relevant tenders..."):
        try:
            if file_content:
                # Create temporary file for processing
                with tempfile.NamedTemporaryFile(suffix=f'.{file_type}', delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_filepath = temp_file.name
                
                try:
                    result = run_match_company_profile(profile_text=profile_text, file_path=temp_filepath)
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_filepath):
                        os.unlink(temp_filepath)
            else:
                result = run_match_company_profile(profile_text=profile_text)
            
            return result
        except Exception as e:
            logger.error(f"Error matching company profile: {str(e)}")
            return {"error": f"Error matching company profile: {str(e)}"}

def display_tender_details(tender: Dict[str, Any]):
    """Display detailed information about a tender"""
    st.subheader(tender.get("title", "Unknown Tender"))
    
    # Format amount as currency if available
    amount = tender.get("amount")
    if amount:
        amount_str = f"₹{amount:,.2f}" if isinstance(amount, (int, float)) else str(amount)
    else:
        amount_str = "Not specified"
    
    # Display tender info in columns
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Amount:** {amount_str}")
        st.markdown(f"**Source:** {tender.get('source', 'Unknown')}")
        st.markdown(f"**Category:** {tender.get('category', 'Not specified')}")
    
    with col2:
        st.markdown(f"**Deadline:** {tender.get('deadline', 'Not specified')}")
        st.markdown(f"**Department:** {tender.get('department', 'Not specified')}")
        st.markdown(f"**Location:** {tender.get('location', 'Not specified')}")
    
    # Display description
    st.markdown("### Description")
    st.markdown(tender.get("description", "No description available"))
    
    # Display URL if available
    if tender.get("url"):
        st.markdown(f"[View Original Tender]({tender.get('url')})")

def main():
    """Main Streamlit application"""
    # Set page config
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # App header
    st.title(APP_NAME)
    st.markdown(APP_DESCRIPTION)
    
    # Check system status
    system_status = check_system_status()
    
    # Create sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", ["Match Company Profile", "Scrape Tenders", "System Status"])
    
    # System status section in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")
    
    status_color = "green" if system_status["system_ready"] else "red"
    st.sidebar.markdown(f"Status: :{status_color}[{'Ready' if system_status['system_ready'] else 'Not Ready'}]")
    st.sidebar.markdown(f"Tenders in Database: {system_status['tender_count']}")
    
    if system_status["error"]:
        st.sidebar.error(system_status["error"])
    
    # Main content based on selected page
    if page == "Match Company Profile":
        st.header("Match Your Company Profile")
        
        if not system_status["system_ready"]:
            st.warning("Please scrape tenders first before matching your company profile.")
            st.markdown("Go to the **Scrape Tenders** page to fetch the latest government tenders.")
        else:
            # Company profile input methods
            input_method = st.radio("Select input method:", ["Enter Text", "Upload File"])
            
            profile_text = None
            uploaded_file = None
            
            if input_method == "Enter Text":
                st.markdown("Enter your company profile details below:")
                company_name = st.text_input("Company Name")
                company_description = st.text_area("Company Description", height=150)
                company_services = st.text_area("Services Offered (one per line)", height=100)
                company_capabilities = st.text_area("Company Capabilities (one per line)", height=100)
                
                if st.button("Find Matching Tenders"):
                    if not company_name or not company_description:
                        st.error("Please provide at least the company name and description.")
                    else:
                        # Format the profile text
                        profile_text = f"""
                        Company Name: {company_name}
                        
                        Description:
                        {company_description}
                        
                        Services:
                        {company_services}
                        
                        Capabilities:
                        {company_capabilities}
                        """
                        
                        # Run matching
                        result = run_company_matching(profile_text=profile_text)
                        
                        # Display results
                        if result.get("error"):
                            st.error(result["error"])
                        else:
                            display_matching_results(result)
            
            else:  # Upload File
                st.markdown("Upload your company profile document (PDF, TXT, DOCX):")
                uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt", "docx"])
                
                if uploaded_file is not None:
                    st.success(f"File uploaded: {uploaded_file.name}")
                    if st.button("Find Matching Tenders"):
                        # Run matching
                        result = run_company_matching(uploaded_file=uploaded_file)
                        
                        # Display results
                        if result.get("error"):
                            st.error(result["error"])
                        else:
                            display_matching_results(result)
    
    elif page == "Scrape Tenders":
        st.header("Scrape Government Tenders")
        st.markdown("""
        This process will scrape tenders from various government websites and prepare them for matching.
        It may take several minutes depending on the number of sources and network conditions.
        """)
        
        if st.button("Start Scraping Tenders"):
            result = run_tender_scraping()
            
            if result.get("error"):
                st.error(result["error"])
            else:
                status = result.get("scraping_status", {})
                
                if status.get("status") == "success":
                    st.success(status.get("message", "Scraping completed successfully"))
                    st.metric("Tenders Scraped", status.get("tender_count", 0))
                else:
                    st.error(status.get("message", "Scraping failed"))
    
    else:  # System Status
        st.header("System Status")
        
        # Display system information
        st.subheader("Database Status")
        if system_status["tender_count"] > 0:
            st.success(f"Found {system_status['tender_count']} tenders in the database")
        else:
            st.warning("No tenders found in the database. Please scrape tenders first.")
        
        # Show technical details for debugging
        st.subheader("Technical Details")
        st.markdown(f"Vector DB Path: `{VECTOR_DB_PATH}`")
        
        st.markdown("### Environment")
        st.code(f"Python version: {sys.version}")
        
        # Check if vector database files exist
        st.subheader("Files")
        index_exists = os.path.exists(os.path.join(VECTOR_DB_PATH, "faiss_index.bin"))
        tenders_exists = os.path.exists(os.path.join(VECTOR_DB_PATH, "tenders.pkl"))
        
        st.markdown(f"FAISS Index: {'✅ Found' if index_exists else '❌ Missing'}")
        st.markdown(f"Tenders File: {'✅ Found' if tenders_exists else '❌ Missing'}")

def display_matching_results(result: Dict[str, Any]):
    """Display the matching results"""
    # Display company profile
    if result.get("company_profile"):
        company = result["company_profile"]
        
        st.subheader("Processed Company Profile")
        st.markdown(f"**Company:** {company.get('name', '')}")
        
        with st.expander("View Company Details"):
            st.markdown(f"**Description:** {company.get('description', '')}")
            
            if company.get('services'):
                st.markdown("**Services:**")
                for service in company.get('services', []):
                    st.markdown(f"- {service}")
            
            if company.get('capabilities'):
                st.markdown("**Capabilities:**")
                for capability in company.get('capabilities', []):
                    st.markdown(f"- {capability}")
            
            if company.get('expertise'):
                st.markdown("**Expertise:**")
                for expertise in company.get('expertise', []):
                    st.markdown(f"- {expertise}")
    
    # Display recommendations
    if result.get("recommendations"):
        recs = result["recommendations"]
        
        st.subheader(f"Found {len(recs)} Matching Tenders")
        
        # Sort by similarity score
        recs.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        # Display filters
        st.markdown("### Filter Results")
        col1, col2 = st.columns(2)
        
        with col1:
            # Get unique sources
            sources = list(set(rec.get('tender_details', {}).get('source', 'Unknown') for rec in recs))
            selected_sources = st.multiselect("Filter by Source", options=sources, default=sources)
        
        with col2:
            # Show slider for minimum similarity score
            min_similarity = st.slider("Minimum Similarity Score (%)", 0, 100, 50)
        
        # Filter recommendations
        filtered_recs = [
            rec for rec in recs 
            if rec.get('similarity_score', 0) >= min_similarity and
            rec.get('tender_details', {}).get('source', 'Unknown') in selected_sources
        ]
        
        if not filtered_recs:
            st.warning("No tenders match your current filters. Try adjusting the filters.")
        else:
            st.markdown(f"Showing {len(filtered_recs)} tenders matching your filters")
            
            # Display tenders
            for i, rec in enumerate(filtered_recs):
                with st.expander(f"{i+1}. {rec.get('tender_title', 'Unknown Tender')} - {rec.get('similarity_score', 0):.2f}% Match"):
                    tender = rec.get("tender_details", {})
                    display_tender_details(tender)

if __name__ == "__main__":
    main()