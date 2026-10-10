
import io
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon

from app.core.errors import GeospatialProcessingError
from app.main import app
from app.core.config import settings
from app.services.measurement import measure_file

client = TestClient(app)


def test_rejects_zip_path_traversal():
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "../../malicious.txt",
            "This file must not be extracted outside the temporary directory.",
        )
        archive.writestr("sample.shp", b"not a real shapefile")

    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "unsafe.zip",
                buffer.getvalue(),
                "application/zip",
            )
        },
    )

    assert response.status_code == 400
    assert "unsafe file path" in response.json()["error"]["message"].lower()


def test_rejects_oversized_upload():
    oversized_content = b"A" * (settings.max_upload_size_bytes + 1)

    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "large.geojson",
                oversized_content,
                "application/geo+json",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "UPLOAD_TOO_LARGE"


def test_rejects_shapefile_without_crs():
    gdf = gpd.GeoDataFrame(
        {"name": ["Test parcel"]},
        geometry=[
            Polygon(
                [
                    (78.4, 17.4),
                    (78.401, 17.4),
                    (78.401, 17.401),
                    (78.4, 17.401),
                    (78.4, 17.4),
                ]
            )
        ],
    )

    # Deliberately do not assign a CRS.
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        shp_path = temp_path / "missing_crs.shp"
        gdf.to_file(shp_path)

        zip_path = temp_path / "missing_crs.zip"

        with zipfile.ZipFile(zip_path, "w") as archive:
            for file_path in temp_path.glob("missing_crs.*"):
                if file_path.suffix.lower() != ".zip":
                    archive.write(file_path, arcname=file_path.name)

        with pytest.raises(
            GeospatialProcessingError,
            match="no CRS",
        ):
            measure_file("missing_crs.zip", zip_path.read_bytes())
