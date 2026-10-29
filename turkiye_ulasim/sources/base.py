"""Kaynakların ortak hata ve yanıt biçimleri."""
from dataclasses import dataclass, field
from datetime import datetime, timezone


class SourceError(Exception):
    pass


class SourceNotFound(SourceError):
    pass


class SourceUnsupported(SourceError):
    pass


class SourceRateLimited(SourceError):
    def __init__(self, retry_after: int, source: str = "İETT", period: str = "saatlik"):
        super().__init__(f"{source} kaynağının {period} istek bütçesi doldu; daha sonra yeniden deneyin.")
        self.retry_after = retry_after


@dataclass
class LiveResult:
    data: list[dict]
    warnings: list[str] = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    cached: bool = False
