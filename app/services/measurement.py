
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

import geopandas as gpd
from pyproj import CRS, Transformer
from shapely.geometry import shape
from shapely.ops import transform

from app.core.config import settings
from app.core.errors import GeospatialProcessingError
from app.schemas.measurement import FeatureMeasurement, MeasurementResponse


def _validate_geojson(data):
    """Validate the basic structure of a GeoJSON Feature or FeatureCollection."""
    if not isinstance(data, dict):
        raise GeospatialProcessingError("GeoJSON root must be an object.")

    if data.get("type") == "FeatureCollection":
        features = data.get("features")
    elif data.get("type") == "Feature":
        features = [data]
    else:
        raise GeospatialProcessingError(
            "Expected a GeoJSON FeatureCollection or Feature."
        )

    if not isinstance(features, list) or not features:
        raise GeospatialProcessingError("No features were found.")

    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise GeospatialProcessingError(
                "Each item must be a valid GeoJSON Feature."
            )

        properties = feature.get("properties")
        if properties is not None and not isinstance(properties, dict):
            raise GeospatialProcessingError(
                "Feature properties must be a JSON object or null."
            )

    return features


def _safe_zip_member_path(root: Path, member_name: str) -> Path:
    """Resolve a ZIP member path and ensure it stays inside the extraction root."""
    posix = PurePosixPath(member_name)
    windows = PureWindowsPath(member_name)

    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or ".." in posix.parts
        or ".." in windows.parts
    ):
        raise GeospatialProcessingError("ZIP contains an unsafe file path.")

    root_resolved = root.resolve()
    target = (root_resolved / Path(*posix.parts)).resolve()

    if target != root_resolved and root_resolved not in target.parents:
        raise GeospatialProcessingError("ZIP contains an unsafe file path.")

    return target


def _read_upload(filename: str, content: bytes):
    suffix = Path(filename).suffix.lower()

    if suffix not in {".geojson", ".json", ".zip"}:
        raise GeospatialProcessingError(
            "Supported files are .geojson, .json, and .zip.",
            415,
            "UNSUPPORTED_FILE_TYPE",
        )

    if len(content) > settings.max_upload_size_bytes:
        raise GeospatialProcessingError(
            "Upload exceeds the configured size limit.",
            413,
            "UPLOAD_TOO_LARGE",
        )

    if suffix in {".geojson", ".json"}:
        try:
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GeospatialProcessingError("File does not contain valid JSON.")

        features = _validate_geojson(data)

        # RFC 7946 GeoJSON uses WGS84 longitude/latitude coordinates.
        # Respect an explicit legacy GeoJSON CRS declaration when supplied.
        source_crs = "EPSG:4326"
        crs_info = data.get("crs")

        if isinstance(crs_info, dict):
            properties = crs_info.get("properties") or {}
            if isinstance(properties, dict) and properties.get("name"):
                source_crs = properties["name"]

        result = []
        for feature in features:
            geometry = feature.get("geometry")
            properties = feature.get("properties") or {}

            if geometry is not None and not isinstance(geometry, dict):
                raise GeospatialProcessingError(
                    "Feature geometry must be an object or null."
                )

            result.append((geometry, properties))

        return result, source_crs

    # Read Shapefile ZIP contents inside a temporary directory.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        archive_path = root / "upload.zip"
        archive_path.write_bytes(content)

        try:
            with zipfile.ZipFile(archive_path) as archive:
                members = archive.infolist()

                if len(members) > settings.max_archive_members:
                    raise GeospatialProcessingError(
                        "ZIP contains too many entries."
                    )

                total_size = sum(member.file_size for member in members)
                if total_size > settings.max_archive_uncompressed_bytes:
                    raise GeospatialProcessingError(
                        "ZIP uncompressed size exceeds the configured limit.",
                        413,
                        "ARCHIVE_TOO_LARGE",
                    )

                # Validate every member before extracting any member.
                validated_paths = []
                shp_files = []

                for member in members:
                    target = _safe_zip_member_path(root, member.filename)
                    validated_paths.append((member, target))

                    if not member.is_dir() and member.filename.lower().endswith(".shp"):
                        shp_files.append((member, target))

                if len(shp_files) != 1:
                    raise GeospatialProcessingError(
                        "ZIP must contain exactly one Shapefile (.shp)."
                    )

                # Extract only validated files, without archive.extractall().
                for member, target in validated_paths:
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, target.open("wb") as destination:
                        destination.write(source.read())

                shp_path = shp_files[0][1]
                frame = gpd.read_file(shp_path)

                if frame.empty:
                    raise GeospatialProcessingError(
                        "No features were found in the Shapefile."
                    )

                if frame.crs is None:
                    raise GeospatialProcessingError(
                        "Shapefile has no CRS; measurement cannot be reliable."
                    )

                features = []
                for _, row in frame.iterrows():
                    geometry = row.geometry
                    properties = row.drop(labels="geometry").to_dict()
                    features.append(
                        (
                            geometry.__geo_interface__ if geometry is not None else None,
                            properties,
                        )
                    )

                return features, frame.crs.to_string()

        except zipfile.BadZipFile:
            raise GeospatialProcessingError("Invalid ZIP archive.")
        except GeospatialProcessingError:
            raise
        except Exception as exc:
            raise GeospatialProcessingError(
                f"Could not read Shapefile: {str(exc)[:200]}"
            )


