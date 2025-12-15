# gh-star-search

GitHub Star 项目语义搜索工具。使用 sentence-transformers 生成向量嵌入，支持语义搜索、关键字搜索和混合搜索。

## 功能特性

- **语义搜索**: 基于 sentence-transformers 的向量相似度搜索
- **关键字搜索**: 传统的全文搜索
- **混合搜索**: 使用 RRF (Reciprocal Rank Fusion) 算法融合两种搜索结果
- **本地存储**: 使用 DuckDB 存储数据和向量索引
- **CLI 工具**: 命令行界面，支持多种操作
- **Web 界面**: 基于 FastAPI 的 Web 搜索界面

## 安装

```bash
# 克隆仓库
git clone https://github.com/zhuwenxing/gh_star_search.git
cd gh_star_search

# 使用 uv 安装
uv sync

# 或使用 pip
pip install -e .
```

## 前置要求

- Python >= 3.10
- [GitHub CLI (gh)](https://cli.github.com/) 已安装并登录

```bash
# 安装 gh cli (macOS)
brew install gh

# 登录 GitHub
gh auth login
```

## 使用方法

### 同步 Star 项目

首次使用需要同步你的 GitHub Star 项目到本地数据库：

```bash
ghstar sync
```

这会：
1. 使用 `gh` CLI 获取你所有的 Star 项目
2. 使用 sentence-transformers 生成向量嵌入
3. 存储到本地 DuckDB 数据库

### 搜索

```bash
# 默认混合搜索
ghstar search "机器学习框架"

# 语义搜索
ghstar search "web scraping" --mode semantic

# 关键字搜索
ghstar search "react" --mode keyword

# 限制结果数量
ghstar search "database" -n 20

# JSON 格式输出
ghstar search "cli tool" --json
```

### 快速打开项目

搜索并在浏览器中打开第一个结果：

```bash
ghstar open "vector database"
```

### 查看状态

```bash
ghstar status
```

### Web 界面

启动 Web 服务：

```bash
ghstar web

# 指定端口
ghstar web -p 8080
```

## 搜索模式

| 模式 | 说明 |
|------|------|
| `hybrid` | 混合搜索（默认），融合语义和关键字搜索结果 |
| `semantic` | 纯语义搜索，基于向量相似度 |
| `keyword` | 纯关键字搜索，基于全文匹配 |

## 技术栈

- **CLI**: [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/)
- **向量嵌入**: [sentence-transformers](https://www.sbert.net/)
- **数据库**: [DuckDB](https://duckdb.org/)
- **Web**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)

## License

MIT
