import streamlit as st
import os
import cv2
from video.utils import delete_all_videos, open_folder
from video.video_analysis import score_selected_video


def render_management_page():
    st.markdown("""
    <h2 class='sub-header'>视频管理</h2>
    """, unsafe_allow_html=True)

    # 视频文件夹路径，根据项目结构调整
    video_dir = r"video\video"
    if not os.path.exists(video_dir):
        st.info("没有视频文件夹，尚未录制任何视频")
        os.makedirs(video_dir, exist_ok=True)
    else:
        mp4_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]

        if not mp4_files:
            st.info("没有录制的视频文件")
        else:
            mp4_files.sort(key=lambda f: os.path.getmtime(os.path.join(video_dir, f)), reverse=True)

            st.subheader("已录制视频列表")
            st.write(f"共 {len(mp4_files)} 个视频文件")

            if st.button("打开视频文件夹"):
                open_folder(video_dir)

            col_batch1, col_batch2 = st.columns(2)
            with col_batch1:
                if st.button("删除所有视频", type="secondary"):
                    confirm = st.checkbox("确认删除所有视频（不可恢复）")
                    if confirm:
                        delete_all_videos(video_dir)
                        st.experimental_rerun()

            for i, file in enumerate(mp4_files):
                file_path = os.path.join(video_dir, file)
                if not os.path.exists(file_path):
                    continue

                file_size = os.path.getsize(file_path) / (1024 * 1024)
                from datetime import datetime
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                duration = 0

                try:
                    cap = cv2.VideoCapture(file_path)
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                    if fps > 0 and frame_count > 0:
                        duration = frame_count / fps
                    cap.release()
                except Exception as e:
                    import logging
                    logging.error(f"获取视频 {file} 时长失败: {e}")

                with st.expander(f"视频 {i + 1}: {file} ({duration:.1f}秒)", expanded=False):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**文件路径:** {file_path}")
                        if st.button(f"打开所在文件夹", key=f"open_{i}"):
                            open_folder(video_dir)

                    with col2:
                        st.markdown(f"**修改时间:** {mod_time}")
                        st.markdown(f"**文件大小:** {file_size:.2f} MB")
                        st.markdown(f"**时长:** {duration:.1f}秒")

                        col_ops1, col_ops2 = st.columns(2)
                        with col_ops1:
                            if st.button(f"分析", key=f"analyze_{i}") and st.session_state.analyzers_loaded:
                                scores = score_selected_video(file_path)
                                if scores and isinstance(scores, dict):
                                    st.session_state.video_scores = scores
                                    st.session_state.current_analysis = {
                                        "scores": scores,
                                        "video_path": file_path
                                    }
                                    st.rerun()

                        with col_ops2:
                            if st.button(f"删除", key=f"delete_{i}", type="secondary"):
                                try:
                                    os.remove(file_path)
                                    st.success(f"已删除: {file}")
                                    import logging
                                    logging.info(f"删除视频: {file_path}")
                                    st.experimental_rerun()
                                except Exception as e:
                                    st.error(f"删除失败: {str(e)}")
                                    import logging
                                    logging.error(f"删除视频 {file_path} 失败: {e}")