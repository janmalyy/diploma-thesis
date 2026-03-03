# Variant Evidence Aggregator (Diploma Thesis Project)

This project is a tool designed to automate the process of genetic variant evidence aggregation and summarization from scientific literature using Large Language Models (LLMs).

    Author: Jan Malý
    Diploma thesis supervisor: Vít Nováček

## Main Pipeline

The core functionality of the project follows a multi-stage pipeline:

1.  **Input**: The user provides a Gene name, Variant change, and Level (e.g., `BRCA1 R7C protein`).
2.  **Variant Normalization (SynVar)**: Normalizes the variant description using the SynVar API to ensure consistent nomenclature.
3.  **Literature Search (SIBiLS)**: Searches for scientific articles mentioning the variant using the SIBiLS Variomes API.
4.  **Full-text Retrieval**: Fetches the full-text content of identified articles from sources like PubTator and BiodiversityPMC.
5.  **Supplementary Data Extraction**: Attempts to retrieve and process supplemental data tables for additional context.
6.  **LLM Relevance Filtering**: An LLM agent checks whether each article is truly relevant to the specific variant and its pathogenicity.
7.  **LLM Evidence Extraction**: For each relevant article, an LLM agent extracts structured evidence, including functional study results, clinical findings, and population data.
8.  **LLM Evidence Aggregation**: A final LLM agent aggregates all extracted evidence into a comprehensive narrative summary and structured pathogenicity overview.

## Project Components

### Core Logic (`diploma_thesis/core`)
-   `run_llm.py`: Defines the LLM agents (checker, extractor, aggregator) using `pydantic-ai`.
-   `models.py`: Pydantic data models for Variants, Articles, and Evidence.
-   `update_article_fulltext.py`: Logic for fetching full-text from external APIs.
-   `update_suppl_data.py`: Logic for downloading and processing supplementary files.

### API Clients (`diploma_thesis/api`)
-   `synvar.py`: Integration with the SynVar API for variant nomenclature.
-   `variomes.py`: Client for the SIBiLS Variomes literature search.
-   `einfra.py`: Client for interacting with the E-INFRA LLM infrastructure.
-   `clinvar.py`, `convert_ids.py`, `annotations.py`: Additional tools for variant data and ID conversion.

### Web Interface (`diploma_thesis/web`)
-   FastAPI application serving:
    -   A Variant summary generation interface.
    -   An Excel file viewer/editor.
-   Jinja2 templates and interactive JavaScript frontend.

## Setup Instructions

### Prerequisites
-   Python 3.12+
-   Docker and Docker Compose (optional, for containerized setup)

### Environment Configuration
Create a `.env` file in the root directory with the following variables:
```env
NIH_EMAIL="your.email@example.com"
E_INFRA_API_KEY="your-einfra-api-key"
```

### Option 1: Docker Setup (Recommended)
1.  Build and start the containers:
    ```bash
    docker-compose up --build
    ```
2.  Access the application at `http://localhost:8000`.

### Option 2: Manual Setup
1.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/macOS
    source venv/bin/activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```bash
    uvicorn diploma_thesis.web.main:app --host 0.0.0.0 --port 8000 --reload
    ```
4.  Access the application at `http://localhost:8000`.
