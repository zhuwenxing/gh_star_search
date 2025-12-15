"""使用 Huggingface sentence-transformers 生成 Embedding"""

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """文本嵌入生成器"""

    DEFAULT_MODEL = "Qwen/Qwen3-Embedding-0.6B"

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """懒加载模型"""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def embedding_dim(self) -> int:
        """返回嵌入向量维度"""
        return self.model.get_sentence_embedding_dimension()

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = True,
    ) -> np.ndarray:
        """
        批量生成 embedding
        返回: shape (n, embedding_dim) 的 numpy 数组
        """
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 归一化，便于余弦相似度计算
        )

    def encode_single(self, text: str) -> np.ndarray:
        """生成单个文本的 embedding"""
        return self.encode([text], show_progress=False)[0]