def measure_file(filename: str, content: bytes) -> MeasurementResponse:
    features, source_crs = _read_upload(filename, content)

    try:
        crs = CRS.from_user_input(source_crs)
        geod = crs.get_geod()
        to_wgs84 = Transformer.from_crs(
            crs, CRS.from_epsg(4326), always_xy=True
        ).transform
    except Exception:
        raise GeospatialProcessingError(
            "The source coordinate reference system is invalid."
        )

    results = []
    geometry_type_counts = {}
    total_area = 0.0
    total_length = 0.0
    has_area = False
    has_length = False
    all_bounds = []

    for index, (geometry_data, properties) in enumerate(features):
        if not geometry_data:
            raise GeospatialProcessingError(
                f"Feature {index} has no geometry."
            )

        try:
            geometry = shape(geometry_data)

            if geometry.is_empty or not geometry.is_valid:
                raise GeospatialProcessingError(
                    f"Feature {index} has an empty or invalid geometry."
                )

            geometry_type = geometry.geom_type
            geometry_type_counts[geometry_type] = (
                geometry_type_counts.get(geometry_type, 0) + 1
            )

            # Convert source coordinates to WGS84 before geodesic measurements.
            wgs_geometry = (
                transform(to_wgs84, geometry)
                if crs != CRS.from_epsg(4326)
                else geometry
            )

            area = None
            length = None

            if geometry_type in {"Polygon", "MultiPolygon"}:
                area, _ = geod.geometry_area_perimeter(wgs_geometry)
                area = abs(float(area))
                length = float(geod.geometry_length(wgs_geometry))

                total_area += area
                total_length += length
                has_area = True
                has_length = True

            elif geometry_type in {
                "LineString",
                "MultiLineString",
                "LinearRing",
            }:
                length = float(geod.geometry_length(wgs_geometry))
                total_length += length
                has_length = True

            bounds = list(geometry.bounds)
            if len(bounds) != 4:
                raise GeospatialProcessingError(
                    f"Feature {index} has invalid bounds."
                )
            all_bounds.append(bounds)

            safe_properties = {}
            for key, value in (properties or {}).items():
                if hasattr(value, "item"):
                    value = value.item()

                if value is None or isinstance(value, (str, int, float, bool)):
                    safe_properties[str(key)] = value
                else:
                    safe_properties[str(key)] = str(value)

            results.append(
                FeatureMeasurement(
                    feature_index=index,
                    geometry_type=geometry_type,
                    area_m2=round(area, 3) if area is not None else None,
                    length_m=round(length, 3) if length is not None else None,
                    properties=safe_properties,
                )
            )

        except GeospatialProcessingError:
            raise
        except Exception as exc:
            raise GeospatialProcessingError(
                f"Could not measure feature {index}: {str(exc)[:160]}"
            )

    if not all_bounds:
        raise GeospatialProcessingError("No measurable geometries were found.")

    bounds = [
        min(bound[0] for bound in all_bounds),
        min(bound[1] for bound in all_bounds),
        max(bound[2] for bound in all_bounds),
        max(bound[3] for bound in all_bounds),
    ]

    return MeasurementResponse(
        filename=Path(filename).name,
        source_crs=crs.to_string(),
        measurement_method="Ellipsoidal geodesic measurements (metres)",
        feature_count=len(results),
        geometry_type_counts=geometry_type_counts,
        total_area_m2=round(total_area, 3) if has_area else None,
        total_length_m=round(total_length, 3) if has_length else None,
        bounds=[round(float(value), 8) for value in bounds],
        features=results,
    )
