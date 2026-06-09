import streamlit as st
import time
import pandas as pd
from datetime import datetime

# 初始化数据存储
if 'heartbeat_list' not in st.session_state:
    st.session_state['heartbeat_list'] = []
if 'last_receive_time' not in st.session_state:
    st.session_state['last_receive_time'] = time.time()
if 'seq_num' not in st.session_state:
    st.session_state['seq_num'] = 0

# 页面标题
st.title("无人机心跳监测可视化")
st.subheader("实时心跳包序号与时间变化")

# 模拟无人机发送心跳包
def send_heartbeat():
    st.session_state['seq_num'] += 1
    current_time = datetime.now().strftime("%H:%M:%S")
    data = {
        "序号": st.session_state['seq_num'],
        "时间": current_time
    }
    st.session_state['heartbeat_list'].append(data)
    st.session_state['last_receive_time'] = time.time()
    return data

# 断线检测（3秒没收到就报警）
def check_connection():
    current_time = time.time()
    if current_time - st.session_state['last_receive_time'] > 3:
        st.error("⚠️ 连接超时！无人机疑似断线！")
        return False
    return True

# 开始按钮
if st.button("开始监测"):
    placeholder = st.empty()
    while True:
        with placeholder.container():
            # 发送并记录心跳
            new_data = send_heartbeat()
            st.success(f"收到心跳包 | 序号：{new_data['序号']} | 时间：{new_data['时间']}")
            
            # 检查是否断线
            check_connection()

            # 画折线图
            df = pd.DataFrame(st.session_state['heartbeat_list'])
            st.line_chart(df, x="时间", y="序号")

            # 控制每秒发一次心跳
            time.sleep(1)