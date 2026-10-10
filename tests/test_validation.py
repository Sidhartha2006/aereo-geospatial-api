
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_rejects_unsupported_file_type():
    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "document.pdf",
                b"this is not a supported geospatial file",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_rejects_malformed_geojson():
    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "malformed.geojson",
                b'{"type": "InvalidData"}',
                "application/geo+json",
            )
        },
    )

    assert response.status_code == 400
    assert "Expected a GeoJSON FeatureCollection or Feature" in (
        response.json()["error"]["message"]
    )


def test_rejects_empty_feature_collection():
    empty_geojson = b'{"type": "FeatureCollection", "features": []}'

    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "empty.geojson",
                empty_geojson,
                "application/geo+json",
            )
        },
    )

    assert response.status_code == 400
    assert "No features were found" in response.json()["error"]["message"]


def test_rejects_invalid_zip_archive():
    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "invalid.zip",
                b"this is not a valid ZIP archive",
                "application/zip",
            )
        },
    )

    assert response.status_code == 400
    assert "Invalid ZIP archive" in response.json()["error"]["message"]



def test_rejects_invalid_polygon_geometry():
    invalid_geojson = b"""
    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Invalid polygon"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [2, 2],
                        [0, 2],
                        [2, 0],
                        [0, 0]
                    ]]
                }
            }
        ]
    }
    """

    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "invalid_polygon.geojson",
                invalid_geojson,
                "application/geo+json",
            )
        },
    )

    assert response.status_code == 400
    assert "invalid geometry" in response.json()["error"]["message"].lower()

def test_rejects_invalid_polygon_geometry():
    invalid_geojson = b"""
    {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Invalid polygon"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0], [2, 2], [0, 2], [2, 0], [0, 0]
                ]]
            }
        }]
    }
    """

    response = client.post(
        "/api/v1/measurements",
        files={"file": ("invalid.geojson", invalid_geojson, "application/geo+json")},
    )

    assert response.status_code == 400
    assert "invalid geometry" in response.json()["error"]["message"].lower()


def test_rejects_feature_without_geometry():
    geojson = b"""
    {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Missing geometry"},
            "geometry": null
        }]
    }
    """

    response = client.post(
        "/api/v1/measurements",
        files={"file": ("missing.geojson", geojson, "application/geo+json")},
    )

    assert response.status_code == 400
    assert "no geometry" in response.json()["error"]["message"].lower()
