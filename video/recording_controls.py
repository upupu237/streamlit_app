import logging
import os
import shutil
import streamlit as st
import time

def start_recording():
    if st.session_state.recording:
        return False, "已在录制中"

    os.makedirs("video", exist_ok=True)
    os.makedirs("analysis_reports", exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = f"video/video/record_{timestamp}.mp4"

    success, msg = st.session_state.video_recorder.initialize_camera()
    if not success:
        logging.error(f"摄像头初始化失败: {msg}")
        return False, msg

    success, msg = st.session_state.video_recorder.start_recording(video_path)
    if not success:
        logging.error(f"录制启动失败: {msg}")
        return False, msg

    st.session_state.video_path = video_path
    st.session_state.recording = True
    st.session_state.analysis_results = []
    st.session_state.video_scores = None
    st.session_state.recording_start_time = time.time()
    st.session_state.recorded_frames = 0
    st.session_state.last_refresh_time = time.time()
    st.session_state.frame_descriptions = []

    # 修正：使用相对导入
    from video.recorder import recording_flag
    if recording_flag.empty():
        recording_flag.put(True)

    logging.info(f"开始录制: {video_path}")
    return True, f"开始录制: {os.path.basename(video_path)}"


def stop_recording():
    if not st.session_state.recording:
        return False, "未在录制中"

    success, frame_count = st.session_state.video_recorder.stop_recording()

    st.session_state.recording = False
    st.session_state.recorded_frames = frame_count

    # 修正：使用相对导入
    from video.recorder import recording_flag
    while not recording_flag.empty():
        recording_flag.get()

    if success and frame_count > 0:
        st.session_state.last_video = st.session_state.video_path
        duration = frame_count / st.session_state.video_recorder.fps
        logging.info(f"录制完成: {frame_count}帧, 时长: {duration:.1f}秒, 路径: {st.session_state.video_path}")
        return True, f"录制完成: {frame_count}帧, 时长: {duration:.1f}秒"
    else:
        if os.path.exists(st.session_state.video_path):
            os.remove(st.session_state.video_path)
            logging.warning(f"录制失败，删除无效文件: {st.session_state.video_path}")
        return False, "录制失败，未获取到有效帧"