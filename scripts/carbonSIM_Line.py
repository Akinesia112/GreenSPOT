import geopandas as gpd
import json
import pydeck as pdk
import datetime
import jinja2

# Load your GeoJSON file
file_path = r'C:\Users\Acer\Downloads\type_route_public_transport_line_Tainan\type_route_public_transport_line_Tainan.geojson'
with open(file_path, 'r', encoding='utf-8') as file:
    geojson_data = json.load(file)

# Convert GeoJSON data to a GeoDataFrame
gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
gdf = gdf.set_crs(epsg=4326)

# Temporarily converting to a projected CRS for length calculation
gdf_projected = gdf.to_crs(epsg=3857)
gdf['length_km'] = gdf_projected.geometry.length / 1000  # Calculate route length in km
gdf['carbon_emissions_kg'] = gdf['length_km'] * 0.3 * 2.68  # Carbon emissions calculation

# Define a color scale for carbon emissions
def color_scale(val):
    if val < 10:
        # Dark green for low emissions
        return [0, 128, 0]
    elif val < 30:
        return [255, 165, 0]  # Bright orange for moderate emissions
    else:
        return [255, 0, 0]    # Bright red for high emissions

gdf['color'] = gdf['carbon_emissions_kg'].apply(color_scale)

# Create a list of coordinates for each route, handling MultiLineStrings
def extract_coordinates(geom):
    if geom.geom_type == 'LineString':
        return list(geom.coords)
    elif geom.geom_type == 'MultiLineString':
        coords = []
        for part in geom.geoms:  # Iterate through each LineString within the MultiLineString
            coords.extend(list(part.coords))
        return coords
    else:
        return []

gdf['coordinates'] = gdf['geometry'].apply(extract_coordinates)

# Pydeck layer for bus routes
layer = pdk.Layer(
    "PathLayer",
    gdf,
    get_path="coordinates",
    get_width=5,
    get_color="color",
    pickable=True
)

# Set the viewport location
view_state = pdk.ViewState(latitude=23.0, longitude=120.2, zoom=10)

# Define labels for the legend
# Calculate carbon emission ranges for the legend
min_emission = gdf['carbon_emissions_kg'].min()
max_emission = gdf['carbon_emissions_kg'].max()
mid_emission = (min_emission + max_emission) / 2

# Update labels with emission ranges
labels = [
    {"text": f"High Emissions (> {mid_emission:.2f} kg CO2)", "color": [255, 0, 0]},
    {"text": f"Medium Emissions ({min_emission:.2f} - {mid_emission:.2f} kg CO2)", "color": [255, 165, 0]},
    {"text": f"Low Emissions (< {min_emission:.2f} kg CO2)", "color": [0, 128, 0]}
]

# Create the legend
def create_legend(labels):
    for label in labels:
        assert label['color'] and label['text']
        assert len(label['color']) in (3, 4)
        label['color'] = ', '.join([str(c) for c in label['color']])
    
    legend_template = jinja2.Template('''
    <style>
      .legend {
        width: 300px;
      }
      .square {
        height: 15px;
        width: 15px;
        border: 1px solid grey;
        display: inline-block;
        margin-right: 5px;
      }
    </style>
    <h2>Bus Carbon Emissions in Tainan</h2>
    {% for label in labels %}
    <div class='legend'>
      <div class="square" style="background:rgba({{ label['color'] }})"></div>
      <span>{{label['text']}}</span>
    </div>
    {% endfor %}
    ''')
    html_str = legend_template.render(labels=labels)
    return html_str

legend = create_legend(labels)

# Render the deck.gl map with the legend as description
r = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={"text": "{length_km} km, {carbon_emissions_kg} kg CO2"},
    description=legend  # 將圖例 HTML 字符串作為描述添加
)

# Save the map as an HTML file with the current timestamp
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
r.to_html(f'bus_routes_carbon_emission_{timestamp}.html')