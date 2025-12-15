"""混合搜索：语义搜索 + 关键字搜索"""

from .database import StarDatabase
from .embedder import EmbeddingGenerator


class HybridSearcher:
    """混合搜索引擎"""

    def __init__(self, db: StarDatabase, embedder: EmbeddingGenerator):
        self.db = db
        self.embedder = embedder

    def search(
        self,
        query: str,
        mode: str = "hybrid",  # "semantic", "keyword", "hybrid"
        limit: int = 10,
        semantic_weight: float = 0.7,
    ) -> list[dict]:
        """
        执行搜索

        Args:
            query: 搜索查询
            mode: 搜索模式
                - "semantic": 纯语义搜索
                - "keyword": 纯关键字搜索
                - "hybrid": 混合搜索 (默认)
            limit: 返回结果数量
            semantic_weight: 混合搜索中语义搜索的权重

        Returns:
            搜索结果列表
        """
        if mode == "semantic":
            return self._semantic_search(query, limit)
        elif mode == "keyword":
            return self._keyword_search(query, limit)
        else:
            return self._hybrid_search(query, limit, semantic_weight)

    def _semantic_search(self, query: str, limit: int) -> list[dict]:
        """纯语义搜索"""
        query_embedding = self.embedder.encode_single(query)
        results = self.db.vector_search(query_embedding, limit)
        for r in results:
            r["match_type"] = "semantic"
        return results

    def _keyword_search(self, query: str, limit: int) -> list[dict]:
        """纯关键字搜索"""
        results = self.db.keyword_search(query, limit)
        for r in results:
            r["match_type"] = "keyword"
            r["similarity"] = None
        return results

    def _hybrid_search(
        self, query: str, limit: int, semantic_weight: float
    ) -> list[dict]:
        """
        混合搜索：结合语义和关键字搜索结果
        使用 Reciprocal Rank Fusion (RRF) 算法合并结果
        """
        # 获取两种搜索结果 (各取更多以便合并)
        semantic_results = self._semantic_search(query, limit * 2)
        keyword_results = self._keyword_search(query, limit * 2)

        # RRF 融合
        k = 60  # RRF 常数
        scores: dict[str, dict] = {}

        # 语义搜索贡献
        for rank, r in enumerate(semantic_results):
            key = r["full_name"]
            rrf_score = semantic_weight / (k + rank + 1)
            if key not in scores:
                scores[key] = {"data": r.copy(), "score": 0}
            scores[key]["score"] += rrf_score
            scores[key]["data"]["match_type"] = "semantic"

        # 关键字搜索贡献
        for rank, r in enumerate(keyword_results):
            key = r["full_name"]
            rrf_score = (1 - semantic_weight) / (k + rank + 1)
            if key in scores:
                scores[key]["score"] += rrf_score
                scores[key]["data"]["match_type"] = "hybrid"
            else:
                r_copy = r.copy()
                r_copy["match_type"] = "keyword"
                scores[key] = {"data": r_copy, "score": rrf_score}

        # 按融合分数排序
        sorted_results = sorted(
            scores.values(), key=lambda x: x["score"], reverse=True
        )[:limit]

        return [item["data"] for item in sorted_results]
