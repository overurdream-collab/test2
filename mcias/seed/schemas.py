from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    organization_name: str = Field(pattern=r"^SYN-")
    username: str = Field(pattern=r"^SYN-")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    claimed_amount: Decimal = Field(ge=0, decimal_places=4)
    permissions: list[str]
