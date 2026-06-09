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

# 心跳包存储初始化
if "heartbeat_data" not in st.session_state:
    st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
if "running" not in st.session_state:
    st.session_state["running"] = False

# ========== 航线规划页面 ==========
if page == "航线规划":
    st.header("🗺️ 航线规划")
    map_area, ctrl_area = st.columns([3, 1])

    with ctrl_area:
        st.subheader("坐标系设置")
        coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02(高德/百度)"], index=1)

        # 起点A输入框
        st.subheader("起点A")
        lat_a = st.number_input("纬度", value=32.2322, format="%.4f", key="la")
        lon_a = st.number_input("经度", value=118.7490, format="%.4f", key="loa")
        btn_a = st.button("设置A点")

        # 终点B输入框
        st.subheader("终点B")
        lat_b = st.number_input("纬度", value=32.2343, format="%.4f", key="lb")
        lon_b = st.number_input("经度", value=118.7490, format="%.4f", key="lob")
        btn_b = st.button("设置B点")

        # 飞行高度
        st.subheader("飞行参数")
        st.slider("设定飞行高度(m)", min_value=0, max_value=200, value=50)

        # 点击按钮后的提示文字
        if btn_a:
            st.success("✅ A点已设置")
        if btn_b:
            st.success("✅ B点已设置")

    with map_area:
        # 地图中心固定校园中间坐标
        center_lat = 32.2330
        center_lon = 118.7490

        # 卫星地图
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=16,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        )
        # 左侧绘制障碍物工具
        Draw(draw_options={"polyline":True,"polygon":True,"rectangle":True,"circle":True,"marker":False}, edit_options={"edit":True}).add_to(m)

        # 【核心改动】无任何判断，直接强制添加A、B标记，页面一加载就出现
        folium.Marker(location=[lat_a, lon_a], popup="起点A", icon=folium.Icon(color="red")).add_to(m)
        folium.Marker(location=[lat_b, lon_b], popup="终点B", icon=folium.Icon(color="green")).add_to(m)

        # 渲染地图
        st_folium(m, width=720, height=520)

# ========== 飞行监控页面（心跳包） ==========
elif page == "飞行监控":
    st.header("📡 实时心跳包序号与时间变化")
    c1, c2 = st.columns(2)
    with c1:
        start = st.button("开始监测")
    with c2:
        stop = st.button("停止监测")

    if start:
        st.session_state["running"] = True
        st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
    if stop:
        st.session_state["running"] = False

    status_text = st.empty()
    chart_box = st.empty()

    if st.session_state["running"]:
        count = 0
        while st.session_state["running"]:
            t = time.strftime("%H:%M:%S")
            count += 1
            status_text.success(f"收到心跳包 | 序号: {count} | 时间: {t}")
            new_line = pd.DataFrame({"时间":[t], "序号":[count]})
            st.session_state["heartbeat_data"] = pd.concat([st.session_state["heartbeat_data"], new_line], ignore_index=True)
            chart_box.line_chart(st.session_state["heartbeat_data"], x="时间", y="序号")
            time.sleep(1)
    else:
        status_text.info("点击「开始监测」按钮启动心跳包模拟")
