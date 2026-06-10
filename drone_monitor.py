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
st.title("🗺️ 航线规划 (3D地图 + 障碍物自动识别模拟)")

# ==================== 坐标转换 ====================
try:
    from utils import gcj02_to_wgs84
    def to_wgs84(lat, lng, input_type):
        if input_type == "GCJ-02":
            try:
                wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                return wgs_lat, wgs_lng
            except:
                return lat, lng
        else:
            return lat, lng
except ImportError:
    def to_wgs84(lat, lng, input_type):
        return lat, lng

# ==================== 工具函数：将圆圈转换为多边形 ====================
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

# ==================== 初始化会话状态 + 自动读取本地文件 ====================
CONFIG_PATH = "obstacle_config.json"
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            load_cfg = json.load(f)
            load_obstacles = load_cfg.get("obstacles", [])
            load_save_time = load_cfg.get("save_time")
    except Exception as e:
        load_obstacles = []
        load_save_time = None
else:
    load_obstacles = []
    load_save_time = None

if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "WGS-84"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2322, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2343, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50
if 'polygon_obstacles' not in st.session_state:
    st.session_state.polygon_obstacles = load_obstacles
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = load_save_time

# ==================== 布局 ====================
left_col, right_col = st.columns([3.5, 1.2])

# ==================== 左侧：地图 ====================
with left_col:
    latA_w, lngA_w = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
    latB_w, lngB_w = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

    center_lat = (latA_w + latB_w) / 2
    center_lng = (lngA_w + lngB_w) / 2
    if not (-90 <= center_lat <= 90) or not (-180 <= center_lng <= 180):
        center_lat, center_lng = 32.233, 118.749

    if st.session_state.coord_type == "GCJ-02":
        m = folium.Map(location=[center_lat, center_lng], zoom_start=16, control_scale=True,
                       tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                       attr="Tiles © Esri")
    else:
        m = folium.Map(location=[center_lat, center_lng], zoom_start=16, control_scale=True,
                       tiles='http://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
                       attr='高德地图')

    # 起点、终点标记
    folium.Marker([latA_w, lngA_w], popup=f"起点 A<br>{latA_w:.6f}, {lngA_w:.6f}",
                  icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)
    folium.Marker([latB_w, lngB_w], popup=f"终点 B<br>{latB_w:.6f}, {lngB_w:.6f}",
                  icon=folium.Icon(color="red", icon="stop", prefix="fa")).add_to(m)

    # 航线
    folium.PolyLine([(latA_w, lngA_w), (latB_w, lngB_w)],
                    color="blue", weight=5, opacity=0.8, dash_array="5, 10").add_to(m)

    # 渲染已保存障碍物
    for obs in st.session_state.polygon_obstacles:
        coords = obs["coordinates"]
        poly_coords = [[c[1], c[0]] for c in coords]
        height = obs.get("height", 40)
        folium.Polygon(
            locations=poly_coords,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.2,
            weight=3,
            popup=f"名称: {obs.get('name', '障碍物')}<br>高度: {height}m"
        ).add_to(m)
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        folium.Marker([cy, cx], icon=folium.DivIcon(
            html=f'<div style="background:rgba(0,0,0,0.7); color:white; padding:2px 6px; border-radius:12px;">{height}m</div>')).add_to(m)

    # 飞行高度标注
    mid_lat = (latA_w + latB_w) / 2
    mid_lng = (lngA_w + lngB_w) / 2
    folium.Marker([mid_lat, mid_lng], icon=folium.DivIcon(
        html=f'<div style="background:rgba(0,0,0,0.6); color:white; padding:4px 12px; border-radius:20px; border:1px solid #3498db;">✈️ 飞行高度: {st.session_state.flight_height} m</div>')).add_to(m)

    # 绘图工具
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

    # 自动适配视野
    all_points = []
    if (-90 <= latA_w <= 90) and (-180 <= lngA_w <= 180):
        all_points.append([latA_w, lngA_w])
    if (-90 <= latB_w <= 90) and (-180 <= lngB_w <= 180):
        all_points.append([latB_w, lngB_w])
    for obs in st.session_state.polygon_obstacles:
        for coord in obs["coordinates"]:
            if isinstance(coord, (list, tuple)) and len(coord) == 2:
                lat, lng = coord[1], coord[0]
                if (-90 <= lat <= 90) and (-180 <= lng <= 180):
                    all_points.append([lat, lng])
    if len(all_points) > 1:
        try:
            m.fit_bounds([
                [min(p[0] for p in all_points), min(p[1] for p in all_points)],
                [max(p[0] for p in all_points), max(p[1] for p in all_points)]
            ])
        except:
            pass

    output = st_folium(m, height=800, use_container_width=True, key="map_key", returned_objects=["last_draw"])

    # 已注释：手绘自动捕获（存在插件兼容BUG）
    # if output and output.get("last_draw") and output["last_draw"].get("geometry"):
    #     geom = output["last_draw"]["geometry"]
    #     coords = []
    #     if geom["type"] == "Polygon":
    #         coords = geom["coordinates"][0]
    #     elif geom["type"] == "Circle":
    #         center = geom["coordinates"][0]
    #         radius = geom["coordinates"][1]
    #         coords = circle_to_polygon(center[0], center[1], radius)
    #     if coords:
    #         new_obs = {
    #             "name": f"自动识别障碍物 {len(st.session_state.polygon_obstacles) + 1}",
    #             "coordinates": coords,
    #             "height": 40
    #         }
    #         st.session_state.polygon_obstacles.append(new_obs)
    #         st.rerun()

