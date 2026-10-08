import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, index=True, default=lambda: uuid.uuid4().hex[:8])
    filename = Column(String, index=True)
    feature_count = Column(Integer, default=0)
    crs = Column(String, nullable=True)
    status = Column(String, default="PROCESSING") # PROCESSING, COMPLETED, FAILED
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    measurements = relationship("FeatureMeasurement", back_populates="file", cascade="all, delete-orphan")

class FeatureMeasurement(Base):
    __tablename__ = "feature_measurements"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("uploaded_files.id"))
    feature_index = Column(Integer)
    geometry_type = Column(String)
    area = Column(Float, nullable=True)
    length = Column(Float, nullable=True)
    properties = Column(JSON, nullable=True)

    file = relationship("UploadedFile", back_populates="measurements")
