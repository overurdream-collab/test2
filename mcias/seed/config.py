from dataclasses import dataclass
from sqlalchemy.engine import make_url

@dataclass(frozen=True)
class SeedConfig:
    database_url: str
    environment: str
    dataset: str = "workspace-v1"
    count: int = 12

    def validate(self):
        url = make_url(self.database_url)
        if self.environment != "development" or url.get_backend_name() != "postgresql" or not url.database or not url.database.endswith("_e2e"):
            raise ValueError("seed requires development and a dedicated PostgreSQL *_e2e database")
        if self.dataset != "workspace-v1" or not 1 <= self.count <= 100000:
            raise ValueError("unsupported dataset or claim count")
