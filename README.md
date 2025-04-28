# Government Tender Intelligent Matcher

A system that intelligently matches company profiles with relevant government tenders using LLMs and similarity search.

## Project Overview

This system scrapes government tenders from multiple sources, stores the data in a vector database, and allows companies to input their details to find the most relevant tenders for their business. It leverages Ollama's LLM models and embeddings for local processing and LangGraph for orchestrating the workflow.

## Features

- Scrapes tenders from 10+ government websites
- Stores tender data in a vector database for fast similarity searches
- Processes company profiles from text input or uploaded documents
- Matches companies to relevant tenders using semantic similarity
- Provides a user-friendly interface via Streamlit

## Installation

1. Clone this repository:
```bash
git clone https://github.com/SubhashGovindharaj/govt-tender-intelligent-matcher.git
cd govt-tender-intelligent-matcher
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install and run Ollama (for local embeddings):
Follow the instructions at [https://ollama.ai/](https://ollama.ai/) to install Ollama

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

Run the Streamlit application:
```bash
streamlit run app.py
```

## Project Structure

```
.
├── agents
│   ├── company_scraper_agent.py  # Scraping company profile and tenders
│   └── tender_scraper_agent.py   # Scraping tenders from government portals
├── data
├── docs
├── graphs
│   └── main_graph.py  # Graph generation and visualization for tender relations
├── README.md  # Documentation and project setup
├── requirements.txt  # Dependencies for the project
├── scripts
│   └── run_graph.py  # Script to execute the tender recommendation process
└── utils
    ├── config.py  # Configuration settings and API keys
    └── firecrawl_wrapper.py  # Firecrawl integration functions
```

## Tech Stack

- **Scraping**: Firecrawl SDK for intelligent scraping
- **Embeddings**: Ollama's local model for embedding generation
- **Vector DB**: FAISS for fast similarity search
- **Web Framework**: Streamlit for the user interface
- **Orchestration**: LangGraph for workflow management
- **Backend**: Python for the backend logic

## License

MIT