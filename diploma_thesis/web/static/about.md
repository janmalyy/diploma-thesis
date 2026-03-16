This tool is an AI-powered platform designed to link genetic variants to biomedical literature. It's developed as a master's thesis by Jan Malý at Masaryk University.

**How it Works**

The pipeline starts with the SynVar service for precise variant recognition and normalization. It then retrieves relevant literature mentions from PMC, MEDLINE and a subset of supplementary data of PMC articles through Variomes. The mentions are sorted and annotated by Pubtator or BiodiversityPMC. Then the mentions are fed into a LLM pipeline that again evaluates the relevance nad extracts specific evidence points regarding pathogenicity and clinical significance. As a result, the user is provided with LLM-generated both narrative and structured variant summary.

The tool is open-source under MIT licence, the code is available at: https://github.com/janmalyy/diploma-thesis.
