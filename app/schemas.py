from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class FileResponse(BaseModel):
    id: str
    filename: str
    feature_count: int
    crs: Optional[str] = None
    status: str

    class Config:
        orm_mode = True
        from_attributes = True

class FeatureMeasurementResponse(BaseModel):
    feature_index: int
    geometry_type: str
    area: Optional[float] = None
    length: Optional[float] = None
    properties: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        from_attributes = True

class FileMeasurementsResponse(BaseModel):
    id: str
    measurements: List[FeatureMeasurementResponse]
