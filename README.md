# 🏛️ Government Tender Intelligent Matcher (LLM + Firecrawl)

This project intelligently scrapes government tender websites, crawls company profiles, generates embeddings, and recommends tenders based on similarity matching using LLMs.

## 🚀 Features
- Real-time tender scraping using Firecrawl AI
- Company profile web crawling
- Vector embedding + similarity search
- LLM-based tender recommendation engine
- Streamlit interactive dashboard

## 🛠️ Tech Stack
- Python 3.11
- Streamlit
- Langchain
- Firecrawl
- Ollama (Local LLMs)
- FAISS / ChromaDB
- Scikit-Learn
- Sentence-Transformers

## 📂 Project Structure

app/
app.py
crawler/
crawl_tenders.py
crawl_company.py
embeddings/
generate_embeddings.py
vectorstore/
store_faiss.py
llm/
query_llm.py
utils/
text_processing.py
config.py
scripts/
ingest_pipeline.py
data/
(scraped data, pdfs, htmls)

## ⚡ Quick Start
```bash
conda create -n tender-recommender-llm python=3.11 -y
conda activate tender-recommender-llm
pip install -r requirements.txt
streamlit run app/app.py

🔥 Developed by

Subhash Govindharaj ❤️
