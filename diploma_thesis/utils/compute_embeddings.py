import os
import csv

from sentence_transformers import SentenceTransformer
from nltk import sent_tokenize
import numpy as np

from diploma_thesis.settings import DATA_DIR
from diploma_thesis.utils.parse_xml import get_title_with_abstract

if __name__ == '__main__':
    # create csv with two columns: id and title+abstract
    # with open(DATA_DIR / "breast_cancer_titles_abstracts_2020_2025.csv", "w", encoding="utf-8") as f:
    #     writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_ALL, quotechar="|")
    #     for dir in os.listdir(DATA_DIR / "breast_cancer"):
    #         for file in os.listdir(DATA_DIR / "breast_cancer" / dir):
    #             file_id = file.split("_")[-1].split(".")[0]
    #             text = get_title_with_abstract(DATA_DIR / "breast_cancer" / dir / file)
    #             if len(text) < 200:     # skip bad xmls without content (e.g. with title '- No Title -')
    #                 continue
    #             writer.writerow([file_id, text])
    #         print(dir + " done.")

    # ---------------------------
    # create csv with two columns: id and embeddings from title+abstract
    # this is much better to run on gpu, e.g. in colab here: https://colab.research.google.com/drive/1NgLvZqrV48XjGKeXftWNP2A2RoEnuRSj#scrollTo=77UOLuLyZnOR
    model = SentenceTransformer("neuml/pubmedbert-base-embeddings")
    with open(DATA_DIR / "breast_cancer_titles_abstracts_2020_2025.csv", "r", encoding="utf-8") as in_file:
        with open(DATA_DIR / "breast_cancer_embeddings_2020_2025.csv", "w", encoding="utf-8", newline="") as out_file:  # without newline="", every second line was blank
            reader = csv.reader(in_file, delimiter=",", quotechar='|')
            writer = csv.writer(out_file, delimiter=",", quoting=csv.QUOTE_ALL, quotechar="|")
            counter = 0
            for row in reader:
                if not row:
                    continue
                text = row[1]
                sentences = sent_tokenize(text)
                for i in range(len(sentences)):
                    sentences[i] = sentences[i].strip().lower()
                embeddings = model.encode(sentences)
                mean_pooled_embedding = np.mean(np.array(embeddings), axis=0).tolist()

                writer.writerow([row[0], mean_pooled_embedding])
                if counter % 1000 == 0:
                    print(f"{counter} abstracts processed.")
                counter += 1
