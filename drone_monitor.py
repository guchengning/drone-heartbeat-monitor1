import streamlit as st
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import math

# ------------------- WGS84与GCJ02坐标转换函数 -------------------
def wgs84_to_gcj02(lat, lon):
    a = 6378245.0
    ee = 0.00669342162296594323
    dlat = _transformlat(lon - 105.0, lat - 35.0)
    dlon = _transformlon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lat + dlat, lon + dlon

def _transformlat(lon, lat):
    ret = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * math.sqrt(abs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def _transformlon(lon, lat):
    ret = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * math.sqrt(abs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lon * math.pi) + 40.0 * math.sin(lon / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lon / 12.0 * math.pi) + 300.0 * math.sin(lon / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

# 页面基础配置
st.set_page_config(page_title="无人机监控系统", layout="wide")

# 侧边双页面切换
page = st.sidebar.radio("功能页面", ["航线规划", "飞行监控"])

# 会话状态存储A/B点标记开关
if "heartbeat_data" not in st.session_state:
    st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
if "running" not in st.session_state:
    st.session_state["running"] = False
if "mark_A" not in st.session_state:
    st.session_state["mark_A"] = False
if "mark_B" not in st.session_state:
    st.session_state["mark_B"] = False

# ========== 航线规划页面（地图页面） ==========
if page == "航线规划":
    st.header("🗺️ 航线规划")
    # 左右分栏：左地图、右侧控制面板
    map_col, ctrl_col = st.columns([3, 1])

    with ctrl_col:
        st.subheader("坐标系设置")
        coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02(高德/百度)"], index=1)

        # 起点A 输入框（加key解决ID冲突）
        st.subheader("起点A")
        lat_a = st.number_input("纬度", value=32.2322, format="%.4f", key="lat_a_in")
        lon_a = st.number_input("经度", value=118.7490, format="%.4f", key="lon_a_in")
        if st.button("设置A点"):
            st.session_state["mark_A"] = True
            st.success("✅ A点已设置")

        # 终点B 输入框
        st.subheader("终点B")
        lat_b = st.number_input("纬度", value=32.2343, format="%.4f", key="lat_b_in")
        lon_b = st.number_input("经度", value=118.7490, format="%.4f", key="lon_b_in")
        if st.button("设置B点"):
            st.session_state["mark_B"] = True
            st.success("✅ B点已设置")

        # 飞行高度滑块
        st.subheader("飞行参数")
        fly_height = st.slider("设定飞行高度(m)", min_value=0, max_value=200, value=50)

    with map_col:
        # 坐标转换
        if coord_type == "GCJ-02(高德/百度)":
            a_lat_map, a_lon_map = wgs84_to_gcj02(lat_a, lon_a)
            b_lat_map, b_lon_map = wgs84_to_gcj02(lat_b, lon_b)
        else:
            a_lat_map, a_lon_map = lat_a, lon_a
            b_lat_map, b_lon_map = lat_b, lon_b

        # 地图中心点固定为校园两点中间，打开页面直接显示校园
        map_center_lat = (lat_a + lat_b) / 2
        map_center_lon = (lon_a + lon_b) / 2

        # 卫星底图（和作业截图一致）
        m = folium.Map(
            location=[map_center_lat, map_center_lon],
            zoom_start=16,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        )
        # 左侧障碍物绘制工具栏（作业要求）
        Draw(
            draw_options={"polyline":True,"polygon":True,"rectangle":True,"circle":True,"marker":False},
            edit_options={"edit": True}
        ).add_to(m)

        # 绘制A/B标记（点击按钮才显示）
        if st.session_state["mark_A"]:
            folium.Marker([a_lat_map, a_lon_map], popup="起点A", icon=folium.Icon(color="red")).add_to(m)
        if st.session_state["mark_B"]:
            folium.Marker([b_lat_map, b_lon_map], popup="终点B", icon=folium.Icon(color="green")).add_to(m)

        # 渲染地图
        st_folium(m, width=720, height=520)

# ========== 飞行监控页面（心跳包页面） ==========
elif page == "飞行监控":
    st.header("📡 实时心跳包序号与时间变化")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        start_btn = st.button("开始监测")
    with btn_col2:
        stop_btn = st.button("停止监测")

    if start_btn:
        st.session_state["running"] = True
        st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
    if stop_btn:
        st.session_state["running"] = False

    status_box = st.empty()
    chart_box = st.empty()

    if st.session_state["running"]:
        count = 0
        while st.session_state["running"]:
            now = time.strftime("%H:%M:%S")
            count += 1
            status_box.success(f"收到心跳包 | 序号: {count} | 时间: {now}")
            new_data = pd.DataFrame({"时间":[now], "序号":[count]})
            st.session_state["heartbeat_data"] = pd.concat([st.session_state["heartbeat_data"], new_data], ignore_index=True)
            chart_box.line_chart(st.session_state["heartbeat_data"], x="时间", y="序号")
            time.sleep(1)
    else:
        status_box.info("点击「开始监测」按钮启动心跳包模拟")
