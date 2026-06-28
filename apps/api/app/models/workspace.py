import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True, index=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    owner: Mapped["User | None"] = relationship(back_populates="workspaces")  # noqa: F821
    documents: Mapped[list["Document"]] = relationship(back_populates="workspace")  # noqa: F821
