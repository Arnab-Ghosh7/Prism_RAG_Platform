import logging
from typing import List, Dict

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except Exception as e:
    logging.warning(f"ChromaDB or its dependencies (e.g. onnxruntime) could not be loaded: {e}. Falling back to In-Memory Mock RAG Engine.")
    CHROMA_AVAILABLE = False

class RAGEngine:
    def __init__(self):
        self.chroma_available = CHROMA_AVAILABLE
        if self.chroma_available:
            try:
                self.client = chromadb.PersistentClient(path="./chroma_db")
                self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
                self.collection = self.client.get_or_create_collection(
                    name="prism_knowledge",
                    embedding_function=self.embedding_fn
                )
            except Exception as e:
                logging.warning(f"Error initializing ChromaDB: {e}. Switching to In-Memory Mock RAG Engine.")
                self.chroma_available = False
        
        if not self.chroma_available:
            self.mock_docs = []
            self.mock_metadatas = []

    def ingest(self, texts: List[str], metadatas: List[Dict]):
        if self.chroma_available:
            try:
                ids = [f"doc_{i}_{hash(t)}" for i, t in enumerate(texts)]
                if self.collection.count() > 0:
                    self.collection.delete(ids=self.collection.get()["ids"])
                self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
                return
            except Exception as e:
                logging.warning(f"ChromaDB ingest failed, falling back to mock: {e}")
        
        # Mock ingest (in-memory)
        self.mock_docs = list(texts)
        self.mock_metadatas = list(metadatas)

    def retrieve(self, query: str, n_results: int = 3) -> Dict:
        if self.chroma_available:
            try:
                if self.collection.count() == 0:
                    return {"documents": [], "metadatas": [], "retrieval_confidence": 0.0}
                
                results = self.collection.query(query_texts=[query], n_results=min(n_results, self.collection.count()))
                distances = results["distances"][0]
                max_dist = 2.0
                retrieval_conf = [max(0.0, 1.0 - (d / max_dist)) for d in distances]
                avg_retrieval_conf = sum(retrieval_conf) / len(retrieval_conf) if retrieval_conf else 0.0

                return {
                    "documents": results["documents"][0],
                    "metadatas": results["metadatas"][0],
                    "retrieval_confidence": avg_retrieval_conf
                }
            except Exception as e:
                logging.warning(f"ChromaDB retrieve failed, falling back to mock: {e}")

        # Mock retrieve (simple keyword matching)
        if not self.mock_docs:
            return {"documents": [], "metadatas": [], "retrieval_confidence": 0.0}

        query_words = set(query.lower().split())
        scored_docs = []
        for doc, meta in zip(self.mock_docs, self.mock_metadatas):
            doc_words = set(doc.lower().split())
            overlap = len(query_words.intersection(doc_words))
            score = overlap / max(1, len(query_words))
            scored_docs.append((doc, meta, score))

        # Sort by overlap score descending
        scored_docs.sort(key=lambda x: x[2], reverse=True)
        top_docs = scored_docs[:n_results]

        retrieval_confidence = top_docs[0][2] if top_docs else 0.0
        if retrieval_confidence == 0.0 and self.mock_docs:
            retrieval_confidence = 0.1

        return {
            "documents": [d[0] for d in top_docs],
            "metadatas": [d[1] for d in top_docs],
            "retrieval_confidence": retrieval_confidence
        }
