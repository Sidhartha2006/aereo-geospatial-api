
@'
# AEREO Geospatial Measurement API

A REST API built with FastAPI to process vector geospatial files and calculate feature measurements. It supports GeoJSON files and ZIP archives containing a Shapefile.

## Features

- Upload GeoJSON Feature and FeatureCollection files.
- Upload ZIP archives containing one Shapefile.
- Calculate polygon area and geometry length in metres.
- Use ellipsoidal geodesic measurements.
- Return feature counts and geometry-type counts.
- Report source coordinate reference system (CRS) and input bounds.
- Validate uploaded files and reject unsupported or unsafe input.
- Enforce upload-size and ZIP archive limits.
- Return structured JSON error responses.
- Provide interactive API documentation through Swagger UI.
- Configure application logging.
- Run the API in Docker with a health check.

## Technology Stack

- Python
- FastAPI
- Uvicorn
- GeoPandas
- Shapely
- PyProj
- Pydantic Settings
- Pytest
- Docker and Docker Compose

## Project Structure

```text
aereo-geospatial-api/
├── app/
│   ├── api/
│   │   └── endpoints/
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   └── logging.py
│   ├── schemas/
│   ├── services/
│   └── main.py
├── samples/
│   ├── sample.geojson
│   └── shapefile_test.zip
├── tests/
├── requirements.txt
├── requirements-docker.txt
├── Dockerfile
├── compose.yaml
└── README.md
```

## Requirements

For Docker:
- Docker Desktop with the Docker engine running.
- Docker Compose.

For local development:
- Python with compatible project dependencies installed.
- The packages listed in the relevant requirements file.

## Run with Docker

Build the image and start the API:

```powershell
docker compose up -d --build
```

Check the container status:

```powershell
docker compose ps
```

View application logs:

```powershell
docker compose logs --tail=50 api
```

Stop the service:

```powershell
docker compose down
```

## Run Locally

Install the runtime dependencies:

```powershell
python -m pip install -r requirements-docker.txt
```

Install test dependencies if they are not already installed:

```powershell
python -m pip install pytest httpx
```

Start the development server:

```powershell
python -m uvicorn app.main:app --reload
```

The local API will be available at:

- Health check: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

## API Endpoints

### Health Check

`GET /health`

Example:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Example response:

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Geospatial Measurement

`POST /api/v1/measurements`

Send a multipart form upload using the field name `file`.

#### Upload GeoJSON

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/measurements" -F "file=@samples/sample.geojson"
```

#### Upload a Shapefile ZIP

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/measurements" -F "file=@samples/shapefile_test.zip"
```

A successful request returns JSON containing the filename, source CRS, measurement method, feature count, geometry-type counts, total area, total length, bounds, and individual feature measurements.

## Response Fields

| Field | Description |
|---|---|
| `filename` | Uploaded filename |
| `source_crs` | Detected or assumed source CRS |
| `measurement_method` | Method used for geodesic measurements |
| `feature_count` | Number of processed features |
| `geometry_type_counts` | Count of each geometry type |
| `total_area_m2` | Total polygon area in square metres |
| `total_length_m` | Total geometry length in metres |
| `bounds` | Input-coordinate bounds |
| `features` | Per-feature geometry measurements and properties |

Area and length totals depend on the geometries present in the input.

## Error Handling

The API returns structured JSON errors for rejected uploads and geospatial processing failures.

Possible HTTP status codes include:

- `400 Bad Request` — Invalid or malformed geospatial input.
- `413 Payload Too Large` — Upload exceeds the configured size limit.
- `415 Unsupported Media Type` — Unsupported file type.
- `500 Internal Server Error` — Unexpected server-side failure.

The exact response depends on the error encountered.

## Configuration and Security

Application settings are defined in `app/core/config.py`. Configurable settings include upload-size limits, ZIP archive limits, application version, API prefix, and log level.

The API validates geospatial input and applies restrictions to archive processing. Do not expose the service publicly without reviewing deployment security, network access, and production configuration.

## Run Tests

Run the automated test suite from the project root:

```powershell
python -m pytest -v
```

For a shorter test summary:

```powershell
python -m pytest -q
```

The current development test suite has passed 13 tests. Test results may change as the application is modified.

## Geospatial Notes

- GeoJSON without a CRS declaration is interpreted as WGS84 (EPSG:4326).
- Measurements use ellipsoidal geodesic calculations.
- Area is reported in square metres and length in metres.
- Bounds are reported in the input coordinate system.
- Shapefile ZIP archives must contain exactly one `.shp` file and the required companion files.
- Input geometry and CRS validity affect whether a measurement can be calculated correctly.

## License

Add the license applicable to this project before distributing it.
'@ | Set-Content -Encoding utf8 README.md

