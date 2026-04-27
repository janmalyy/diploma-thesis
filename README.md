## Interpreting genetic variants mentions in the literature
_Codebase for the diploma thesis_

This project is a tool designed to automate the process of genetic variant evidence aggregation and summarization from scientific literature using LLMs.

    Author: Jan Malý
    Diploma thesis supervisor: Vít Nováček

## Main Pipeline

The core functionality of the project follows a multi-stage pipeline:

1.  **Input**: The user provides a Gene name, Variant change, and Level (e.g., `BRCA1 R7C protein`).
2.  **Variant Normalization (SynVar)**: Normalizes the variant description using the SynVar API.
3.  **Literature Search (Variomes)**: Searches for biomedical articles mentioning the variant using the SIBiLS Variomes API.
4.  **Full-text Retrieval**: Fetches the full-text content of identified articles from PubTator or BiodiversityPMC.
5.  **Supplementary Data Extraction**: Attempts to retrieve and process supplementary data.
6.  **LLM Relevance Filtering + Evidence Extraction**: An LLM agent checks whether each article is truly relevant to the specific variant and its pathogenicity and if so, extracts structured evidence.
8.  **LLM Evidence Aggregation**: A final LLM agent aggregates all extracted evidence into a comprehensive narrative summary.

## Project Components

### Core Logic (`diploma_thesis/core`)
- `build_paragraph.py`: Processing logic for supplementary data reconstruction.
- `document_parsers.py`: Parsing and annotation of PubTator XLMs and BIodiversityPMC JSONs.
- `llm_response_models.py`: Pydantic models defining the LLM outputs.
- `models.py`: definition of Article and Variant classes.
- `run_llm.py`: Defines the LLM agents and functions to run them.
- `update_article_fulltext.py`: Main logic for processing fulltext.
- `update_suppl_data.py`: Main logic for processing supplementary data.

### Web Interface (`diploma_thesis/web`)
The FE uses HTML and JS and communicates with the BE thanks to FastAPI.
- `main.py`: Includes the main function to run the pipeline.
- `static/variant_summary.js`: All JavaScript logic for UI
- `templates/variant_summary.html`: All HTML logic for UI

### Data Folder Structure (`diploma_thesis/data`)

-   `100variants/`: 1x 100 runs for BRCA1+BRCA2 variants for the **statistical analysis**
-   `15variants/`: 5x 15 runs for selected 15 variants for the **evaluation consistency**
-   `15variants_data_evaluated_by_molecular_geneticist/`: log of 1x 15 runs for selected 15 variants displayed to the annotator during her evaluation
-   `retrieval_quality/`: One run for each article in 15 variants with **LLM verification outputs**

## Setup Instructions

### Prerequisites
-   Python 3.12+
-   Docker and Docker Compose (optional, for containerized setup)

### Environment Configuration

#### 1. API and Service Credentials
Create a `.env` file in the root directory with the following variables:
```env
NIH_EMAIL="your.email@example.com"
E_INFRA_API_KEY="your-einfra-api-key"
```

#### 2. Google Drive Integration (for Result Logging)
- To enable automatic upload of results to Google Drive, you need to provide Google `credentials.json` file:
- Place the file in the project root.
- The application will use this to upload and share results with the email specified in `NIH_EMAIL`.

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
