"""Get the Staten Island taxi zones and the latitude/longitude of each zone.

The TLC zone lookup gives the zone names and boroughs. The TLC zone shapefile
gives the zone boundaries in NY State Plane coordinates (EPSG:2263, feet). We
take the centroid of each zone polygon and convert it to WGS84 lat/lon, which
is what the Open-Meteo API expects.

Output: data/external/staten_island_zones.csv
"""
import zipfile

import pandas as pd
import shapefile
from pyproj import CRS, Transformer

import config
from utils import download_file, log, setup_logging


def load_zone_lookup():
    path = download_file(config.ZONE_LOOKUP_URL, config.RAW_DIR / "taxi_zone_lookup.csv")
    return pd.read_csv(path)


def borough_zones(lookup, borough=config.BOROUGH):
    zones = lookup[lookup["Borough"] == borough].copy()
    if zones.empty:
        raise ValueError(f"No zones found for borough {borough!r}")
    return zones.sort_values("LocationID").reset_index(drop=True)


def ring_area_and_centroid(points):
    """Signed area and centroid of one polygon ring (shoelace formula)."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    if area == 0:
        return 0.0, 0.0, 0.0
    return area, cx / (6 * area), cy / (6 * area)


def shape_centroid(shape):
    """Area-weighted centroid over all rings of a (multi)polygon.

    Outer rings and holes have opposite winding in a shapefile, so their signed
    areas have opposite signs and holes are subtracted automatically.
    """
    starts = list(shape.parts) + [len(shape.points)]
    total_area = sum_x = sum_y = 0.0
    for start, end in zip(starts, starts[1:]):
        area, cx, cy = ring_area_and_centroid(shape.points[start:end])
        total_area += area
        sum_x += cx * area
        sum_y += cy * area
    return sum_x / total_area, sum_y / total_area


def zone_centroids():
    """Return LocationID, latitude, longitude for every zone in the shapefile."""
    zip_path = download_file(config.ZONE_SHAPES_URL, config.RAW_DIR / "taxi_zones.zip")
    shp_dir = config.RAW_DIR / "taxi_zones"
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(config.RAW_DIR)

    source_crs = CRS.from_wkt((shp_dir / "taxi_zones.prj").read_text())
    to_wgs84 = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)

    rows = []
    with shapefile.Reader(str(shp_dir / "taxi_zones.shp")) as reader:
        for record in reader.iterShapeRecords():
            x, y = shape_centroid(record.shape)
            lon, lat = to_wgs84.transform(x, y)
            rows.append({
                "LocationID": int(record.record["LocationID"]),
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
            })
    return pd.DataFrame(rows)


def main():
    setup_logging()
    zones = borough_zones(load_zone_lookup())

    centroids = zone_centroids()
    zones = zones.merge(centroids, on="LocationID", how="left", validate="one_to_one")
    missing = zones[zones["latitude"].isna()]
    if not missing.empty:
        raise ValueError(f"No shape found for zones: {missing['LocationID'].tolist()}")

    config.EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    zones.to_csv(config.ZONES_FILE, index=False)
    log.info("%d %s zones saved to %s", len(zones), config.BOROUGH, config.ZONES_FILE)


if __name__ == "__main__":
    main()
