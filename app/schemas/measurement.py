from typing import Any
from pydantic import BaseModel, Field

class FeatureMeasurement(BaseModel):
    feature_index: int
    geometry_type: str
    area_m2: float | None = None
    length_m: float | None = None
    properties: dict[str, Any] = Field(default_factory=dict)

class MeasurementResponse(BaseModel):
    filename: str
    source_crs: str
    measurement_method: str
    feature_count: int
    geometry_type_counts: dict[str, int]
    total_area_m2: float | None = None
    total_length_m: float | None = None
    bounds: list[float]
    features: list[FeatureMeasurement]

class HealthResponse(BaseModel):
    status: str
    version: str
