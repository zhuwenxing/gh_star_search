"""Web 界面 - FastAPI"""

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "stars.duckdb"

# HTML 模板
INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Star Search</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .htmx-indicator {{ display: none; }}
        .htmx-request .htmx-indicator {{ display: inline; }}
        .htmx-request.htmx-indicator {{ display: inline; }}
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <h1 class="text-3xl font-bold text-center mb-8 text-gray-800">
            GitHub Star Search
        </h1>

        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <form hx-get="/search" hx-target="#results" hx-indicator="#loading">
                <div class="flex gap-4 mb-4">
                    <input
                        type="text"
                        name="q"
                        placeholder="搜索你的 Star 项目..."
                        class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                    >
                    <button
                        type="submit"
                        class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        搜索
                    </button>
                </div>
                <div class="flex gap-4 items-center text-sm text-gray-600">
                    <span>搜索模式:</span>
                    <label class="flex items-center gap-1">
                        <input type="radio" name="mode" value="hybrid" checked>
                        混合
                    </label>
                    <label class="flex items-center gap-1">
                        <input type="radio" name="mode" value="semantic">
                        语义
                    </label>
                    <label class="flex items-center gap-1">
                        <input type="radio" name="mode" value="keyword">
                        关键字
                    </label>
                    <span class="ml-4">数量:</span>
                    <select name="limit" class="border border-gray-300 rounded px-2 py-1">
                        <option value="10">10</option>
                        <option value="20" selected>20</option>
                        <option value="50">50</option>
                    </select>
                </div>
            </form>
        </div>

        <div id="loading" class="htmx-indicator text-center py-4">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p class="mt-2 text-gray-600">搜索中...</p>
        </div>

        <div id="results">
            <div class="text-center text-gray-500 py-8">
                输入关键词开始搜索
            </div>
        </div>

        <div class="text-center text-gray-400 text-sm mt-8">
            数据库状态: {total_repos} 个项目已索引
        </div>
    </div>
</body>
</html>
"""

RESULT_ITEM_HTML = """
<div class="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
    <div class="flex justify-between items-start mb-2">
        <a href="{html_url}" target="_blank" class="text-lg font-semibold text-blue-600 hover:underline">
            {full_name}
        </a>
        <div class="flex items-center gap-2 text-sm text-gray-500">
            {similarity_badge}
            <span class="bg-gray-100 px-2 py-1 rounded">{language}</span>
            <span>⭐ {stargazers_count}</span>
        </div>
    </div>
    <p class="text-gray-600 text-sm">{description}</p>
</div>
"""


def create_app(db_path: str | None = None) -> FastAPI:
    """创建 FastAPI 应用"""
    from ..core.database import StarDatabase
    from ..core.embedder import EmbeddingGenerator
    from ..core.searcher import HybridSearcher

    db_file = db_path or str(DEFAULT_DB_PATH)

    app = FastAPI(title="GitHub Star Search")

    # 初始化组件 (懒加载)
    _components: dict = {}

    def get_components():
        if not _components:
            _components["db"] = StarDatabase(db_file)
            _components["embedder"] = EmbeddingGenerator()
            _components["searcher"] = HybridSearcher(
                _components["db"], _components["embedder"]
            )
        return _components

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """主页"""
        components = get_components()
        status = components["db"].get_sync_status()
        return INDEX_HTML.format(total_repos=status["total_repos"])

    @app.get("/search", response_class=HTMLResponse)
    async def search(
        q: str = Query(..., min_length=1),
        mode: str = Query("hybrid"),
        limit: int = Query(20),
    ):
        """搜索 API - 返回 HTML 片段"""
        components = get_components()
        results = components["searcher"].search(q, mode=mode, limit=limit)

        if not results:
            return '<div class="text-center text-gray-500 py-8">未找到匹配的项目</div>'

        html_parts = [f'<div class="space-y-4"><p class="text-gray-600 mb-4">找到 {len(results)} 个结果</p>']

        for r in results:
            similarity = r.get("similarity")
            if similarity:
                similarity_badge = f'<span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">{similarity:.3f}</span>'
            else:
                similarity_badge = ""

            html_parts.append(
                RESULT_ITEM_HTML.format(
                    html_url=r["html_url"],
                    full_name=r["full_name"],
                    similarity_badge=similarity_badge,
                    language=r.get("language") or "-",
                    stargazers_count=r.get("stargazers_count", 0),
                    description=r.get("description") or "无描述",
                )
            )

        html_parts.append("</div>")
        return "".join(html_parts)

    @app.get("/api/search")
    async def api_search(
        q: str = Query(..., min_length=1),
        mode: str = Query("hybrid"),
        limit: int = Query(20),
    ):
        """搜索 API - 返回 JSON"""
        components = get_components()
        return components["searcher"].search(q, mode=mode, limit=limit)

    @app.get("/api/status")
    async def api_status():
        """状态 API"""
        components = get_components()
        return components["db"].get_sync_status()

    return app
