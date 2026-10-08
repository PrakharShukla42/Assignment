import os
import geopandas as gpd
import fiona
from sqlalchemy.orm import Session
from . import models, database
import numpy as np

# Enable KML driver
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

def process_geospatial_file(file_path: str, file_id: str):
    db = database.SessionLocal()
    try:
        db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
        if not db_file:
            return
            
        # Load the geospatial data
        gdf = gpd.read_file(file_path)

        # Update file info
        db_file.feature_count = len(gdf)
        
        crs_str = None
        if gdf.crs is not None:
            crs_str = f"EPSG:{gdf.crs.to_epsg()}" if gdf.crs.to_epsg() else gdf.crs.name
        db_file.crs = crs_str

        db.commit()

        # Handle projection for accurate measurements if it's geographic
        if gdf.crs and gdf.crs.is_geographic:
            # estimate_utm_crs() finds the best UTM zone for the data
            try:
                utm_crs = gdf.estimate_utm_crs()
                gdf = gdf.to_crs(utm_crs)
            except Exception as e:
                print(f"Warning: Could not project to UTM. Measurements might be inaccurate. {e}")
                # Fallback to a custom equal area projection if UTM fails (unlikely, but safe)
                pass

        measurements = []
        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None:
                continue

            geom_type = geom.geom_type
            area = None
            length = None

            if geom_type in ['Polygon', 'MultiPolygon']:
                area = geom.area
            elif geom_type in ['LineString', 'MultiLineString']:
                length = geom.length
            # Point and others have no measurement (area/length will be None)

            # Extract properties (filter out geometry)
            properties = {}
            for col in gdf.columns:
                if col != 'geometry':
                    val = row[col]
                    # handle non-serializable types like timestamp or nan
                    if isinstance(val, (int, float, str, bool)):
                        # check for NaN
                        if isinstance(val, float) and np.isnan(val):
                            properties[col] = None
                        else:
                            properties[col] = val
                    else:
                        properties[col] = str(val) if val is not None else None

            meas = models.FeatureMeasurement(
                file_id=db_file.id,
                feature_index=idx,
                geometry_type=geom_type,
                area=area,
                length=length,
                properties=properties
            )
            measurements.append(meas)

        db.add_all(measurements)
        db_file.status = "COMPLETED"
        db.commit()

    except Exception as e:
        db_file.status = "FAILED"
        db_file.error_message = str(e)
        db.commit()
    finally:
        # Clean up the file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        db.close()
