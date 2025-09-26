# Cancer Treatment Personalization Tool
**The work is stilll under the development.**


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
- Docker
- Natural Language Processing (NLTK, sentence-transformers)
- BioPython

## Setup with Docker

### Prerequisites

- [Docker](https://www.docker.com/get-started)
- Git

### Installation Steps

1. Clone the repository:
   ```
   git clone <repository-url>
   cd diploma_thesis
   ```

2. Configure environment variables:
   - You have to ask for `.env` file with credentials and place it into root directory

3. Build and start the services:
   ```
   docker-compose up -d
   ```

4. Access the application on web interface: http://localhost:8000 or acces the database on: http://localhost:7474


## Local Setup (without Docker)

### Prerequisites

- Git
- [Neo4j Desktop](https://neo4j.com/download/neo4j-desktop/?edition=desktop&flavour=winstall64&release=2.0.3&offline=false) with running database filled in with the data

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

3. Configure environment variables:
   - You have to ask for `.env` file with credentials and place it into root directory

4. Run the application:
   ```
   python -m diploma_thesis.web.main
   ```
5. Access the application on web interface: http://localhost:8000 or acces the database on: http://localhost:7474

---

- **Author**: Jan Malý, 526325@mail.muni.cz
- **Diploma thesis supervisor**: Vít Nováček
