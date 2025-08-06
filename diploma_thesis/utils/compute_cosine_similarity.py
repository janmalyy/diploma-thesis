import numpy as np
import pickle

from diploma_thesis.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, DATA_DIR
from diploma_thesis.utils.xml_to_neo4j import Neo4jConnection


def compute_topk_similarities(keys: list, vectors: np.ndarray, k: int = 100, batch_size: int = 500) -> dict:
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


if __name__ == '__main__':
    conn = Neo4jConnection(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    keys = [record["id"] for record in conn.query("MATCH (d:Document) RETURN d.id AS id")]
    vectors = [record["embedding"] for record in conn.query("MATCH (d:Document) RETURN d.embedding AS embedding")]
    vectors = np.asarray(vectors)

    topk_results = compute_topk_similarities(keys, vectors, k=200, batch_size=500)

    with open(DATA_DIR / "topk_similarities.pkl", "wb") as f:
        pickle.dump(topk_results, f, protocol=pickle.HIGHEST_PROTOCOL)
