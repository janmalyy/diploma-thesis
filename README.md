This repo is a base for diploma thesis project.
The aim is to develop an interactive, graph-based web app designed to support oncologists in the personalization of cancer treatment.

### Structure
- **api**
  - pubtator_api = download articles from pubtator 
- **utils**
  - compute_embeddings = compute word embeddings for title+abstract field in articles
  - xml_to_neo4j = extract the data from articles and save them into neo4j database 
  - compute_cosine_similarity = compute the similarity of word embeddings of articles and save the info about the most similar articles into neo4j
  - parse_xml = helper functions to parse XML-structured pubtator articles
- **web**
  - WIP


---
- Author: Jan Malý
- Diploma thesis supervisor: Vít Nováček