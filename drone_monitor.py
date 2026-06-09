import streamlit as st
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw

st.set_page_config(page_title="无人机监控系统", layout="wide")
page = st.sidebar.radio("功能页面", ["航线规划", "飞行监控"])

if "heartbeat_data" not in st.session_state:
    st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
if "running" not in st.session_state:
    st.session_state["running"] = False

if page == "航线规划":
    st.header("🗺️ 航线规划")
    map_area, ctrl_area = st.columns([3, 1])
    with ctrl_area:
        st.subheader("坐标系设置")
        coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02(高德/百度)"], index=1)

        # 校内湖边A点（经度大幅减小，左移校园）
        st.subheader("起点A")
        lat_a = st.number_input("纬度", value=32.2341, format="%.4f", key="la")
        lon_a = st.number_input("经度", value=118.7450, format="%.4f", key="loa")
        btn_a = st.button("设置A点")

        # 校内操场B点
        st.subheader("终点B")
        lat_b = st.number_input("纬度", value=32.2315, format="%.4f", key="lb")
        lon_b = st.number_input("经度", value=118.7440, format="%.4f", key="lob")
        btn_b = st.button("设置B点")

        st.subheader("飞行参数")
        st.slider("设定飞行高度(m)", min_value=0, max_value=200, value=50)
        if btn_a:
            st.success("✅ A点已设置")
        if btn_b:
            st.success("✅ B点已设置")

    with map_area:
        # 地图中心锁定校园湖泊
        center_lat = 32.2328
        center_lon = 118.7445
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=16,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        )
        Draw(draw_options={"polyline":True,"polygon":True,"rectangle":True,"circle":True,"marker":False}, edit_options={"edit":True}).add_to(m)
        # 渲染校内两点
        folium.Marker([lat_a, lon_a], popup="起点A（校园湖边）", icon=folium.Icon(color="red")).add_to(m)
        folium.Marker([lat_b, lon_b], popup="终点B（校园操场）", icon=folium.Icon(color="green")).add_to(m)
        st_folium(m, width=720, height=520)

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
