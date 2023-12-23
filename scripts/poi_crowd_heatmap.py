import pandas as pd
import geopandas as gpd
import pydeck as pdk
import numpy as np
from sklearn.neighbors import BallTree
from joblib import Parallel, delayed

def count_neighbors(tree, point, radius):
    """ 计算一个点在给定半径内的邻居数量 """
    count = tree.query_radius([point], r=radius, count_only=True)
    return count[0]

# POI GeoJSON文件的路径
POI_DATA = r"C:\Users\Acer\Downloads\poi_points\poi_points.geojson"

# 读取POI数据
poi_gdf = gpd.read_file(POI_DATA)
poi_df = pd.DataFrame(poi_gdf.drop(columns='geometry'))
poi_df['lng'] = poi_gdf.geometry.x
poi_df['lat'] = poi_gdf.geometry.y

# 计算空间群聚程度
SEARCH_RADIUS = 500  # 假设搜索半径为500米
SEARCH_RADIUS_DEGREE = SEARCH_RADIUS / 111320  # 转换为球面距离

# 建立球面树
poi_coords = np.deg2rad(poi_df[['lat', 'lng']].values)
tree = BallTree(poi_coords, metric='haversine')

# 使用joblib并行处理
n_jobs = -1  # 使用所有CPU核心
counts = Parallel(n_jobs=n_jobs)(delayed(count_neighbors)(tree, point, SEARCH_RADIUS_DEGREE) for point in poi_coords)
poi_df['weight'] = counts

# 為POI數據設置列名
poi_df = poi_df[['lng', 'lat', 'weight']]

# 設置顏色範圍
COLOR_BREWER_BLUE_SCALE = [
    [247, 252, 240],
    [242, 250, 229],
    [237, 248, 217],
    [232, 246, 206],
    [227, 244, 195],
    [222, 243, 184],
    [217, 241, 173],
    [204, 235, 197],
    [191, 229, 220],
    [179, 223, 204],
    [166, 217, 188],
    [153, 211, 172],
    [140, 205, 156],
    [123, 204, 196],
    [106, 203, 196],
    [89, 202, 196],
    [72, 201, 196],
    [55, 200, 196],
    [38, 199, 196],
    [21, 198, 196],
    [67, 162, 202],
    [57, 152, 192],
    [47, 142, 182],
    [37, 132, 172],
    [27, 122, 162],
    [17, 112, 152],
    [8, 104, 172],
    [7, 93, 162],
    [6, 82, 152],
    [5, 71, 142],
    [4, 60, 132],
    [3, 49, 122],
]

# calculate the max density and min density
max_density = poi_df['weight'].max()
min_density = poi_df['weight'].min()

# 創建POI熱點圖層
poi_layer = pdk.Layer(
    "HeatmapLayer",
    data=poi_df,
    opacity=0.9,
    get_position=["lng", "lat"],
    aggregation=pdk.types.String("MEAN"), 
    color_range=COLOR_BREWER_BLUE_SCALE,
    threshold=0.75,
    get_weight="weight",
    pickable=True,
)

# Set the viewport location
view_state = pdk.ViewState(
    latitude=22.9,    # 經度
    longitude=120.1,  # 緯度
    zoom=11,          # 放大級別
    pitch=85,         # 傾斜角度，接近垂直向下
    bearing=45        # 朝向角度，從西南方向往東北方向
)

# 创建Deck
r = pdk.Deck(
    layers=[poi_layer],
    initial_view_state=view_state,
    tooltip={"text": "Concentration of POI"}
)

# 生成地图的HTML
map_html = r.to_html(as_string=True)

# 创建包含色条图例的完整HTML
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Crowd Heatmap</title>
    <style>
        .colorbar {{
            width: 20px;
            height: 200px;
            background: linear-gradient(to top, 
                #031D7A 0%, 
                #67A2D2 50%, 
                #F7FCF0 100%);
            position: absolute;
            bottom: 20px;
            left: 20px;
            border: 1px solid black;
        }}
        .colorbar-label {{
            position: absolute;
            left: 50px;
            font-family: Arial, sans-serif;
            font-size: 12px;
        }}
        .title {{
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            font-family: Arial, sans-serif;
            font-size: 24px;
        }}
    </style>
</head>
<body>
    <div id="container" style="width:100%;height:100%;">{map_html}</div>
    <div class="title">Crowd Heatmap based on Commercial POI in Tainan</div>
    <div class="colorbar"></div>
    <div class="colorbar-label" style="bottom: 20px;">Low Density:{min_density} people/area </div>
    <div class="colorbar-label" style="bottom: 220px;">High Density:{max_density} people/area </div>
</body>
</html>
"""

# 保存HTML文件
with open('poi_heatmap_with_legend.html', 'w') as file:
    file.write(full_html)