```python
# pages/1_航线规划.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import json
import datetime
import math
import os

# ==================== 页面配置 ====================
st.set_page_config(page_title="航线规划 - 3D地图", layout="wide")
st.title("🗺️ 航线规划 (卫星地图 + 障碍物圈选记忆)")

# ==================== 坐标转换 GCJ-02 <-> WGS84 ====================
def gcj02_to_wgs84(lng, lat):
    a = 6378245.0
    ee = 0.00669342162296594323
    if out_of_china(lng, lat):
        return lng, lat
    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng - dlng, lat - dlat

def wgs84_to_gcj02(lng, lat):
    a = 6378245.0
    ee = 0.00669342162296594323
    if out_of_china(lng, lat):
        return lng, lat
    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat

def transform_lng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def transform_lat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def out_of_china(lng, lat):
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)

def to_wgs84_display(lat, lng, input_type):
    if input_type == "GCJ-02":
        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
        return wgs_lat, wgs_lng
    else:
        return lat, lng

# ==================== 圆转多边形 ====================
def circle_to_polygon(center_lng, center_lat, radius_meters, num_points=24):
    points = []
    lat_rad = math.radians(center_lat)
    dlat = radius_meters / 110540
    dlng = radius_meters / (111320 * math.cos(lat_rad))
    for i in range(num_points):
        angle = math.radians(360 * i / num_points)
        offset_lng = dlng * math.cos(angle)
        offset_lat = dlat * math.sin(angle)
        points.append([center_lng + offset_lng, center_lat + offset_lat])
    return points

# ==================== 初始化会话状态 ====================
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2323, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2344, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 10
if 'polygon_obstacles' not in st.session_state:
    try:
        with open("obstacle_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            st.session_state.polygon_obstacles = config.get("obstacles", [])
    except:
        st.session_state.polygon_obstacles = []
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = None

# ==================== 保存障碍物到文件 ====================
def save_obstacles():
    config = {
        "version": "v1.0",
        "save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "obstacles": st.session_state.polygon_obstacles
    }
    with open("obstacle_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    st.session_state.last_save_time = config["save_time"]

# ==================== 布局 ====================
left_col, right_col = st.columns([3.5, 1.2])

# ==================== 左侧地图 ====================
with left_col:
    latA_disp, lngA_disp = to_wgs84_display(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
    latB_disp, lngB_disp = to_wgs84_display(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

    center_lat = (latA_disp + latB_disp) / 2
    center_lng = (lngA_disp + lngB_disp) / 2
    if not (-90 <= center_lat <= 90):
        center_lat, center_lng = 32.233, 118.749

    m = folium.Map(
        location=[center_lat, center_lng], 
        zoom_start=16, 
        control_scale=True,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri | 卫星影像"
    )

    folium.Marker([latA_disp, lngA_disp], popup=f"起点 A<br>{latA_disp:.6f}, {lngA_disp:.6f}",
                  icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)
    folium.Marker([latB_disp, lngB_disp], popup=f"终点 B<br>{latB_disp:.6f}, {lngB_disp:.6f}",
                  icon=folium.Icon(color="red", icon="stop", prefix="fa")).add_to(m)

    folium.PolyLine([(latA_disp, lngA_disp), (latB_disp, lngB_disp)],
                    color="blue", weight=5, opacity=0.8, dash_array="5, 10").add_to(m)

    # 渲染障碍物
    for obs in st.session_state.polygon_obstacles:
        coords = obs["coordinates"]
        display_coords = []
        for lng, lat in coords:
            if st.session_state.coord_type == "GCJ-02":
                wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
            else:
                wgs_lng, wgs_lat = lng, lat
            display_coords.append([wgs_lat, wgs_lng])
        height = obs.get("height", 40)
        folium.Polygon(
            locations=display_coords,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.25,
            weight=3,
            popup=f"障碍物<br>高度: {height}m"
        ).add_to(m)
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        if st.session_state.coord_type == "GCJ-02":
            cx_disp, cy_disp = gcj02_to_wgs84(cx, cy)
        else:
            cx_disp, cy_disp = cx, cy
        folium.Marker([cy_disp, cx_disp], icon=folium.DivIcon(
            html=f'<div style="background:rgba(0,0,0,0.7); color:white; padding:2px 6px; border-radius:12px;">{height}m</div>')).add_to(m)

    mid_lat = (latA_disp + latB_disp) / 2
    mid_lng = (lngA_disp + lngB_disp) / 2
    folium.Marker([mid_lat, mid_lng], icon=folium.DivIcon(
        html=f'<div style="background:rgba(0,0,0,0.6); color:white; padding:4px 12px; border-radius:20px;">✈️ 高度: {st.session_state.flight_height}m</div>')).add_to(m)

    Draw(
        draw_options={
            "polygon": {"shapeOptions": {"color": "#ffdd00"}, "allowIntersection": False},
            "polyline": False,
            "rectangle": {"shapeOptions": {"color": "#ffdd00"}},
            "circle": {"shapeOptions": {"color": "#ffdd00"}},
            "circlemarker": False,
            "marker": False
        },
        edit_options={"edit": True, "remove": True}
    ).add_to(m)
    MousePosition().add_to(m)

    all_points = [[latA_disp, lngA_disp], [latB_disp, lngB_disp]]
    for obs in st.session_state.polygon_obstacles:
        for lng, lat in obs["coordinates"]:
            if st.session_state.coord_type == "GCJ-02":
                wlat, wlng = gcj02_to_wgs84(lng, lat)
            else:
                wlat, wlng = lat, lng
            all_points.append([wlat, wlng])
    if len(all_points) > 1:
        try:
            m.fit_bounds([[min(p[0] for p in all_points), min(p[1] for p in all_points)],
                          [max(p[0] for p in all_points), max(p[1] for p in all_points)]])
        except:
            pass

    output = st_folium(m, height=800, use_container_width=True, key="map_key", returned_objects=["last_draw"])

    # 自动识别并保存障碍物
    if output and output.get("last_draw") and output["last_draw"].get("geometry"):
        geom = output["last_draw"]["geometry"]
        coords = []
        
        if geom["type"] == "Polygon":
            raw_coords = geom["coordinates"][0]
            for lng, lat in raw_coords:
                if st.session_state.coord_type == "GCJ-02":
                    gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
                    coords.append([gcj_lng, gcj_lat])
                else:
                    coords.append([lng, lat])
        elif geom["type"] == "Circle":
            center = geom["coordinates"][0]
            radius = geom["coordinates"][1]
            if st.session_state.coord_type == "GCJ-02":
                center_gcj_lng, center_gcj_lat = wgs84_to_gcj02(center[0], center[1])
            else:
                center_gcj_lng, center_gcj_lat = center[0], center[1]
            coords = circle_to_polygon(center_gcj_lng, center_gcj_lat, radius)
        
        if coords:
            new_obs = {
                "name": f"障碍物{len(st.session_state.polygon_obstacles) + 1}",
                "coordinates": coords,
                "height": 40
            }
            st.session_state.polygon_obstacles.append(new_obs)
            save_obstacles()
            st.rerun()

# ==================== 右侧控制面板 ====================
with right_col:
    st.subheader("🎮 控制面板")
    
    coord_type_option = st.radio("输入坐标系", ["WGS-84", "GCJ-02"], index=1 if st.session_state.coord_type == "GCJ-02" else 0)
    if coord_type_option != st.session_state.coord_type:
        st.session_state.coord_type = coord_type_option
        st.rerun()
    
    st.subheader("起点 A")
    col1, col2 = st.columns(2)
    latA_input = col1.number_input("纬度", value=st.session_state.pointA["lat"], format="%.6f")
    lngA_input = col2.number_input("经度", value=st.session_state.pointA["lng"], format="%.6f")
    if st.button("📍 设置A点", use_container_width=True):
        st.session_state.pointA = {"lat": latA_input, "lng": lngA_input}
        st.rerun()
    
    st.subheader("终点 B")
    col3, col4 = st.columns(2)
    latB_input = col3.number_input("纬度", value=st.session_state.pointB["lat"], format="%.6f")
    lngB_input = col4.number_input("经度", value=st.session_state.pointB["lng"], format="%.6f")
    if st.button("📍 设置B点", use_container_width=True):
        st.session_state.pointB = {"lat": latB_input, "lng": lngB_input}
        st.rerun()
    
    st.subheader("✈️ 飞行参数")
    height_input = st.number_input("设定飞行高度 (m)", min_value=10, max_value=500,
                                   value=st.session_state.flight_height, step=5)
    st.session_state.flight_height = height_input
    st.metric("当前飞行高度", f"{st.session_state.flight_height} 米")

    st.divider()
    st.markdown("### 🚧 障碍物管理")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 保存配置", use_container_width=True):
            save_obstacles()
            st.success(f"已保存 {len(st.session_state.polygon_obstacles)} 个障碍物")
    with col_btn2:
        if st.button("📂 加载记忆", use_container_width=True):
            try:
                with open("obstacle_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    st.session_state.polygon_obstacles = config.get("obstacles", [])
                    st.session_state.last_save_time = config.get("save_time", None)
                st.success("已加载障碍物")
                st.rerun()
            except:
                st.warning("未找到记忆文件")
    
    if st.button("🗑️ 清理所有障碍物", use_container_width=True):
        st.session_state.polygon_obstacles = []
        st.session_state.last_save_time = None
        try:
            os.remove("obstacle_config.json")
        except:
            pass
        st.success("已清理")
        st.rerun()
    
    if st.session_state.polygon_obstacles:
        st.download_button(
            label="📥 导出JSON",
            data=json.dumps({"obstacles": st.session_state.polygon_obstacles}, indent=2, ensure_ascii=False),
            file_name="obstacle_config.json",
            mime="application/json",
            use_container_width=True
        )
    
    st.info(f"📂 障碍物数量: {len(st.session_state.polygon_obstacles)}")

# ==================== 底部数据 ====================
st.divider()
st.subheader("📊 当前规划数据")
c1, c2, c3 = st.columns(3)
c1.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
c2.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
c3.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"📍 坐标系: {st.session_state.coord_type} | 底图: 卫星影像 | 多边形/圆形自动转为障碍物并记忆")
```
