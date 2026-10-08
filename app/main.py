import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, database
from .services import process_geospatial_file

# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Geospatial File Measurement API",
    description="API to upload Shapefiles/KML and calculate measurements.",
    version="1.0.0"
)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

TEMP_DIR = "./temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/api/files/", response_model=schemas.FileResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not (file.filename.endswith('.zip') or file.filename.endswith('.kml')):
        raise HTTPException(status_code=400, detail="Only .zip (Shapefile) or .kml files are supported.")

    file_id = uuid.uuid4().hex[:8]
    temp_file_path = os.path.join(TEMP_DIR, f"{file_id}_{file.filename}")

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create DB entry
    db_file = models.UploadedFile(id=file_id, filename=file.filename, status="PROCESSING")
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Process in background with a new session
    background_tasks.add_task(process_geospatial_file, temp_file_path, db_file.id)

    return db_file

@app.get("/api/files/{id}/", response_model=schemas.FileResponse)
def get_file_info(id: str, db: Session = Depends(get_db)):
    db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    return db_file

@app.get("/api/files/{id}/measurements/", response_model=schemas.FileMeasurementsResponse)
def get_file_measurements(id: str, db: Session = Depends(get_db)):
    db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if db_file.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"File processing is not complete. Status: {db_file.status}")

    return {"id": db_file.id, "measurements": db_file.measurements}
