import streamlit as st
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import math

# ------------------- 坐标系转换工具函数 -------------------
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

# ------------------- 页面配置 -------------------
st.set_page_config(page_title="无人机监控系统", layout="wide")

# 侧边栏导航（实现双页面切换）
page = st.sidebar.radio("功能页面", ["航线规划", "飞行监控"])

# ------------------- 全局变量初始化 -------------------
if "heartbeat_data" not in st.session_state:
    st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
if "running" not in st.session_state:
    st.session_state["running"] = False

# ------------------- 1. 航线规划页面 -------------------
if page == "航线规划":
    st.header("🗺️ 航线规划")
    col1, col2 = st.columns([3, 1])

    # 先获取所有坐标设置
    with col2:
        # 坐标系设置
        st.subheader("坐标系设置")
        coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02(高德/百度)"])

        # 起点A设置（增加唯一key解决ID冲突）
        st.subheader("起点A")
        lat_a = st.number_input("纬度", value=32.2322, format="%.4f", key="lat_a")
        lon_a = st.number_input("经度", value=118.749, format="%.4f", key="lon_a")
        set_a = st.button("设置A点")

        # 终点B设置（独立key，不再和A点组件ID重复）
        st.subheader("终点B")
        lat_b = st.number_input("纬度", value=32.2343, format="%.4f", key="lat_b")
        lon_b = st.number_input("经度", value=118.749, format="%.4f", key="lon_b")
        set_b = st.button("设置B点")

        # 飞行参数
        st.subheader("飞行参数")
        height = st.slider("设定飞行高度(m)", 0, 200, 50)

        # 状态提示
        if set_a:
            st.success("✅ A点已设置")
        if set_b:
            st.success("✅ B点已设置")

    # 再处理地图显示
    with col1:
        # 坐标转换
        if coord_type == "GCJ-02(高德/百度)":
            lat_a_map, lon_a_map = wgs84_to_gcj02(lat_a, lon_a)
            lat_b_map, lon_b_map = wgs84_to_gcj02(lat_b, lon_b)
        else:
            lat_a_map, lon_a_map = lat_a, lon_a
            lat_b_map, lon_b_map = lat_b, lon_b

        # 计算地图中心
        center_lat = (lat_a_map + lat_b_map) / 2
        center_lon = (lon_a_map + lon_b_map) / 2

        # 初始化卫星地图（和作业截图一致）
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=16,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        )

        # 添加障碍物圈选工具（作业要求）
        Draw(
            draw_options={
                'polyline': True,
                'polygon': True,
                'rectangle': True,
                'circle': True,
                'marker': False
            },
            edit_options={'edit': True}
        ).add_to(m)

        # 添加A、B点标记
        if set_a:
            folium.Marker([lat_a_map, lon_a_map], popup="起点A", icon=folium.Icon(color="red")).add_to(m)
        if set_b:
            folium.Marker([lat_b_map, lon_b_map], popup="终点B", icon=folium.Icon(color="green")).add_to(m)

        # 显示地图
        st_folium(m, width=700, height=500)

# ------------------- 2. 飞行监控页面（你的心跳包代码） -------------------
elif page == "飞行监控":
    st.header("📡 实时心跳包序号与时间变化")

    # 控制按钮
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        start_btn = st.button("开始监测")
    with col_btn2:
        stop_btn = st.button("停止监测")

    if start_btn:
        st.session_state["running"] = True
        st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
    if stop_btn:
        st.session_state["running"] = False

    # 显示区域
    status_placeholder = st.empty()
    chart_placeholder = st.empty()

    # 心跳包模拟循环
    if st.session_state["running"]:
        count = 0
        while st.session_state["running"]:
            # 获取当前时间和序号
            now_time = time.strftime("%H:%M:%S")
            count += 1

            # 更新状态显示
            status_placeholder.success(f"收到心跳包 | 序号: {count} | 时间: {now_time}")

            # 保存数据
            new_row = pd.DataFrame({"时间": [now_time], "序号": [count]})
            st.session_state["heartbeat_data"] = pd.concat([st.session_state["heartbeat_data"], new_row], ignore_index=True)

            # 更新折线图
            chart_placeholder.line_chart(st.session_state["heartbeat_data"], x="时间", y="序号")

            time.sleep(1)
    else:
        status_placeholder.info("点击「开始监测」按钮启动心跳包模拟")
