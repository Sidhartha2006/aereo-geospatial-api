from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_valid_geojson_upload():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Test parcel"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [78.4, 17.4],
                        [78.401, 17.4],
                        [78.401, 17.401],
                        [78.4, 17.401],
                        [78.4, 17.4]
                    ]]
                }
            }
        ]
    }

    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "test.geojson",
                __import__("json").dumps(geojson),
                "application/geo+json",
            )
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["feature_count"] == 1
    assert result["geometry_type_counts"]["Polygon"] == 1
    assert result["total_area_m2"] > 0


def test_unsupported_file_type():
    response = client.post(
        "/api/v1/measurements",
        files={"file": ("test.pdf", b"not a geospatial file", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_invalid_geojson_structure():
    response = client.post(
        "/api/v1/measurements",
        files={
            "file": (
                "invalid.geojson",
                b'{"type": "InvalidData"}',
                "application/geo+json",
            )
        },
    )

    assert response.status_code == 400
    assert "Expected a GeoJSON" in response.json()["error"]["message"]
