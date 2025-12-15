"""GitHub Star 语义搜索 CLI"""

import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

app = typer.Typer(name="ghstar", help="GitHub Star 项目语义搜索工具")
console = Console()

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "stars.duckdb"


@app.command()
def sync(
    force: bool = typer.Option(False, "--force", "-f", help="强制全量同步"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="数据库文件路径"),
):
    """
    同步 GitHub Star 项目到本地数据库

    首次运行会全量同步所有 Star 项目
    """
    from .core.database import StarDatabase
    from .core.embedder import EmbeddingGenerator
    from .core.fetcher import GitHubStarFetcher

    db_file = str(db_path) if db_path else str(DEFAULT_DB_PATH)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        # 1. 获取 Star 项目
        task = progress.add_task("[cyan]获取 GitHub Star 项目...", total=None)
        fetcher = GitHubStarFetcher()
        repos = list(fetcher.fetch_all_stars())
        progress.update(
            task, completed=100, total=100, description=f"[green]获取到 {len(repos)} 个项目"
        )

        # 2. 生成 Embedding
        console.print("\n[cyan]加载 Embedding 模型...[/cyan]")
        embedder = EmbeddingGenerator()

        task = progress.add_task(
            "[cyan]生成 Embedding...", total=len(repos)
        )
        texts = [r.to_search_text() for r in repos]
        embeddings = embedder.encode(texts, batch_size=32, show_progress=False)
        progress.update(task, completed=len(repos))

        # 3. 存入数据库
        task = progress.add_task("[cyan]保存数据...", total=None)
        db = StarDatabase(db_file)
        db.save_repos(repos, texts, embeddings)
        progress.update(task, completed=100, total=100, description="[green]数据已保存")

    # 显示统计
    status = db.get_sync_status()
    console.print(f"\n[bold green]同步完成![/bold green]")
    console.print(f"  总项目数: {status['total_repos']}")
    console.print(f"  已索引: {status['indexed_repos']}")
    console.print(f"  最后同步: {status['last_sync']}")


@app.command()
def search(
    query: str = typer.Argument(..., help="搜索查询"),
    limit: int = typer.Option(10, "--limit", "-n", help="返回结果数量"),
    mode: str = typer.Option(
        "hybrid", "--mode", "-m", help="搜索模式: semantic/keyword/hybrid"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 格式输出"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="数据库文件路径"),
):
    """
    搜索 Star 项目

    支持语义搜索、关键字搜索或混合搜索

    示例:
      ghstar search "机器学习框架"
      ghstar search "web scraping" --mode semantic
      ghstar search "react" --mode keyword -n 20
    """
    from .core.database import StarDatabase
    from .core.embedder import EmbeddingGenerator
    from .core.searcher import HybridSearcher

    db_file = str(db_path) if db_path else str(DEFAULT_DB_PATH)

    db = StarDatabase(db_file)
    embedder = EmbeddingGenerator()
    searcher = HybridSearcher(db, embedder)

    with console.status("[bold green]搜索中..."):
        results = searcher.search(query, mode=mode, limit=limit)

    if not results:
        console.print("[yellow]未找到匹配的项目[/yellow]")
        return

    if json_output:
        import json

        console.print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    # Rich 表格输出
    table = Table(title=f"搜索结果: {query}")
    table.add_column("项目", style="cyan", no_wrap=True)
    table.add_column("描述", max_width=50)
    table.add_column("语言", style="yellow")
    table.add_column("Stars", justify="right")
    table.add_column("相似度", justify="right")

    for r in results:
        similarity = f"{r['similarity']:.3f}" if r.get("similarity") else "-"
        desc = r.get("description") or ""
        if len(desc) > 50:
            desc = desc[:47] + "..."
        table.add_row(
            r["full_name"],
            desc,
            r.get("language") or "-",
            str(r.get("stargazers_count", "-")),
            similarity,
        )

    console.print(table)


@app.command()
def status(
    db_path: Optional[Path] = typer.Option(None, "--db", help="数据库文件路径"),
):
    """
    查看数据库状态
    """
    from .core.database import StarDatabase

    db_file = str(db_path) if db_path else str(DEFAULT_DB_PATH)

    if not Path(db_file).exists():
        console.print("[yellow]数据库不存在，请先运行 'ghstar sync' 同步数据[/yellow]")
        return

    db = StarDatabase(db_file)
    status = db.get_sync_status()

    console.print("\n[bold]数据库状态[/bold]")
    console.print(f"  数据库路径: {db_file}")
    console.print(f"  总项目数: {status['total_repos']}")
    console.print(f"  已索引: {status['indexed_repos']}")
    console.print(f"  最后同步: {status['last_sync']}")


@app.command(name="open")
def open_repo(
    query: str = typer.Argument(..., help="搜索查询"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="数据库文件路径"),
):
    """
    搜索并在浏览器中打开第一个结果
    """
    from .core.database import StarDatabase
    from .core.embedder import EmbeddingGenerator
    from .core.searcher import HybridSearcher

    db_file = str(db_path) if db_path else str(DEFAULT_DB_PATH)

    db = StarDatabase(db_file)
    embedder = EmbeddingGenerator()
    searcher = HybridSearcher(db, embedder)

    results = searcher.search(query, limit=1)
    if results:
        url = results[0]["html_url"]
        console.print(f"打开: [link={url}]{url}[/link]")
        webbrowser.open(url)
    else:
        console.print("[red]未找到匹配的项目[/red]")


@app.command()
def web(
    port: int = typer.Option(8000, "--port", "-p", help="端口号"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="主机地址"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="数据库文件路径"),
):
    """
    启动 Web 界面
    """
    import uvicorn

    from .web.app import create_app

    db_file = str(db_path) if db_path else str(DEFAULT_DB_PATH)

    console.print(f"启动 Web 服务: http://{host}:{port}")
    uvicorn_app = create_app(db_file)
    uvicorn.run(uvicorn_app, host=host, port=port)


if __name__ == "__main__":
    app()
