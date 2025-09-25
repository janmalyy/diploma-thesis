# Cancer Treatment Personalization Tool
The work is stilll under the development.


An interactive, graph-based web application designed to support oncologists in the personalization of cancer treatment. This project is developed as part of a diploma thesis.

## Project Overview

This application processes biomedical articles from PubTator, computes text embeddings, and stores the data in a Neo4j graph database. The web interface allows oncologists to explore relationships between articles, treatments, and medical concepts to support personalized cancer treatment decisions.

## Project Structure

- **api/**
  - `pubtator_api` - Downloads articles from PubTator
- **utils/**
  - `compute_embeddings` - Computes word embeddings for title+abstract fields in articles
  - `xml_to_neo4j` - Extracts data from articles and saves them into Neo4j database
  - `compute_cosine_similarity` - Computes similarity between article embeddings and saves relationships to Neo4j
  - `parse_xml` - Helper functions to parse XML-structured PubTator articles
- **web/**
  - Web interface for the application

## Technologies

- Python 3.12
- Neo4j Graph Database
- FastAPI
- Docker & Docker Compose
- Natural Language Processing (NLTK, sentence-transformers)
- BioPython

## Setup with Docker

### Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
- Git

### Installation Steps

1. Clone the repository:
   ```
   git clone <repository-url>
   cd diploma_thesis
   ```

2. Configure environment variables:
   - The project includes default values in the `docker-compose.yml` file
   - You can modify the `.env` file to customize:
     - Neo4j connection details
     - Database credentials
     - Other configuration parameters

3. Build and start the services:
   ```
   docker-compose up -d
   ```

4. Access the application on web interface: http://localhost:8000


## Local Setup (without Docker)

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables in `.env` file

4. Run the application:
   ```
   python -m diploma_thesis.web.main
   ```


---

- **Author**: Jan Malý
- **Diploma thesis supervisor**: Vít Nováček
