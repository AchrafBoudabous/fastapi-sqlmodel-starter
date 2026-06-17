# Import all table models here so Alembic can discover them via SQLModel.metadata.
# Add new models as they are created — no other file needs to change.
from app.models.item import Item  # noqa: F401
from app.models.user import User  # noqa: F401