# ==================== 右侧控制面板 ====================
with right_col:
    st.subheader("🎮 控制面板")
    
    coord_type_option = st.radio("输入坐标系", ["WGS-84", "GCJ-02 (高德/百度)"],
                                 index=0 if st.session_state.coord_type == "WGS-84" else 1)
    st.session_state.coord_type = coord_type_option.split()[0]
    
    st.subheader("起点 A")
    col1, col2 = st.columns(2)
    latA_input = col1.number_input("纬度", value=st.session_state.pointA["lat"], format="%.6f", key="latA")
    lngA_input = col2.number_input("经度", value=st.session_state.pointA["lng"], format="%.6f", key="lngA")
    if st.button("📍 设置A点", use_container_width=True):
        st.session_state.pointA = {"lat": latA_input, "lng": lngA_input}
        st.rerun()
    
    st.subheader("终点 B")
    col3, col4 = st.columns(2)
    latB_input = col3.number_input("纬度", value=st.session_state.pointB["lat"], format="%.6f", key="latB")
    lngB_input = col4.number_input("经度", value=st.session_state.pointB["lng"], format="%.6f", key="lngB")
    if st.button("📍 设置B点", use_container_width=True):
        st.session_state.pointB = {"lat": latB_input, "lng": lngB_input}
        st.rerun()
    
    st.subheader("✈️ 飞行参数")
    height_input = st.number_input("设定飞行高度 (m)", min_value=10, max_value=500,
                                   value=st.session_state.flight_height, step=5)
    st.session_state.flight_height = height_input

    # 手动添加障碍物按钮
    st.divider()
    if st.button("➕ 手动添加测试障碍物", use_container_width=True):
        lat_c = (st.session_state.pointA["lat"] + st.session_state.pointB["lat"]) / 2
        lng_c = (st.session_state.pointA["lng"] + st.session_state.pointB["lng"]) / 2
        test_obs = {
            "name": "测试障碍物",
            "coordinates": [
                [lng_c-0.001, lat_c-0.001],
                [lng_c+0.001, lat_c-0.001],
                [lng_c+0.001, lat_c+0.001],
                [lng_c-0.001, lat_c+0.001]
            ],
            "height": 40
        }
        st.session_state.polygon_obstacles.append(test_obs)
        st.rerun()

    st.divider()
    
    st.markdown("### 🚧 障碍物配置持久化")
    st.caption(f"配置文件：{CONFIG_PATH} | 版本：v12.2")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        # 一键部署：修复版，写入本地文件并强制刷新状态
        if st.button("💾 一键部署", type="primary", use_container_width=True):
            config = {
                "version": "v12.2",
                "save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "obstacles": st.session_state.polygon_obstacles
            }
            # 真正写入本地文件
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            st.session_state.last_save_time = config["save_time"]
            st.success("✅ 一键部署完成！障碍物已永久保存")
            # 强制刷新页面，让状态数字更新
            st.rerun()
    with col_btn2:
        uploaded_file = st.file_uploader("📂 从文件加载", type=["json"], label_visibility="collapsed")
        if uploaded_file is not None:
            try:
                config = json.load(uploaded_file)
                st.session_state.polygon_obstacles = config.get("obstacles", [])
                st.session_state.last_save_time = config.get("save_time", None)
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                st.rerun()
            except Exception as e:
                st.error(f"加载失败: {e}")
    
    col_btn3, col_btn4 = st.columns(2)
    with col_btn3:
        if st.button("🗑️ 清理所有框", use_container_width=True):
            st.session_state.polygon_obstacles = []
            st.session_state.last_save_time = None
            empty_config = {"version": "v12.2", "save_time": None, "obstacles": []}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(empty_config, f, indent=2, ensure_ascii=False)
            st.success("已清理所有障碍物")
            st.rerun()
    with col_btn4:
        if st.button("🧹 一键清理存储", type="primary", use_container_width=True):
            st.session_state.polygon_obstacles = []
            st.session_state.last_save_time = None
            empty_config = {"version": "v12.2", "save_time": None, "obstacles": []}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(empty_config, f, indent=2, ensure_ascii=False)
            st.success("已清除所有存储数据")
            st.rerun()
    
    st.divider()
    
    st.markdown("#### 📥 下载配置文件备份")
    if st.session_state.polygon_obstacles:
        config_download = {
            "version": "v12.2",
            "save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "obstacles": st.session_state.polygon_obstacles
        }
        st.download_button(
            label="⬇️ 下载 obstacle_config.json",
            data=json.dumps(config_download, indent=2, ensure_ascii=False),
            file_name="obstacle_config.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.button("⬇️ 下载 (暂无数据)", disabled=True, use_container_width=True)
    
    # 文件状态展示（修复版，会实时显示真实数量）
    status_text = f"📂 文件状态：共 {len(st.session_state.polygon_obstacles)} 个障碍物"
    if st.session_state.last_save_time:
        status_text += f" | 保存时间：{st.session_state.last_save_time}"
    st.info(status_text)

    with st.expander("📋 障碍物列表"):
        if st.session_state.polygon_obstacles:
            for i, obs in enumerate(st.session_state.polygon_obstacles):
                pts = len(obs["coordinates"])
                st.write(f"{i+1}. **{obs.get('name', f'障碍物{i+1}')}** (点数: {pts}, 高度: {obs.get('height', 40)}m)")
        else:
            st.write("暂无障碍物")

# 底部数据展示
st.divider()
st.subheader("当前规划数据")
c1, c2, c3 = st.columns(3)
c1.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
c2.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
c3.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}")
st.info("使用【手动添加测试障碍物】生成障碍物，点击一键部署保存，重启页面自动加载。")
