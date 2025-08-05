import streamlit as st
import os
import tempfile
import json
from video.video_analysis import score_selected_video
from video.utils import open_folder
from video.analysis_display import show_detailed_analysis


def render_scoring_page():
    st.markdown("""
    <h2 class='sub-header'>视频评分</h2>
    """, unsafe_allow_html=True)

    # 视频选择
    video_option = st.radio("选择视频来源", ["上传视频文件", "选择已录制视频"])
    video_path = None

    if video_option == "上传视频文件":
        uploaded_file = st.file_uploader("选择视频文件", type=["mp4", "avi", "mov"])

        if uploaded_file:
            try:
                # 创建video/video目录用于保存上传的视频
                video_save_dir = os.path.join("video", "video")
                os.makedirs(video_save_dir, exist_ok=True)

                # 生成唯一文件名
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_ext = os.path.splitext(uploaded_file.name)[1]
                video_path = os.path.join(video_save_dir, f"uploaded_{timestamp}{file_ext}")

                # 保存视频文件
                with open(video_path, "wb") as f:
                    f.write(uploaded_file.read())

                st.success(f"已上传视频: {uploaded_file.name} (大小: {uploaded_file.size / 1024 / 1024:.2f}MB)")
                import logging
                logging.info(f"上传视频: {uploaded_file.name} 保存至: {video_path}")

                if st.button("打开视频所在文件夹"):
                    open_folder(video_save_dir)
            except Exception as e:
                st.error(f"上传失败: {str(e)}")
                import logging
                logging.error(f"上传视频失败: {e}")
    else:
        # 修改为video/video目录
        video_dir = os.path.join("video", "video")

        if os.path.exists(video_dir):
            mp4_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]

            if mp4_files:
                mp4_files.sort(key=lambda f: os.path.getmtime(os.path.join(video_dir, f)), reverse=True)
                selected_file = st.selectbox("选择已录制的视频", mp4_files)
                video_path = os.path.join(video_dir, selected_file)

                file_size = os.path.getsize(video_path) / (1024 * 1024)
                from datetime import datetime
                mod_time = datetime.fromtimestamp(os.path.getmtime(video_path)).strftime("%Y-%m-%d %H:%M:%S")
                st.info(f"选中视频: {selected_file} | 大小: {file_size:.2f} MB | 修改时间: {mod_time}")

                if st.button("打开视频所在文件夹"):
                    open_folder(video_dir)
            else:
                st.info("没有已录制的视频，请先录制视频")
        else:
            st.info("没有已录制的视频，请先录制视频")

    # 分析控制
    if video_path and os.path.exists(video_path):
        if st.button("开始分析") and st.session_state.analyzers_loaded:
            scores = score_selected_video(video_path)
            if scores and isinstance(scores, dict):
                st.session_state.video_scores = scores
                st.session_state.current_analysis = {
                    "scores": scores,
                    "video_path": video_path
                }

                # 自动保存分析报告到video/analysis_reports目录
                try:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    reports_dir = os.path.join("video", "analysis_reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    report_path = f"{reports_dir}/analysis_{timestamp}.json"

                    # 构建完整的报告数据
                    report_data = {
                        "scores": scores,
                        "video_path": video_path,
                        "time": timestamp,
                        "frame_descriptions": st.session_state.get("frame_descriptions", [])
                    }

                    # 保存报告
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(report_data, f, ensure_ascii=False, indent=2)

                    # 更新会话状态中的分析报告
                    if 'saved_analyses' not in st.session_state:
                        st.session_state.saved_analyses = {}
                    st.session_state.saved_analyses[report_path] = report_data

                    st.success(f"分析完成并已保存报告至: {report_path}")
                except Exception as e:
                    st.error(f"保存分析报告失败: {str(e)}")
                    import logging
                    logging.error(f"保存分析报告失败: {e}")
        elif not st.session_state.analyzers_loaded:
            st.warning("分析器未加载，无法进行分析")

    # 显示评分结果
    if 'video_scores' in st.session_state and st.session_state.video_scores:
        scores = st.session_state.video_scores
        if not isinstance(scores, dict):
            st.error("分析结果格式异常，无法显示")
            st.session_state.video_scores = None
        else:
            if st.session_state.current_analysis:
                show_detailed_analysis(scores, st.session_state.current_analysis["video_path"])