from pydantic import BaseModel


class Open5eRow(BaseModel):
    """Lightweight row for a monster picker (not the full statblock)."""
    slug: str
    name: str
    type: str | None = None
    challenge_rating: str | None = None
    cr: float | None = None
    hit_points: int | None = None
    document: str | None = None


class Open5eBrowse(BaseModel):
    count: int              # total matches across all pages
    page: int               # current page (1-based)
    num_pages: int
    results: list[Open5eRow]


class Open5eSource(BaseModel):
    slug: str
    name: str | None = None


class BulkImportRequest(BaseModel):
    slugs: list[str]


class BulkImportResult(BaseModel):
    imported: list[str] = []   # newly created (or already present) slugs
    failed: list[str] = []     # not found on Open5e / errored
