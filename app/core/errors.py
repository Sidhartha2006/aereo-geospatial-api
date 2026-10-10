from fastapi import Request
from fastapi.responses import JSONResponse

class GeospatialProcessingError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "GEOSPATIAL_PROCESSING_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code

async def geospatial_error_handler(request: Request, exc: GeospatialProcessingError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "path": request.url.path}},
    )
