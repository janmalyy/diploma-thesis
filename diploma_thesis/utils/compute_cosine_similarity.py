import logging
import numpy as np
import pickle
import time

from diploma_thesis.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, DATA_DIR
from diploma_thesis.utils.xml_to_neo4j import Neo4jConnection, batch


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def compute_topk_similarities(keys: list, vectors: np.ndarray, k: int = 100, batch_size: int = 500) -> dict[str, dict[str, list]]:
    """
    Compute top-k cosine similarities for each vector and return results mapped by keys.

    Args:
        keys (list): List of keys corresponding to each vector. Length = n_vectors.
        vectors (np.ndarray): Matrix of shape (n_vectors, dim).
        k (int): Number of top similarities to keep per vector. Must be less than n_vectors.
        batch_size (int): Batch size for computation.

    Returns:
        dict: Mapping key -> {"top_keys": List[key], "similarities": List[float]},
              sorted by similarity in descending order.
    """
    n_vectors, dim = vectors.shape
    assert len(keys) == n_vectors, "Keys length must match vectors count"

    if not (0 < k < n_vectors):
        raise ValueError(f"k must be greater than 0 and less than the number of vectors ({n_vectors}). Got k={k}")

    # Normalize vectors to unit norm
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors_norm = vectors / np.clip(norms, a_min=1e-10, a_max=None)

    results = {}

    for start in range(0, n_vectors, batch_size):
        end = min(start + batch_size, n_vectors)

        batch = vectors_norm[start:end]  # (batch_size, dim)
        sims = np.dot(batch, vectors_norm.T)  # (batch_size, n_vectors)

        # Exclude self-similarity
        for i in range(end - start):
            sims[i, start + i] = -np.inf

        # Get top-k per vector using argpartition for efficiency
        # We need k+1 because we excluded the self-similarity
        batch_top_idx = np.argpartition(sims, -k, axis=1)[:, -k:]
        batch_top_sims = np.take_along_axis(sims, batch_top_idx, axis=1)

        # Sort top-k descending
        sorted_order = np.argsort(-batch_top_sims, axis=1)
        batch_top_idx_sorted = np.take_along_axis(batch_top_idx, sorted_order, axis=1)
        batch_top_sims_sorted = np.take_along_axis(batch_top_sims, sorted_order, axis=1)

        # Map indices back to keys and store
        for i, vec_idx in enumerate(range(start, end)):
            top_keys = [keys[j] for j in batch_top_idx_sorted[i]]
            top_sims = batch_top_sims_sorted[i].tolist()
            results[keys[vec_idx]] = {"top_keys": top_keys, "similarities": top_sims}

    return results


def fetch_and_compute_similarities(conn, k=200, batch_size=500):
    """
    Fetch document IDs and embeddings from Neo4j, compute similarities, and return results.

    Args:
        conn: Neo4j connection object
        k: Number of top similarities to compute per document
        batch_size: Batch size for computation

    Returns:
        Dictionary of top-k similarities
    """
    logger.info("Fetching document IDs from Neo4j...")
    keys = [record["id"] for record in conn.query("MATCH (d:Document) RETURN d.id AS id")]

    logger.info(f"Fetched {len(keys)} document IDs")
    if not keys:
        logger.error("No documents found in the database.")
        return None

    logger.info("Fetching document embeddings from Neo4j...")
    vectors = [record["embedding"] for record in conn.query("MATCH (d:Document) RETURN d.embedding AS embedding")]
    vectors = np.asarray(vectors)

    logger.info(f"Computing top-{k} similarities for {len(keys)} documents...")
    start_time = time.time()
    topk_results = compute_topk_similarities(keys, vectors, k=k, batch_size=batch_size)
    elapsed_time = time.time() - start_time

    logger.info(f"Similarity computation completed in {elapsed_time:.2f} seconds.")
    return topk_results


def save_similarities_to_pkl(topk_results, output_path=DATA_DIR / "topk_similarities.pkl"):
    """
    Save similarity results to a pickle file.

    Args:
        topk_results: Dictionary of similarity results
        output_path: Path to save the pickle file (default: DATA_DIR/topk_similarities.pkl)
    """
    with open(output_path, "wb") as f:
        pickle.dump(topk_results, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Similarity results saved successfully.")


def load_similarities_from_pkl(input_path=DATA_DIR / "topk_similarities.pkl"):
    """
    Load similarity results from a pickle file.

    Args:
        input_path: Path to the pickle file (default: DATA_DIR/topk_similarities.pkl)

    Returns:
        Dictionary of similarity results
    """
    try:
        with open(input_path, "rb") as f:
            data = pickle.load(f)
        logger.info("Similarity results loaded successfully.")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {input_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading similarity results: {e}")
        return None


def save_similarities_to_neo4j(conn, data, top_n=20, batch_size=500):
    """
    Save similarity relationships to Neo4j.

    Args:
        conn: Neo4j connection object
        data: Dictionary of similarity results
        top_n: Number of top similarities to save per document
        batch_size: Batch size for Neo4j operations
    """
    if not data:
        logger.error("No similarity data to save")
        return

    batch_create_relationships_query = """
    UNWIND $batch AS relationship
    MATCH (a:Document {id: toInteger(relationship.id1)})
    MATCH (b:Document {id: toInteger(relationship.id2)})
    MERGE (a)-[r:is_similar_to]-(b)
    SET r.weight = relationship.similarity
    """

    # Prepare relationships data
    relationships = []
    for article_id, article_data in data.items():
        top_keys = article_data["top_keys"][:top_n]
        similarities = article_data["similarities"][:top_n]

        for i, target_id in enumerate(top_keys):
            similarity = round(similarities[i], 4)
            relationships.append({
                "id1": article_id,
                "id2": target_id,
                "similarity": similarity
            })

    total_batches = (len(relationships) + batch_size - 1) // batch_size
    logger.info(f"Saving {len(relationships)} relationships to Neo4j in {total_batches} batches.")

    # Process in batches
    start_time = time.time()
    for i, batch_chunk in enumerate(batch(relationships, batch_size)):
        logger.info(f"Processing batch {i + 1}/{total_batches}...")
        conn.query(batch_create_relationships_query, {"batch": batch_chunk})

    elapsed_time = time.time() - start_time
    logger.info(f"Created {len(relationships)} 'is_similar_to' relationships in {elapsed_time:.2f} seconds.")


if __name__ == '__main__':
    k = 200
    top_n = 20
    batch_size = 500

    conn = Neo4jConnection(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

    topk_results = fetch_and_compute_similarities(conn, k, batch_size)
    save_similarities_to_pkl(topk_results)

    data = load_similarities_from_pkl()
    save_similarities_to_neo4j(conn, data, top_n, batch_size)
