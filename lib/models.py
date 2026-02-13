from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .database import Base

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    filepath = Column(String, unique=True, index=True)
    title = Column(String, index=True, nullable=True)
    artist = Column(String, index=True, nullable=True)
    album = Column(String, index=True, nullable=True)
    genre = Column(String, index=True, nullable=True)
    year = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
