from collections.abc import Generator
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, create_engine
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


class MeasurementRow(Base):
    __tablename__ = "measurements"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    foo: Mapped[float]
    bar: Mapped[float]
    buzz: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def build_session_factory(settings: Settings) -> sessionmaker[Session]:
    if not settings.database_url.startswith("postgresql+psycopg://"):
        raise ValueError("DATABASE_URL must use postgresql+psycopg")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database(factory: sessionmaker[Session]) -> None:
    engine = factory.kw["bind"]
    if engine is not None:
        Base.metadata.create_all(engine)


def get_session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as session:
        yield session
