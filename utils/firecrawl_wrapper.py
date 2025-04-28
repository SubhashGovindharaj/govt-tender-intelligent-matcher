import os
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import logging
from firecrawl import FireCrawl
from utils.config import TenderSchema, TENDER_SOURCES
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FirecrawlWrapper:
    """Wrapper class for FireCrawl to scrape government tender websites"""
    
    def __init__(self):
        self.crawler = FireCrawl()
        self.sources = TENDER_SOURCES
        
    def scrape_all_sources(self) -> List[TenderSchema]:
        """Scrape tenders from all sources defined in config"""
        all_tenders = []
        
        for source in self.sources:
            try:
                logger.info(f"Scraping tenders from {source['name']}")
                source_tenders = self._scrape_source(source)
                all_tenders.extend(source_tenders)
                
                # Add a small delay to avoid overwhelming servers
                time.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.error(f"Error scraping {source['name']}: {str(e)}")
        
        logger.info(f"Scraped {len(all_tenders)} tenders in total")
        return all_tenders
    
    def _scrape_source(self, source: Dict) -> List[TenderSchema]:
        """Scrape tenders from a specific source"""
        scraped_tenders = []
        
        try:
            # Use FireCrawl to get the page content
            response = requests.get(source['url'])
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find tender listings using the source-specific selector
            tender_elements = soup.select(source['selector'])
            
            for index, element in enumerate(tender_elements[:20]):  # Limit to first 20 for testing
                try:
                    # Extract tender details - these selectors will need to be adjusted per site
                    tender_data = self._extract_tender_data(element, source)
                    
                    # Skip tenders with missing essential information
                    if not (tender_data.get('title') and tender_data.get('description')):
                        continue
                    
                    # Create a TenderSchema object
                    tender = TenderSchema(
                        id=f"{source['name'].lower().replace(' ', '-')}-{int(time.time())}-{index}",
                        title=tender_data.get('title', ''),
                        description=tender_data.get('description', ''),
                        amount=tender_data.get('amount'),
                        deadline=tender_data.get('deadline'),
                        source=source['name'],
                        url=tender_data.get('url', source['url']),
                        category=tender_data.get('category'),
                        department=tender_data.get('department'),
                        location=tender_data.get('location'),
                        publication_date=tender_data.get('publication_date'),
                        raw_text=str(element)
                    )
                    
                    scraped_tenders.append(tender)
                    
                except Exception as e:
                    logger.warning(f"Error processing tender element: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in scraping source {source['name']}: {str(e)}")
        
        logger.info(f"Scraped {len(scraped_tenders)} tenders from {source['name']}")
        return scraped_tenders
    
    def _extract_tender_data(self, element, source) -> Dict:
        """Extract tender data from HTML element - customize for each source"""
        tender_data = {}
        
        # This is a simplified extraction - in production you'd need specific selectors for each site
        if source['name'] == "Tamil Nadu Tenders":
            try:
                tender_data['title'] = element.select_one('td:nth-child(1)').text.strip()
                tender_data['description'] = element.select_one('td:nth-child(2)').text.strip()
                amount_text = element.select_one('td:nth-child(3)').text.strip()
                tender_data['amount'] = self._extract_amount(amount_text)
                tender_data['deadline'] = element.select_one('td:nth-child(4)').text.strip()
                tender_data['url'] = source['url'] + element.select_one('a')['href'] if element.select_one('a') else source['url']
            except:
                # Fallback to generic extraction if specific selectors fail
                tender_data = self._generic_extract(element)
                
        elif source['name'] == "Maharashtra Tenders":
            # Similar extraction logic customized for Maharashtra site
            try:
                tender_data['title'] = element.select_one('td:nth-child(1)').text.strip()
                tender_data['description'] = element.select_one('td:nth-child(2)').text.strip()
                amount_text = element.select_one('td:nth-child(3)').text.strip()
                tender_data['amount'] = self._extract_amount(amount_text)
                tender_data['deadline'] = element.select_one('td:nth-child(4)').text.strip()
                tender_data['url'] = source['url'] + element.select_one('a')['href'] if element.select_one('a') else source['url']
            except:
                tender_data = self._generic_extract(element)
                
        elif source['name'] == "Central Public Procurement Portal":
            try:
                tender_data['title'] = element.select_one('h4').text.strip()
                tender_data['description'] = element.select_one('p.description').text.strip()
                amount_text = element.select_one('span.amount').text.strip()
                tender_data['amount'] = self._extract_amount(amount_text)
                tender_data['deadline'] = element.select_one('span.deadline').text.strip()
                tender_data['url'] = source['url'] + element.select_one('a')['href'] if element.select_one('a') else source['url']
            except:
                tender_data = self._generic_extract(element)
                
        elif source['name'] == "Government e-Marketplace":
            try:
                tender_data['title'] = element.select_one('h3.card-title').text.strip()
                tender_data['description'] = element.select_one('div.card-text').text.strip()
                amount_text = element.select_one('span.bid-amount').text.strip()
                tender_data['amount'] = self._extract_amount(amount_text)
                tender_data['deadline'] = element.select_one('span.deadline').text.strip()
                tender_data['url'] = element.select_one('a.card-link')['href'] if element.select_one('a.card-link') else source['url']
            except:
                tender_data = self._generic_extract(element)
        
        else:
            # Generic extraction for other sources
            tender_data = self._generic_extract(element)
            
        return tender_data
    
    def _generic_extract(self, element) -> Dict:
        """Generic extraction method for when specific selectors fail"""
        tender_data = {}
        
        # Try to find title in any heading tag
        headings = element.select('h1, h2, h3, h4, h5, h6')
        if headings:
            tender_data['title'] = headings[0].text.strip()
        else:
            # Fallback to first significant text
            tender_data['title'] = element.get_text().strip()[:100]
        
        # Description - use all text content
        tender_data['description'] = element.get_text().strip()
        
        # Look for amount patterns
        text = element.get_text()
        tender_data['amount'] = self._extract_amount(text)
        
        # Look for date patterns for deadline
        tender_data['deadline'] = self._extract_date(text)
        
        # URL - find first link
        link = element.select_one('a')
        if link and link.has_attr('href'):
            tender_data['url'] = link['href']
            
        return tender_data
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amount from text"""
        import re
        # Look for patterns like "Rs. 1,000,000" or "₹ 10.5 Lakhs" or "INR 5 Cr"
        amount_patterns = [
            r'(?:Rs\.?|₹|INR)\s*([\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|crores?|cr))?)',
            r'([\d,]+(?:\.\d+)?)\s*(?:lakhs?|crores?|cr)'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    # Handle lakhs and crores conversion
                    if 'lakh' in text.lower():
                        return float(amount_str) * 100000
                    elif 'cr' in text.lower() or 'crore' in text.lower():
                        return float(amount_str) * 10000000
                    else:
                        return float(amount_str)
                except ValueError:
                    pass
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text"""
        import re
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None