import logging

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import (
    GeospatialProcessingError,
    geospatial_error_handler,
)
from app.core.logging import configure_logging
from app.schemas.measurement import HealthResponse, MeasurementResponse
from app.services.measurement import measure_file

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Measure geospatial features from GeoJSON and Shapefile ZIP uploads.",
)

app.add_exception_handler(
    GeospatialProcessingError,
    geospatial_error_handler,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    logger.info("Health check requested")
    return HealthResponse(status="ok", version=settings.app_version)


@app.post(
    f"{settings.api_prefix}/measurements",
    response_model=MeasurementResponse,
    tags=["Measurements"],
)
async def create_measurement(file: UploadFile = File(...)):
    filename = file.filename or "upload"
    logger.info("Measurement request received for filename=%s", filename)

    content = await file.read(settings.max_upload_size_bytes + 1)

    if len(content) > settings.max_upload_size_bytes:
        logger.warning("Upload rejected because it exceeds the size limit")
        raise GeospatialProcessingError(
            "Upload exceeds the configured size limit.",
            413,
            "UPLOAD_TOO_LARGE",
        )

    result = measure_file(filename, content)
    logger.info(
        "Measurement completed for filename=%s, feature_count=%s",
        filename,
        result.feature_count,
    )
    return result
