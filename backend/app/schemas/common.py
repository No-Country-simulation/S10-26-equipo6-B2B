"""Esquemas genéricos compartidos por la API."""

from typing import Any

from pydantic import BaseModel, Field


class PaginatedResponse[T](BaseModel):
    """Respuesta paginada estándar con metadatos calculados."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = 0
    has_next: bool = False

    def model_post_init(self, __context: Any) -> None:
        """Calcula ``total_pages`` y ``has_next`` a partir del total y la página."""
        self.total_pages = (self.total + self.page_size - 1) // self.page_size
        self.has_next = self.page < self.total_pages
