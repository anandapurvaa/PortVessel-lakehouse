import geopandas as gpd

gdf = gpd.read_file(
    "data/reference/raw/california_ports_ospr.geojson"
)

print("Rows:", len(gdf))
print("CRS:", gdf.crs)
print("Columns:", list(gdf.columns))

for column in gdf.columns:
    if column != "geometry":
        print(f"\n{column}")
        print(gdf[column].dropna().astype(str).head(20).to_list())