"""GitHub Star 项目数据模型"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StarredRepo:
    """Star 项目数据"""

    id: int
    full_name: str
    name: str
    owner: str
    html_url: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    language: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    stargazers_count: int = 0
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    starred_at: Optional[str] = None

    def to_search_text(self) -> str:
        """
        生成用于 embedding 的搜索文本
        格式: "项目名: 描述"
        """
        parts = [self.full_name]
        if self.description:
            parts.append(self.description)
        return ": ".join(parts)

    @classmethod
    def from_dict(cls, data: dict) -> "StarredRepo":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            full_name=data["full_name"],
            name=data["name"],
            owner=data.get("owner", ""),
            html_url=data["html_url"],
            description=data.get("description"),
            homepage=data.get("homepage"),
            language=data.get("language"),
            topics=data.get("topics", []),
            stargazers_count=data.get("stargazers_count", 0),
            updated_at=data.get("updated_at"),
            created_at=data.get("created_at"),
            starred_at=data.get("starred_at"),
        )
