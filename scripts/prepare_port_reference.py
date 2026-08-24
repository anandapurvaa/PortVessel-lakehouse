from pathlib import Path
import geopandas as gpd

INPUT = Path("data/reference/raw/california_ports_ospr.geojson")
OUTPUT = Path("data/reference/ports/california_ports_ospr.parquet")

if not INPUT.exists():
    raise FileNotFoundError(
        f"Missing {INPUT}. Download the GeoJSON resource from the California Open Data page first."
    )

gdf = gpd.read_file(INPUT)
print("Original CRS:", gdf.crs)
print("Rows:", len(gdf))
print("Columns:", list(gdf.columns))
print(gdf.head())

if gdf.crs is None:
    raise ValueError("The reference layer has no CRS metadata")

gdf = gdf.to_crs("EPSG:4326")
gdf["geometry_valid_before"] = gdf.geometry.is_valid
gdf["geometry"] = gdf.geometry.make_valid()
gdf["geometry_valid_after"] = gdf.geometry.is_valid
gdf["geometry_wkt"] = gdf.geometry.to_wkt()

gdf.drop(columns="geometry").to_parquet(OUTPUT, index=False)
print(f"Wrote {OUTPUT}")
