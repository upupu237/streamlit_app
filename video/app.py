import streamlit as st
import logging
import time
import os
import sys
import threading
from datetime import datetime

# 导入自定义模块（整理重复导入，确保仅导入一次）
from video.session_state import init_session_state
from video.ui_utils import set_page_config, load_custom_css
from video.analyzers import init_analyzers, analyze_frames
from video.recording_controls import start_recording, stop_recording
from video.video_analysis import score_selected_video
from video.utils import get_latest_video, delete_all_videos, export_analysis, open_folder, load_saved_reports
from video.analysis_display import show_detailed_analysis
from video.recorder import VideoRecorder

# 配置日志（保持原有配置）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("video_analysis.log"),
        logging.StreamHandler()
    ]
)


# 内部函数：初始化视频会话状态
def _init_video_session_state():
    """初始化视频分析功能所需的会话状态变量"""
    # 基础会话状态初始化
    init_session_state()

    # 视频录制器实例化（确保单例）
    if 'video_recorder' not in st.session_state:
        st.session_state.video_recorder = VideoRecorder()

    # 分析线程初始化（按需创建）
    if st.session_state.get('analyzers_loaded', False) and 'analysis_thread' not in st.session_state:
        st.session_state.analysis_thread = threading.Thread(
            target=analyze_frames,
            daemon=True
        )
        st.session_state.analysis_thread.start()


# 内部函数：渲染录制视频页面
def _render_recording_page():
    """封装录制视频页面逻辑"""
    from .pages.render_recording_page import render_recording_page
    render_recording_page()


# 内部函数：渲染评分视频页面
def _render_scoring_page():
    """封装评分视频页面逻辑"""
    from .pages.render_scoring_page import render_scoring_page
    render_scoring_page()


# 内部函数：渲染视频管理页面
def _render_management_page():
    """封装视频管理页面逻辑"""
    from .pages.render_management_page import render_management_page
    render_management_page()


# 内部函数：渲染分析报告页面
def _render_reports_page():
    """封装分析报告页面逻辑"""
    from .pages.render_reports_page import render_reports_page
    render_reports_page()


# 内部函数：显示帮助信息
def _show_help_info():
    """封装帮助信息展示逻辑"""
    with st.expander("使用指南", expanded=True):
        st.markdown("""
        ### 系统功能说明
        1. **视频录制**：点击"开始录制"启动摄像头，录制过程中实时分析姿态和表情
        2. **视频评分**：支持上传视频或选择已录制视频进行多维度分析
        3. **视频管理**：查看、分析或删除已录制的视频
        4. **分析报告**：查看和管理已保存的分析报告（含帧描述详情）

        ### 评分标准
        - 85分以上：优秀
        - 70-85分：良好
        - 60-70分：一般
        - 60分以下：需改进

        ### 常见问题
        - **未生成帧描述**：视频过短（<3秒）、质量过差或角度问题可能导致，建议重新录制
        - **分析失败**：确保视频格式为MP4/AVI，且文件未损坏
        """)


# 核心功能封装：视频分析应用入口
def show_video_app():
    """展示完整的视频分析功能（包含四个功能页面）"""
    # 页面配置
    set_page_config()

    # 加载自定义CSS
    load_custom_css()

    # 初始化分析器
    analyzers_loaded = init_analyzers()
    st.session_state.analyzers_loaded = analyzers_loaded

    # 初始化会话状态及线程
    _init_video_session_state()


    # 系统状态检查
    if not analyzers_loaded:
        st.error("⚠️ 分析器加载失败，部分功能可能无法使用")

    # 加载本地保存的报告
    load_saved_reports()

    # 侧边栏导航
    with st.sidebar:
        st.markdown("""
        <h5 class='sub-header'>视频功能导航</h3>
        """, unsafe_allow_html=True)
        page = st.radio("", ["录制视频", "评分视频", "管理视频", "分析报告"])

        # 帮助按钮逻辑
        def toggle_help():
            st.session_state.show_help = not st.session_state.get('show_help', False)

        st.button("使用帮助", on_click=toggle_help)

        # 显示帮助信息
        if st.session_state.get('show_help', False):
            _show_help_info()

    # 页面渲染分发
    if page == "录制视频":
        _render_recording_page()
    elif page == "评分视频":
        _render_scoring_page()
    elif page == "管理视频":
        _render_management_page()
    elif page == "分析报告":
        _render_reports_page()

    # 页脚
    st.markdown("""
    ---
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        面试姿态分析系统 v1.0 | 提供实时面试姿态与微表情分析
    </div>
    """, unsafe_allow_html=True)


# 脚本独立运行入口
if __name__ == "__main__":
    show_video_app()