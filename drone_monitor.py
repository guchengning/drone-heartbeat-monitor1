# pages/1_航线规划.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import json
import datetime
import math
import os
import time
from shapely.geometry import Polygon, Point, LineString

# ==================== 页面配置 ====================
st.set_page_config(page_title="航线规划 + 飞行监控", layout="wide")
st.title("🗺️ 航线规划 + 飞行监控 (智能避障)")

# ==================== 坐标转换 ====================
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
    return lat, lng

def calculate_distance(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

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

# ==================== 航线规划 ====================
def calculate_waypoints_with_safety(A, B, obstacles, flight_height, safe_radius=5):
    buffered_obstacles = []
    for obs in obstacles:
        if obs.get("height", 0) >= flight_height:
            poly = Polygon(obs["coordinates"])
            center = poly.centroid
            meter_per_deg = 111320 * math.cos(math.radians(center.y))
            buffer_deg = safe_radius / meter_per_deg if meter_per_deg > 0 else 0
            buffered = poly.buffer(buffer_deg)
            buffered_obstacles.append(buffered)
    
    line = LineString([A, B])
    need_detour = False
    for buffered in buffered_obstacles:
        if line.intersects(buffered):
            need_detour = True
            break
    
    if not need_detour:
        return [A, B], "直线飞行(安全)"
    
    detour_points = []
    for buffered in buffered_obstacles:
        if line.intersects(buffered):
            intersection = line.intersection(buffered)
            if not intersection.is_empty:
                if intersection.geom_type == "LineString":
                    coords = list(intersection.coords)
                    if len(coords) >= 2:
                        detour_points.extend([coords[0], coords[-1]])
                elif intersection.geom_type == "Point":
                    detour_points.append((intersection.x, intersection.y))
    
    seen = set()
    unique_points = []
    for p in detour_points:
        key = (round(p[0], 8), round(p[1], 8))
        if key not in seen:
            seen.add(key)
            unique_points.append(p)
    
    if unique_points:
        unique_points.sort(key=lambda p: line.project(Point(p)))
    
    waypoints_left = [A]
    waypoints_right = [A]
    waypoints_optimal = [A]
    
    if not unique_points:
        return [A, B], "直线飞行(无障碍)"
    
    for i, point in enumerate(unique_points):
        if i < len(unique_points) - 1:
            next_point = unique_points[i + 1]
            dx = next_point[0] - point[0]
            dy = next_point[1] - point[1]
        else:
            dx = B[0] - point[0]
            dy = B[1] - point[1]
        
        length = math.sqrt(dx**2 + dy**2)
        if length > 0:
            dx /= length
            dy /= length
        else:
            dx, dy = 1, 0
        
        perp_x = -dy
        perp_y = dx
        
        lat_mid = (point[1] + B[1]) / 2
        meter_per_deg = 111320 * math.cos(math.radians(lat_mid))
        if meter_per_deg <= 0:
            meter_per_deg = 111320
        offset_deg = (safe_radius * 2) / meter_per_deg
        
        left_point = (point[0] + perp_x * offset_deg, point[1] + perp_y * offset_deg)
        right_point = (point[0] - perp_x * offset_deg, point[1] - perp_y * offset_deg)
        
        waypoints_left.append(left_point)
        waypoints_right.append(right_point)
        optimal_point = ((left_point[0] + right_point[0]) / 2, (left_point[1] + right_point[1]) / 2)
        waypoints_optimal.append(optimal_point)
    
    waypoints_left.append(B)
    waypoints_right.append(B)
    waypoints_optimal.append(B)
    
    return {
        "left": waypoints_left,
        "right": waypoints_right,
        "optimal": waypoints_optimal
    }, "需要绕行"

# ==================== 飞行监控类 ====================
class FlightMonitor:
    def __init__(self, waypoints, speed=10):
        self.waypoints = waypoints
        self.speed = speed
        self.current_index = 0
        self.current_position = waypoints[0] if waypoints else None
        self.start_time = None
        self.is_flying = False
        self.total_distance = self.calculate_total_distance()
        
    def calculate_total_distance(self):
        total = 0
        for i in range(len(self.waypoints) - 1):
            p1 = self.waypoints[i]
            p2 = self.waypoints[i + 1]
            total += calculate_distance(p1[1], p1[0], p2[1], p2[0])
        return total
    
    def get_remaining_distance(self):
        if self.current_index >= len(self.waypoints) - 1:
            return 0
        remaining = 0
        if self.current_position:
            current_target = self.waypoints[self.current_index + 1]
            remaining += calculate_distance(
                self.current_position[1], self.current_position[0],
                current_target[1], current_target[0]
            )
        for i in range(self.current_index + 1, len(self.waypoints) - 1):
            p1 = self.waypoints[i]
            p2 = self.waypoints[i + 1]
            remaining += calculate_distance(p1[1], p1[0], p2[1], p2[0])
        return remaining
    
    def get_elapsed_time(self):
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def get_estimated_time(self):
        remaining_dist = self.get_remaining_distance()
        if self.speed > 0:
            return remaining_dist / self.speed
        return 0
    
    def update(self, dt):
        if not self.is_flying or self.current_index >= len(self.waypoints) - 1:
            return False
        
        current_target = self.waypoints[self.current_index + 1]
        dist_to_target = calculate_distance(
            self.current_position[1], self.current_position[0],
            current_target[1], current_target[0]
        )
        
        move_dist = self.speed * dt
        
        if move_dist >= dist_to_target:
            self.current_index += 1
            self.current_position = current_target
            if self.current_index >= len(self.waypoints) - 1:
                self.is_flying = False
                return False
        else:
            dx = current_target[0] - self.current_position[0]
            dy = current_target[1] - self.current_position[1]
            ratio = move_dist / dist_to_target
            self.current_position = (
                self.current_position[0] + dx * ratio,
                self.current_position[1] + dy * ratio
            )
        return True
    
    def start(self):
        self.is_flying = True
        self.start_time = time.time()
    
    def pause(self):
        self.is_flying = False
    
    def reset(self):
        self.current_index = 0
        self.current_position = self.waypoints[0] if self.waypoints else None
        self.start_time = None
        self.is_flying = False

# ==================== 初始化 ====================
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2323, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2344, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 10
if 'safe_radius' not in st.session_state:
    st.session_state.safe_radius = 10
if 'flight_speed' not in st.session_state:
    st.session_state.flight_speed = 10
if 'polygon_obstacles' not in st.session_state:
    try:
        with open("obstacle_config.json", "r") as f:
            st.session_state.polygon_obstacles = json.load(f).get("obstacles", [])
    except:
        st.session_state.polygon_obstacles = []
if 'selected_route' not in st.session_state:
    st.session_state.selected_route = "optimal"
if 'temp_new_obstacle' not in st.session_state:
    st.session_state.temp_new_obstacle = None
if 'waypoints' not in st.session_state:
    st.session_state.waypoints = None
if 'flight_monitor' not in st.session_state:
    st.session_state.flight_monitor = None
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'battery_level' not in st.session_state:
    st.session_state.battery_level = 100
if 'flight_log' not in st.session_state:
    st.session_state.flight_log = []
if 'route_message' not in st.session_state:
    st.session_state.route_message = ""

def save_obstacles():
    config = {
        "save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "flight_height": st.session_state.flight_height,
        "safe_radius": st.session_state.safe_radius,
        "obstacles": st.session_state.polygon_obstacles
    }
    with open("obstacle_config.json", "w") as f:
        json.dump(config, f)

def generate_waypoints():
    A_geo = (st.session_state.pointA["lng"], st.session_state.pointA["lat"])
    B_geo = (st.session_state.pointB["lng"], st.session_state.pointB["lat"])
    
    obstacles_for_route = []
    for obs in st.session_state.polygon_obstacles:
        obstacles_for_route.append({
            "coordinates": obs["coordinates"],
            "height": obs.get("height", 40)
        })
    
    route_result = calculate_waypoints_with_safety(
        A_geo, B_geo, obstacles_for_route,
        st.session_state.flight_height,
        st.session_state.safe_radius
    )
    
    if isinstance(route_result, tuple) and len(route_result) == 2:
        waypoints_dict, message = route_result
        if isinstance(waypoints_dict, dict):
            if st.session_state.selected_route in waypoints_dict:
                selected_waypoints = waypoints_dict[st.session_state.selected_route]
            else:
                selected_waypoints = waypoints_dict.get("optimal", [A_geo, B_geo])
            st.session_state.waypoints = selected_waypoints
            st.session_state.route_message = message
        else:
            st.session_state.waypoints = waypoints_dict
            st.session_state.route_message = message
    else:
        st.session_state.waypoints = route_result
        st.session_state.route_message = "直线飞行"
    
    if st.session_state.waypoints and len(st.session_state.waypoints) >= 2:
        st.session_state.flight_monitor = FlightMonitor(st.session_state.waypoints, st.session_state.flight_speed)
    
    st.session_state.simulation_running = False

# ==================== 布局 ====================
map_col, monitor_col, control_col = st.columns([2.5, 0.8, 1.2])

with map_col:
    st.subheader("卫星地图 + 障碍物")
    
    latA_disp, lngA_disp = to_wgs84_display(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
    latB_disp, lngB_disp = to_wgs84_display(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)
    
    center_lat = (latA_disp + latB_disp) / 2
    center_lng = (lngA_disp + lngB_disp) / 2
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=17,
                   tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                   attr="Esri Satellite")
    
    folium.Marker([latA_disp, lngA_disp], popup=f"起点 A", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([latB_disp, lngB_disp], popup=f"终点 B", icon=folium.Icon(color="red")).add_to(m)
    
    # 绘制航线
    if st.session_state.waypoints:
        display_waypoints = []
        for lng, lat in st.session_state.waypoints:
            if st.session_state.coord_type == "GCJ-02":
                wgs_lng, wgs_lat = wgs84_to_gcj02(lng, lat)
            else:
                wgs_lng, wgs_lat = lng, lat
            display_waypoints.append([wgs_lat, wgs_lng])
        folium.PolyLine(display_waypoints, color="blue", weight=4, opacity=0.8).add_to(m)
        
        if st.session_state.flight_monitor and st.session_state.flight_monitor.current_position:
            pos = st.session_state.flight_monitor.current_position
            if st.session_state.coord_type == "GCJ-02":
                disp_lng, disp_lat = wgs84_to_gcj02(pos[0], pos[1])
            else:
                disp_lng, disp_lat = pos[0], pos[1]
            folium.Marker([disp_lat, disp_lng], icon=folium.Icon(color="purple", icon="plane", prefix="fa"),
                         popup="无人机").add_to(m)
    
    # 绘制障碍物
    for i, obs in enumerate(st.session_state.polygon_obstacles):
        coords = [[lat, lng] for lng, lat in obs["coordinates"]]
        color = "red" if obs["height"] >= st.session_state.flight_height else "orange"
        folium.Polygon(locations=coords, color=color, fill=True, fill_opacity=0.3,
                       popup=f"{obs.get('name', f'障碍物{i+1}')}<br>高度: {obs['height']}m").add_to(m)
    
    Draw(draw_options={
        "polygon": {"shapeOptions": {"color": "#ffdd00"}},
        "rectangle": {"shapeOptions": {"color": "#ffdd00"}},
        "circle": {"shapeOptions": {"color": "#ffdd00"}},
        "polyline": False, "marker": False, "circlemarker": False
    }).add_to(m)
    MousePosition().add_to(m)
    
    output = st_folium(m, height=650, width="100%", key="map")
    
    # 处理绘制
    if output and output.get("last_active_drawing"):
        drawing = output["last_active_drawing"]
        if drawing and drawing.get("geometry"):
            geom = drawing["geometry"]
            coords = []
            
            if geom["type"] == "Polygon":
                raw = geom["coordinates"][0]
                for lng, lat in raw:
                    if st.session_state.coord_type == "GCJ-02":
                        gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
                        coords.append([gcj_lng, gcj_lat])
                    else:
                        coords.append([lng, lat])
            elif geom["type"] == "Circle":
                center = geom["coordinates"][0]
                radius = geom["coordinates"][1]
                if st.session_state.coord_type == "GCJ-02":
                    gcj_lng, gcj_lat = wgs84_to_gcj02(center[0], center[1])
                else:
                    gcj_lng, gcj_lat = center[0], center[1]
                coords = circle_to_polygon(gcj_lng, gcj_lat, radius)
            
            if coords and st.session_state.temp_new_obstacle is None:
                st.session_state.temp_new_obstacle = coords
                st.rerun()

with monitor_col:
    st.subheader("飞行监控")
    
    if st.session_state.waypoints:
        st.info(f"航线: {st.session_state.selected_route} | {st.session_state.route_message}")
        st.metric("总航点数", f"{len(st.session_state.waypoints)}")
        st.metric("总航程", f"{st.session_state.flight_monitor.total_distance:.1f}m" if st.session_state.flight_monitor else "N/A")
    else:
        st.warning("请先生成航线")
    
    st.divider()
    st.markdown("### 飞行状态")
    
    if st.session_state.flight_monitor:
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("当前航点", f"{st.session_state.flight_monitor.current_index + 1}/{len(st.session_state.flight_monitor.waypoints)}")
        with col_b:
            st.metric("飞行速度", f"{st.session_state.flight_speed} m/s")
        
        st.metric("已用时间", f"{st.session_state.flight_monitor.get_elapsed_time():.1f}s")
        st.metric("剩余距离", f"{st.session_state.flight_monitor.get_remaining_distance():.1f}m")
        st.metric("预计到达", f"{st.session_state.flight_monitor.get_estimated_time():.1f}s")
        
        if st.session_state.simulation_running:
            elapsed = st.session_state.flight_monitor.get_elapsed_time()
            estimated_total = st.session_state.flight_monitor.total_distance / st.session_state.flight_speed if st.session_state.flight_speed > 0 else 1
            battery_used = min(100, (elapsed / estimated_total) * 100) if estimated_total > 0 else 0
            st.session_state.battery_level = max(0, 100 - battery_used)
        
        st.progress(st.session_state.battery_level / 100)
        st.metric("电量", f"{st.session_state.battery_level:.1f}%")
        
        st.divider()
        
        col_start, col_pause, col_reset = st.columns(3)
        with col_start:
            if st.button("开始", use_container_width=True):
                if st.session_state.flight_monitor and not st.session_state.simulation_running:
                    st.session_state.flight_monitor.start()
                    st.session_state.simulation_running = True
                    st.rerun()
        with col_pause:
            if st.button("暂停", use_container_width=True):
                if st.session_state.flight_monitor and st.session_state.simulation_running:
                    st.session_state.flight_monitor.pause()
                    st.session_state.simulation_running = False
                    st.rerun()
        with col_reset:
            if st.button("重置", use_container_width=True):
                if st.session_state.flight_monitor:
                    st.session_state.flight_monitor.reset()
                    st.session_state.simulation_running = False
                    st.session_state.battery_level = 100
                    st.rerun()
    
    st.divider()
    st.markdown("### 飞行日志")
    log_container = st.container(height=150)
    with log_container:
        if st.session_state.flight_log:
            for log in st.session_state.flight_log[-10:]:
                st.caption(log)
        else:
            st.caption("等待飞行...")

with control_col:
    st.subheader("控制面板")
    
    coord_opt = st.radio("坐标系", ["WGS-84", "GCJ-02"], index=1)
    st.session_state.coord_type = coord_opt
    
    st.divider()
    st.markdown("### 起终点")
    
    st.markdown("**起点 A (32.2323, 118.749)**")
    latA = st.number_input("纬度", value=st.session_state.pointA["lat"], format="%.6f")
    lngA = st.number_input("经度", value=st.session_state.pointA["lng"], format="%.6f")
    if st.button("设置A点"):
        st.session_state.pointA = {"lat": latA, "lng": lngA}
        st.rerun()
    
    st.markdown("**终点 B (32.2344, 118.749)**")
    latB = st.number_input("纬度", value=st.session_state.pointB["lat"], format="%.6f", key="latB")
    lngB = st.number_input("经度", value=st.session_state.pointB["lng"], format="%.6f", key="lngB")
    if st.button("设置B点"):
        st.session_state.pointB = {"lat": latB, "lng": lngB}
        st.rerun()
    
    st.divider()
    st.markdown("### 飞行参数")
    st.session_state.flight_height = st.number_input("飞行高度(m)", value=st.session_state.flight_height, step=5)
    st.session_state.safe_radius = st.number_input("安全半径(m)", value=st.session_state.safe_radius, step=1)
    st.session_state.flight_speed = st.number_input("飞行速度(m/s)", value=st.session_state.flight_speed, step=1)
    
    st.divider()
    st.markdown("### 航线选择")
    route_option = st.radio("绕行策略", ["optimal", "left", "right"],
                           format_func=lambda x: {"optimal": "最佳航线", "left": "向左绕行", "right": "向右绕行"}[x])
    if route_option != st.session_state.selected_route:
        st.session_state.selected_route = route_option
        generate_waypoints()
        st.rerun()
    
    if st.button("生成航线", type="primary", use_container_width=True):
        generate_waypoints()
        st.rerun()
    
    st.divider()
    st.markdown("### 障碍物管理")
    
    if st.session_state.temp_new_obstacle is not None:
        st.warning("检测到新绘制的区域，请设置高度")
        new_height = st.number_input("障碍物高度(米)", min_value=0, max_value=500, value=40, step=5, key="new_h")
        new_name = st.text_input("名称", value=f"障碍物{len(st.session_state.polygon_obstacles)+1}", key="new_n")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认添加", type="primary", use_container_width=True):
                st.session_state.polygon_obstacles.append({
                    "name": new_name,
                    "coordinates": st.session_state.temp_new_obstacle,
                    "height": new_height
                })
                save_obstacles()
                st.session_state.temp_new_obstacle = None
                st.success(f"已添加 {new_name}")
                st.rerun()
        with col2:
            if st.button("取消", use_container_width=True):
                st.session_state.temp_new_obstacle = None
                st.rerun()
    else:
        st.info("在地图上绘制多边形/矩形/圆形")
    
    col_save, col_load = st.columns(2)
    with col_save:
        if st.button("一键保存", use_container_width=True):
            save_obstacles()
            st.success("已保存")
    with col_load:
        if st.button("加载记忆", use_container_width=True):
            try:
                with open("obstacle_config.json", "r") as f:
                    config = json.load(f)
                    st.session_state.polygon_obstacles = config.get("obstacles", [])
                    st.session_state.flight_height = config.get("flight_height", 10)
                    st.session_state.safe_radius = config.get("safe_radius", 10)
                st.success("已加载")
                st.rerun()
            except:
                st.warning("未找到文件")
    
    if st.button("清理所有", use_container_width=True):
        st.session_state.polygon_obstacles = []
        try:
            os.remove("obstacle_config.json")
        except:
            pass
        st.rerun()
    
    st.info(f"障碍物数量: {len(st.session_state.polygon_obstacles)}")
    
    with st.expander("障碍物列表"):
        if st.session_state.polygon_obstacles:
            for i, obs in enumerate(st.session_state.polygon_obstacles):
                st.write(f"{i+1}. {obs.get('name', f'障碍物{i+1}')} - {obs.get('height', 40)}m")
        else:
            st.write("暂无")

# ==================== 模拟飞行更新 ====================
if st.session_state.simulation_running and st.session_state.flight_monitor:
    dt = 0.5
    completed = st.session_state.flight_monitor.update(dt)
    if completed:
        st.session_state.simulation_running = False
        st.session_state.flight_log.append(f"{datetime.datetime.now().strftime('%H:%M:%S')} - 飞行完成")
        st.rerun()
    else:
        st.session_state.flight_log.append(
            f"{datetime.datetime.now().strftime('%H:%M:%S')} - 航点 {st.session_state.flight_monitor.current_index + 1}"
        )
    time.sleep(0.1)
    st.rerun()

st.divider()
st.caption(f"A点: 32.2323, 118.749 | B点: 32.2344, 118.749 | 障碍物: {len(st.session_state.polygon_obstacles)}个 | 坐标系: {st.session_state.coord_type}")
