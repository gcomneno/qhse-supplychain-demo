# Warning Cleanup -- Pydantic v2 & UTC Timestamps

This patch removes deprecation warnings and improves temporal
correctness.

## 1. Pydantic v2 Migration

Replace class-based Config:

``` python
class SupplierOut(BaseModel):
    class Config:
        from_attributes = True
```

With:

``` python
from pydantic import BaseModel, ConfigDict

class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

Apply same change to all response models.

------------------------------------------------------------------------

## 2. UTC Aware Timestamps

Replace:

``` python
datetime.utcnow()
```

With:

``` python
from datetime import datetime, UTC

datetime.now(UTC)
```

Rationale:

-   Avoid naive datetime objects
-   Ensure timezone consistency
-   Future-proof against Python deprecation

------------------------------------------------------------------------

Result:

-   No Pydantic v2 warnings
-   No SQLAlchemy datetime deprecation warnings
-   Improved temporal correctness
