import geopandas as gpd

path = "data/reference/raw/la_lb_anchorage_areas.geojson"

gdf = gpd.read_file(path)

print("Rows:", len(gdf))
print("CRS:", gdf.crs)
print("Geometry types:")
print(gdf.geometry.geom_type.value_counts())

print("\nColumns:")
print(list(gdf.columns))

print("\nBounds:")
print(gdf.total_bounds)

print("\nValidity:")
print(gdf.geometry.is_valid.value_counts())

for column in gdf.columns:
    if column != "geometry":
        print(f"\n{column}")
        print(gdf[column].dropna().astype(str).head(20).to_list())