from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils import safe_clamp


class EvidenceRetriever:
    """Small local TF-IDF retriever for grounding without a vector database."""

    def __init__(self, documents: list[str]):
        self.documents = [safe_clamp(x, 3000) for x in documents if x and x.strip()]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(self.documents) if self.documents else None

    def retrieve(self, query: str, k: int = 5) -> list[str]:
        if self.matrix is None:
            return []
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix).ravel()
        idx = sims.argsort()[::-1][:k]
        return [self.documents[i] for i in idx if sims[i] > 0]
