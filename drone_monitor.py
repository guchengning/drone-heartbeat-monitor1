import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import json
import datetime

# 页面基础配置
st.set_page_config(page_title="航线规划障碍物", layout="wide")
st.title("🗺️ 航线规划 - 障碍物存储测试")

# 会话初始化（核心：障碍物永久存在内存）
if "obs_list" not in st.session_state:
    st.session_state.obs_list = []
if "draw_temp" not in st.session_state:
    st.session_state.draw_temp = None

# 保存配置字符串（一键部署=下载文件）
def get_config_data():
    data = {
        "save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "obstacles": st.session_state.obs_list
    }
    return json.dumps(data, indent=2, ensure_ascii=False)

# 分栏
map_area, ctrl_area = st.columns([3, 1])

# 左侧地图
with map_area:
    m = folium.Map(location=[32.233, 118.749], zoom_start=16,
                   tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")
    
    # 渲染已保存障碍物
    for obs in st.session_state.obs_list:
        points = [[lat, lng] for lng, lat in obs["coords"]]
        folium.Polygon(locations=points, color="red", fill=True, fill_opacity=0.2).add_to(m)

    # 绘图工具
    Draw(draw_options={
        "polygon": {"shapeOptions":{"color":"#ffdd00"}},
        "rectangle": {"shapeOptions":{"color":"#ffdd00"}},
        "circle": False,
        "polyline": False,
        "marker": False
    }).add_to(m)

    map_out = st_folium(m, height=700, key="main_map")

    # 捕获绘制图形
    if map_out and map_out.get("last_active_drawing"):
        draw_data = map_out["last_active_drawing"]
        if draw_data.get("geometry") and st.session_state.draw_temp is None:
            geo = draw_data["geometry"]
            if geo["type"] == "Polygon":
                st.session_state.draw_temp = geo["coordinates"][0]
                st.rerun()

# 右侧控制面板
with ctrl_area:
    st.subheader("障碍物管理")
    st.info(f"当前障碍物总数：{len(st.session_state.obs_list)}")

    # 绘制后弹窗确认添加
    if st.session_state.draw_temp is not None:
        st.warning("已绘制障碍物，请确认入库")
        obs_name = st.text_input("障碍物名称", value=f"障碍{len(st.session_state.obs_list)+1}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认添加", type="primary"):
                st.session_state.obs_list.append({
                    "name": obs_name,
                    "coords": st.session_state.draw_temp
                })
                st.session_state.draw_temp = None
                st.success("添加成功，计数+1")
                st.rerun()
        with col2:
            if st.button("❌ 取消绘制"):
                st.session_state.draw_temp = None
                st.rerun()
    else:
        st.write("在地图绘制矩形/多边形生成障碍物")

    st.divider()

    # 一键部署（下载配置文件，真正持久化）
    st.subheader("💾 一键部署（导出配置）")
    json_text = get_config_data()
    st.download_button(
        label="一键部署，下载obstacle_config.json",
        data=json_text,
        file_name="obstacle_config.json",
        mime="application/json",
        use_container_width=True
    )

    # 上传配置恢复
    st.subheader("📂 加载历史配置")
    upload_file = st.file_uploader("上传json文件恢复障碍物", type="json")
    if upload_file:
        try:
            load_data = json.load(upload_file)
            st.session_state.obs_list = load_data.get("obstacles", [])
            st.success("加载完成，障碍物已恢复")
            st.rerun()
        except Exception as err:
            st.error(f"加载失败：{err}")

    st.divider()
    # 清空全部
    if st.button("🗑️ 清空所有障碍物", use_container_width=True):
        st.session_state.obs_list = []
        st.success("已全部清空，计数归零")
        st.rerun()

    # 障碍物清单
    with st.expander("障碍物列表"):
        if st.session_state.obs_list:
            for idx, item in enumerate(st.session_state.obs_list):
                st.write(f"{idx+1}. {item['name']}")
        else:
            st.write("暂无障碍物")

st.divider()
st.caption("使用说明：地图绘制黄色框 → 右侧点确认添加 → 一键部署下载配置文件保存；下次上传文件恢复数据")
