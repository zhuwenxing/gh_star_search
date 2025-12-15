"""使用 gh cli 获取 GitHub Star 项目数据"""

import json
import subprocess
from typing import Iterator

from ..models.repo import StarredRepo


class GitHubStarFetcher:
    """从 GitHub 获取 Star 项目"""

    def check_gh_auth(self) -> bool:
        """检查 gh cli 是否已登录"""
        try:
            subprocess.run(
                ["gh", "auth", "status"],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def fetch_all_stars(self) -> Iterator[StarredRepo]:
        """
        获取所有 Star 项目
        使用 gh api 的 --paginate 选项自动处理分页
        """
        if not self.check_gh_auth():
            raise RuntimeError("请先运行 'gh auth login' 登录 GitHub")

        cmd = [
            "gh",
            "api",
            "user/starred",
            "--paginate",
            "--jq",
            ".[] | {id, full_name, name, owner: .owner.login, description, html_url, homepage, language, topics, stargazers_count, updated_at, created_at}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split("\n"):
            if line:
                data = json.loads(line)
                yield StarredRepo.from_dict(data)

    def fetch_stars_count(self) -> int:
        """获取 Star 项目总数"""
        if not self.check_gh_auth():
            raise RuntimeError("请先运行 'gh auth login' 登录 GitHub")

        cmd = [
            "gh",
            "api",
            "user/starred",
            "--jq",
            "length",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
