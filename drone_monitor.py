import streamlit as st
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw

# ------------------- 页面配置 -------------------
st.set_page_config(page_title="无人机监控系统", layout="wide")

# 侧边栏导航（和示例一样的布局）
page = st.sidebar.radio("功能页面", ["航线规划", "飞行监控"])

# ------------------- 全局变量初始化 -------------------
if "heartbeat_data" not in st.session_state:
    st.session_state["heartbeat_data"] = pd.DataFrame(columns=["时间", "序号"])
if "running" not in st.session_state:
    st.session_state["running"] = False

# ------------------- 1. 航线规划页面（地图页面） -------------------
if page == "航线规划":
    st.header("🗺️ 航线规划")
    # 左右分栏：左地图、右侧控制面板
    map_col, ctrl_col = st.columns([3, 1])

    # ------------------- 右侧控制面板 -------------------
    with ctrl_col:
        # 坐标系设置（和示例一样默认选GCJ-02）
        st.subheader("坐标系设置")
        coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02(高德/百度)"], index=1)

        # 起点A（和示例完全一致的校园坐标）
        st.subheader("起点A")
        lat_a = st.number_input("纬度", value=32.2322, format="%.4f", key="lat_a")
        lon_a = st.number_input("经度", value=118.7490, format="%.4f", key="lon_a")
        set_a = st.button("设置A点")

        # 终点B（和示例完全一致的校园坐标）
        st.subheader("终点B")
        lat_b = st.number_input("纬度", value=32.2343, format="%.4f", key="lat_b")
        lon_b = st.number_input("经度", value=118.7490, format="%.4f", key="lon_b")
        set_b = st.button("设置B点")

        # 飞行参数
        st.subheader("飞行参数")
        height = st.slider("设定飞行高度(m)", 0, 200, 50)

        # 系统状态提示（和示例一样的状态框）
        st.markdown("### 系统状态")
        if set_a:
            st.success("✅ A点已设置")
        if set_b:
            st.success("✅ B点已设置")

    # ------------------- 左侧地图显示 -------------------
    with map_col:
        # 地图中心直接设为校园区域，打开页面就显示校园
        campus_lat = 32.2330
        campus_lon = 118.7490

        # 卫星地图底图（和示例一致的Esri影像）
        m = folium.Map(
            location=[campus_lat, campus_lon],
            zoom_start=16,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        )

        # 左侧障碍物绘制工具栏（作业要求）
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

        # 添加A、B点标记（和示例一样的红/绿色标记）
        if set_a or set_b:
            # 暂时去掉坐标转换，先保证点位在校园里
            folium.Marker([lat_a, lon_a], popup="起点A", icon=folium.Icon(color="red")).add_to(m)
            folium.Marker([lat_b, lon_b], popup="终点B", icon=folium.Icon(color="green")).add_to(m)

        # 渲染地图
        st_folium(m, width=720, height=520)

# ------------------- 2. 飞行监控页面（心跳包页面） -------------------
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
            now_time = time.strftime("%H:%M:%S")
            count += 1

            status_placeholder.success(f"收到心跳包 | 序号: {count} | 时间: {now_time}")

            new_row = pd.DataFrame({"时间": [now_time], "序号": [count]})
            st.session_state["heartbeat_data"] = pd.concat([st.session_state["heartbeat_data"], new_row], ignore_index=True)

            chart_placeholder.line_chart(st.session_state["heartbeat_data"], x="时间", y="序号")

            time.sleep(1)
    else:
        status_placeholder.info("点击「开始监测」按钮启动心跳包模拟")
