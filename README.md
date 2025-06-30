This repo is a base for diploma thesis project. The code and the topic itself is still under development.
The areas of interest are: biomedical data, gene disease associations, graphs, visualization.

### Structure
- **api**
  - pubmed_api = access to pubmed articles
  - pubtator_api = access to pubmed articles, too, but with annotations from pubtator
- **utils**
  - parse_xml = parse XML-structured pubmed article and convert it into nodes (entities) and edges (relations)
  - create_testset = further process data from xml to create a dataframe and then csv file in special format
    - the format is: pubmed_id, text and then triplets (gene_entity_from_text, disease_entity_from_text, their relation) 
- **visualisation**
  - visualize relations between diseases and genes from one pubmed article
- **web**
  - NOT WORKING NOW


---
- Author: Jan Malý
- Diploma thesis supervisor: Vít Nováček