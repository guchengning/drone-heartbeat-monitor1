import streamlit as st
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw

# 页面基础配置
st.set_page_config(page_title="无人机监控系统", layout="wide")

# 侧边双页面切换
page = st.sidebar.radio("功能页面", ["航线规划", "飞行监控"])

# 会话状态初始化心跳包
if "heartbeat_data" not in st.session_state:
    st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
if "running" not in st.session_state:
    st.session_state["running"] = False

# ========== 航线规划页面 ==========
if page == "航线规划":
    st.header("🗺️ 航线规划")
    map_col, ctrl_col = st.columns([3, 1])

    with ctrl_col:
        st.subheader("坐标系设置")
        coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02(高德/百度)"], index=1)

        st.subheader("起点A")
        lat_a = st.number_input("纬度", value=32.2322, format="%.4f", key="lat_a_in")
        lon_a = st.number_input("经度", value=118.7490, format="%.4f", key="lon_a_in")

        st.subheader("终点B")
        lat_b = st.number_input("纬度", value=32.2343, format="%.4f", key="lat_b_in")
        lon_b = st.number_input("经度", value=118.7490, format="%.4f", key="lon_b_in")

        st.subheader("飞行参数")
        fly_height = st.slider("设定飞行高度(m)", min_value=0, max_value=200, value=50)

    with map_col:
        # 先不做坐标转换，直接用原始坐标渲染，保证点位在视野内
        a_lat_map, a_lon_map = lat_a, lon_a
        b_lat_map, b_lon_map = lat_b, lon_b

        map_center_lat = (lat_a + lat_b) / 2
        map_center_lon = (lon_a + lon_b) / 2

        # 卫星底图
        m = folium.Map(
            location=[map_center_lat, map_center_lon],
            zoom_start=16,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        )
        # 障碍物绘制工具栏
        Draw(
            draw_options={"polyline":True,"polygon":True,"rectangle":True,"circle":True,"marker":False},
            edit_options={"edit": True}
        ).add_to(m)

        # 强制添加两个标记，页面加载立刻显示
        folium.Marker([a_lat_map, a_lon_map], popup="起点A", icon=folium.Icon(color="red")).add_to(m)
        folium.Marker([b_lat_map, b_lon_map], popup="终点B", icon=folium.Icon(color="green")).add_to(m)

        # 渲染地图
        st_folium(m, width=720, height=520)

# ========== 飞行监控页面 ==========
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
