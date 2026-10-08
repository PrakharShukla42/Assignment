# Geospatial File Measurement API

A backend service built with FastAPI that accepts geospatial files (Shapefile in `.zip` or `.kml`), processes the features within them, and returns measurement information such as area for polygons and length for linestrings.

## Minimum Requirements Satisfied
- **Backend Framework:** FastAPI.
- **File Upload:** Accepts `.zip` containing a Shapefile and `.kml` via `POST /api/files/`.
- **File Processing:** Extracts feature ID/index, geometry type, geometry properties, and CRS. Handles unsupported geometries for measurements gracefully.
- **Measurements:** Calculates Area for Polygons and Length for LineStrings.
- **CRS Handling:** Correctly handles geographic coordinates (like EPSG:4326) by projecting the geometry to an appropriate UTM projected coordinate system (estimated based on the centroid of the geometries) before calculating accurate planar measurements in meters.
- **API Design:** Endpoints for upload, file information, and measurements.

## Setup and Run Locally

### Prerequisites
- Python 3.9+
- SQLite (built-in with Python)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn python-multipart geopandas fiona shapely pyproj sqlalchemy
   ```

4. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://127.0.0.1:8000`. You can also access the interactive API documentation at `http://127.0.0.1:8000/docs`.

## API Documentation

### 1. Upload File
- **Endpoint:** `POST /api/files/`
- **Description:** Uploads a `.zip` (Shapefile) or `.kml` file. Processing happens in the background.
- **Request Body:** `multipart/form-data` with a `file` field.
- **Example Response:**
  ```json
  {
    "id": "1a2b3c4d",
    "filename": "survey.kml",
    "feature_count": 0,
    "crs": null,
    "status": "PROCESSING"
  }
  ```

### 2. File Information
- **Endpoint:** `GET /api/files/{id}/`
- **Description:** Returns information about the uploaded file.
- **Example Response:**
  ```json
  {
    "id": "1a2b3c4d",
    "filename": "survey.kml",
    "feature_count": 120,
    "crs": "EPSG:4326",
    "status": "COMPLETED"
  }
  ```

### 3. Measurements
- **Endpoint:** `GET /api/files/{id}/measurements/`
- **Description:** Returns the processed measurements for the features in the file.
- **Example Response:**
  ```json
  {
    "id": "1a2b3c4d",
    "measurements": [
      {
        "feature_index": 0,
        "geometry_type": "Polygon",
        "area": 1234.56,
        "length": null,
        "properties": {
          "Name": "Plot A",
          "Type": "Residential"
        }
      },
      {
        "feature_index": 1,
        "geometry_type": "LineString",
        "area": null,
        "length": 456.78,
        "properties": {
          "Name": "Road 1"
        }
      },
      {
        "feature_index": 2,
        "geometry_type": "Point",
        "area": null,
        "length": null,
        "properties": {
          "Name": "Landmark"
        }
      }
    ]
  }
  ```

## Architecture

- **Application structure:**
  - `app/main.py`: Entry point for the FastAPI application, containing the route handlers.
  - `app/services.py`: Contains the core business logic for processing geospatial files.
  - `app/models.py`: SQLAlchemy ORM models for storing file and feature metadata.
  - `app/schemas.py`: Pydantic schemas for request validation and response serialization.
  - `app/database.py`: Database connection setup.
- **File-processing flow:**
  1. User uploads a file via the `POST /api/files/` endpoint.
  2. The file is saved to a temporary directory on the server.
  3. A new database entry is created with a `PROCESSING` status.
  4. A background task is dispatched to process the file using GeoPandas, ensuring the main API thread remains unblocked and responsive.
- **Measurement calculation flow:**
  1. The background worker loads the file into a GeoPandas GeoDataFrame.
  2. The CRS is detected.
  3. The system checks if the coordinate reference system (CRS) is geographic (e.g. latitude/longitude in EPSG:4326).
  4. If geographic, the system calculates the optimal Universal Transverse Mercator (UTM) projection zone based on the centroid of the data and projects the geometries to this new CRS.
  5. It iterates through all features, computing `.area` for Polygons/MultiPolygons and `.length` for LineStrings/MultiLineStrings.
  6. The metadata and computed measurements are stored in the database, and the file status is updated to `COMPLETED`. The temp file is deleted.
- **CRS handling:**
  By leveraging `gdf.estimate_utm_crs()`, the application dynamically identifies the most appropriate local UTM zone for the uploaded data's bounding box/centroid. This prevents errors introduced by attempting planar measurements on an unprojected globe, and provides a robust localization without hardcoding a specific EPSG zone.

## Design Decisions

- **FastAPI over Django:** FastAPI is significantly lighter, has built-in async support for better I/O bound performance (e.g., file uploads), and natively integrates with Pydantic for data validation, providing automatic OpenAPI documentation.
- **SQLite Database:** For this assignment, an embedded SQLite database is used. This allows data persistence and tracking of background job statuses without the heavy requirement of a separate PostgreSQL/PostGIS database setup, making local testing trivial.
- **Background Tasks:** Geospatial file processing (especially for large Shapefiles) can be CPU-intensive and time-consuming. Using FastAPI's `BackgroundTasks` ensures that the client receives an immediate response with a tracking ID, rather than timing out on the initial upload request.
- **GeoPandas + Fiona:** GeoPandas provides a very high-level and easy-to-use API for vector data. Combined with Fiona (with KML driver enabled), it cleanly handles various input formats (`.zip` shapefiles, `.kml`) and seamlessly provides CRS detection and reprojection. 
- **Missing Measurement Logic:** Geometries that don't logically have area (like points) simply return `null` for measurements, rather than throwing an error, meeting the requirement for graceful handling.

## Learning and Future Scope

- **Learning:** Improved understanding of dynamic CRS reprojection and efficient file handling using FastAPI's background tasks and dependency injection.
- **Future Scope:** 
  - Add robust celery-based queues (e.g., Redis + Celery) for horizontal scaling of the background processing tasks.
  - Switch to PostGIS for spatial queries and advanced bounding box searches.
  - Implement caching for the measurement endpoints.
  - Add a feature to view geometry on an interactive map using Folium or similar libraries.
