"""DuckDB 存储元数据 + NumPy 向量搜索"""

from pathlib import Path
from typing import Any

import duckdb
import numpy as np

from ..models.repo import StarredRepo


class StarDatabase:
    """数据库管理：DuckDB 存元数据，NumPy 存向量"""

    def __init__(self, db_path: str = "data/stars.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings_path = self.db_path.with_suffix(".npy")
        self.ids_path = self.db_path.with_suffix(".ids.npy")
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._embeddings: np.ndarray | None = None
        self._ids: np.ndarray | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
            self._setup()
        return self._conn

    def _setup(self):
        """初始化数据库表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS starred_repos (
                id BIGINT PRIMARY KEY,
                full_name VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                owner VARCHAR NOT NULL,
                description VARCHAR,
                html_url VARCHAR NOT NULL,
                homepage VARCHAR,
                language VARCHAR,
                topics VARCHAR[],
                stargazers_count INTEGER,
                updated_at VARCHAR,
                created_at VARCHAR,
                starred_at VARCHAR,
                search_text VARCHAR,
                sync_at TIMESTAMP DEFAULT current_timestamp
            );
        """)

    def save_repos(
        self,
        repos: list[StarredRepo],
        search_texts: list[str],
        embeddings: np.ndarray,
    ):
        """保存项目数据和向量"""
        # 保存元数据到 DuckDB
        for repo, text in zip(repos, search_texts):
            self.conn.execute(
                """
                INSERT OR REPLACE INTO starred_repos
                (id, full_name, name, owner, description, html_url, homepage,
                 language, topics, stargazers_count, updated_at, created_at,
                 search_text, sync_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
                """,
                [
                    repo.id,
                    repo.full_name,
                    repo.name,
                    repo.owner,
                    repo.description,
                    repo.html_url,
                    repo.homepage,
                    repo.language,
                    repo.topics,
                    repo.stargazers_count,
                    repo.updated_at,
                    repo.created_at,
                    text,
                ],
            )
        self.conn.commit()

        # 保存向量到 NumPy 文件
        ids = np.array([r.id for r in repos], dtype=np.int64)
        np.save(self.embeddings_path, embeddings)
        np.save(self.ids_path, ids)

        # 更新缓存
        self._embeddings = embeddings
        self._ids = ids

    def load_embeddings(self) -> tuple[np.ndarray, np.ndarray]:
        """加载向量数据"""
        if self._embeddings is None:
            if self.embeddings_path.exists():
                self._embeddings = np.load(self.embeddings_path)
                self._ids = np.load(self.ids_path)
            else:
                raise FileNotFoundError("向量数据不存在，请先运行 sync")
        return self._embeddings, self._ids

    def get_sync_status(self) -> dict[str, Any]:
        """获取同步状态"""
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total_repos,
                MAX(sync_at) as last_sync
            FROM starred_repos
        """).fetchone()
        return {
            "total_repos": result[0],
            "last_sync": result[1],
            "indexed_repos": result[0],
        }

    def vector_search(
        self, query_embedding: np.ndarray, limit: int = 10
    ) -> list[dict]:
        """NumPy 暴力向量搜索"""
        embeddings, ids = self.load_embeddings()

        # 归一化查询向量
        query_norm = query_embedding / np.linalg.norm(query_embedding)

        # 计算余弦相似度 (embeddings 已归一化)
        similarities = embeddings @ query_norm

        # 取 top-k
        top_indices = np.argsort(similarities)[::-1][:limit]
        top_ids = ids[top_indices].tolist()
        top_scores = similarities[top_indices].tolist()

        # 查询元数据
        placeholders = ",".join(["?"] * len(top_ids))
        result = self.conn.execute(
            f"""
            SELECT id, full_name, description, html_url, language,
                   topics, stargazers_count
            FROM starred_repos
            WHERE id IN ({placeholders})
            """,
            top_ids,
        ).fetchall()

        # 按相似度排序
        id_to_row = {r[0]: r for r in result}
        results = []
        for repo_id, score in zip(top_ids, top_scores):
            if repo_id in id_to_row:
                r = id_to_row[repo_id]
                results.append({
                    "full_name": r[1],
                    "description": r[2],
                    "html_url": r[3],
                    "language": r[4],
                    "topics": r[5],
                    "stargazers_count": r[6],
                    "similarity": float(score),
                })
        return results

    def keyword_search(self, keyword: str, limit: int = 10) -> list[dict]:
        """关键字搜索"""
        result = self.conn.execute(
            """
            SELECT full_name, description, html_url, language,
                   topics, stargazers_count
            FROM starred_repos
            WHERE full_name ILIKE '%' || ? || '%'
               OR description ILIKE '%' || ? || '%'
            ORDER BY stargazers_count DESC
            LIMIT ?
            """,
            [keyword, keyword, limit],
        ).fetchall()

        return [
            {
                "full_name": r[0],
                "description": r[1],
                "html_url": r[2],
                "language": r[3],
                "topics": r[4],
                "stargazers_count": r[5],
            }
            for r in result
        ]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
