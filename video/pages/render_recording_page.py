import streamlit as st
import time
import cv2
import os
import shutil
from datetime import datetime
# 导入自定义模块，根据项目结构调整导入路径
from video.recording_controls import start_recording, stop_recording
from video.video_analysis import score_selected_video
from video.utils import open_folder
from video.recorder import frame_queue, result_queue


def render_recording_page():
    st.markdown("""
    <h2 class='sub-header'>视频录制</h2>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("摄像头预览")
            video_placeholder = st.empty()
            timer_placeholder = st.empty()
            status_placeholder = st.empty()

            # 录制状态指示
            if st.session_state.recording:
                st.markdown("""
                <p>
                    <span class="status-indicator recording-blink" style="background-color: #E74C3C;"></span>
                    <strong>正在录制中...</strong>
                </p>
                """, unsafe_allow_html=True)

            # 控制按钮
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("开始录制", disabled=st.session_state.recording):
                    success, msg = start_recording()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

            with col_btn2:
                if st.button("停止录制", disabled=not st.session_state.recording):
                    success, msg = stop_recording()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

            with col_btn3:
                if st.button("摄像头测试"):
                    success, msg = st.session_state.video_recorder.initialize_camera()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        with col2:
            st.subheader("实时分析结果")
            result_placeholder = st.empty()
            stats_placeholder = st.empty()
            feedback_placeholder = st.empty()

    # 实时预览
    if st.session_state.recording:
        recorder = st.session_state.video_recorder
        refresh_interval = 0.2

        while st.session_state.recording:
            current_time = time.time()
            if current_time - st.session_state.last_refresh_time > refresh_interval:
                success, frame = recorder.record_frame()
                if success and frame is not None:
                    if not frame_queue.full():
                        frame_queue.put(frame)

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    video_placeholder.image(
                        frame_rgb,
                        channels="RGB",
                        use_container_width=True,
                        caption=f"实时预览 - 已录制: {recorder.frame_count}帧"
                    )

                    elapsed = current_time - st.session_state.recording_start_time
                    timer_placeholder.markdown(
                        f"**录制时间: {int(elapsed // 60):02d}:{int(elapsed % 60):02d}**"
                    )

                    fps = recorder.frame_count / elapsed if elapsed > 0 else 0
                    stats_placeholder.markdown(f"""
                    - 帧率: {fps:.1f}fps
                    - 已录制帧数: {recorder.frame_count}
                    """)

                # 处理分析结果
                if st.session_state.analyzers_loaded:
                    recent_results = []
                    while not result_queue.empty():
                        result = result_queue.get()
                        st.session_state.analysis_results.append(result)
                        recent_results.append(result)

                    if recent_results:
                        latest = recent_results[-1]

                        body_data = latest.get('body', {})
                        pose_data = body_data.get('pose', {})
                        arms_data = body_data.get('arms', {})
                        posture_data = body_data.get('posture', {})
                        facial_data = body_data.get('facial', {})

                        micro_data = latest.get('micro', {})

                        body_score = body_data.get('得分', 0)
                        micro_score = micro_data.get('得分', 0)

                        def get_status_class(score):
                            if score >= 80:
                                return "good"
                            elif score >= 60:
                                return "warning"
                            else:
                                return "bad"

                        result_html = f"""
                        <div class="analysis-item {get_status_class(body_score)}">
                            <strong>肢体语言:</strong> {body_data.get('状态', 'N/A')} 
                            (得分: {body_score})
                        </div>
                        <div class="analysis-item {get_status_class(micro_score)}">
                            <strong>微表情:</strong> {micro_data.get('dominant_emotion', 'N/A')}
                            (得分: {micro_score})
                        </div>

                        <div class="info-box">
                            <h4>详细分析</h4>
                            <div class="analysis-item">
                                <strong>姿态:</strong> {pose_data.get('shoulder_state', 'N/A')}
                            </div>
                            <div class="analysis-item">
                                <strong>坐姿:</strong> {posture_data.get('posture_state', 'N/A')}
                            </div>
                            <div class="analysis-item">
                                <strong>眨眼频率:</strong> {facial_data.get('blinks_per_minute', 'N/A'):.1f} 次/分钟
                                ({facial_data.get('blink_status', 'N/A')})
                            </div>
                            <div class="analysis-item">
                                <strong>手臂状态:</strong> {arms_data.get('arm_suggestion', 'N/A')}
                            </div>
                            <div class="analysis-item">
                                <strong>微表情置信度:</strong> {micro_data.get('confidence', 0):.2f}
                            </div>
                        </div>
                        """
                        result_placeholder.markdown(result_html, unsafe_allow_html=True)

                        feedback_html = "<div class='feedback-box'>"

                        posture_score = posture_data.get('posture_score', 0)
                        if posture_score < 60:
                            feedback_html += """
                            <div class="alert alert-danger" role="alert">
                                <strong>坐姿建议:</strong> 您的坐姿需要调整，身体过于前倾或后靠会显得不专业
                            </div>
                            """
                        elif posture_score < 80:
                            feedback_html += """
                            <div class="alert alert-warning" role="alert">
                                <strong>坐姿建议:</strong> 坐姿基本良好，但可以进一步挺直背部，展现更好的精神面貌
                            </div>
                            """
                        else:
                            feedback_html += """
                            <div class="alert alert-success" role="alert">
                                <strong>坐姿建议:</strong> 坐姿非常好，保持挺直的背部和放松的肩膀
                            </div>
                            """

                        emotion = micro_data.get('dominant_emotion', '')
                        confidence = micro_data.get('confidence', 0)
                        if confidence > 0.7:
                            if emotion in ['happy', 'positive']:
                                feedback_html += """
                                <div class="alert alert-success" role="alert">
                                    <strong>表情建议:</strong> 保持微笑，展现积极态度
                                </div>
                                """
                            elif emotion in ['nervous', 'anxious']:
                                feedback_html += """
                                <div class="alert alert-warning" role="alert">
                                    <strong>表情建议:</strong> 看起来有些紧张，可以尝试深呼吸放松面部肌肉
                                </div>
                                """
                            elif emotion in ['neutral']:
                                feedback_html += """
                                <div class="alert alert-info" role="alert">
                                    <strong>表情建议:</strong> 表情略显平淡，可以适当增加一些自然的表情变化
                                </div>
                                """

                        blink_rate = facial_data.get('blinks_per_minute', 0)
                        if blink_rate > 30:
                            feedback_html += """
                            <div class="alert alert-warning" role="alert">
                                <strong>眨眼建议:</strong> 眨眼频率偏高，可能是紧张的表现，尝试保持自然眨眼
                            </div>
                            """
                        elif blink_rate < 10:
                            feedback_html += """
                            <div class="alert alert-warning" role="alert">
                                <strong>眨眼建议:</strong> 眨眼频率偏低，可能会让对方感到不自然
                            </div>
                            """

                        feedback_html += "</div>"
                        feedback_placeholder.markdown(feedback_html, unsafe_allow_html=True)

                st.session_state.last_refresh_time = current_time

            time.sleep(0.01)

    else:
        video_placeholder.markdown("""
        <div style="background-color: #f8f9fa; padding: 3rem 0; text-align: center; border-radius: 5px;">
            <p style="font-size: 1.2rem;">点击"开始录制"按钮启动摄像头</p>
            <p style="color: #666;">录制过程中请保持自然姿态，确保光线充足</p>
        </div>
        """, unsafe_allow_html=True)

    # 录制完成操作
    if st.session_state.last_video and not st.session_state.recording:
        with st.container():
            st.markdown("""
            <h3 class='sub-header'>录制完成</h3>
            """, unsafe_allow_html=True)

            if st.session_state.recorded_frames > 0:
                duration = st.session_state.recorded_frames / st.session_state.video_recorder.fps
                st.info(
                    f"录制统计: {st.session_state.recorded_frames}帧, 时长: {duration:.1f}秒, 帧描述: {len(st.session_state.frame_descriptions)}条")

                # 显示视频文件夹打开按钮
                video_dir = os.path.dirname(st.session_state.last_video)
                if st.button("打开视频所在文件夹"):
                    open_folder(video_dir)

            col_save, col_score = st.columns(2)
            with col_save:
                # 生成默认保存路径到video/video/目录
                save_dir = "video\\video"
                os.makedirs(save_dir, exist_ok=True)  # 确保目录存在

                # 初始化session_state存储保存路径，避免刷新重置
                if 'save_path' not in st.session_state:
                    # 生成唯一默认文件名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    default_filename = f"record_{timestamp}.mp4"
                    st.session_state.save_path = os.path.join(save_dir, default_filename)

                # 显示保存路径输入框（值与session_state绑定，保持用户输入）
                save_path = st.text_input("保存路径", st.session_state.save_path)
                # 实时更新session_state中的保存路径（关键：避免刷新后丢失修改）
                st.session_state.save_path = save_path

                col_save1, col_save2 = st.columns(2)
                with col_save1:
                    if st.button("确认保存"):
                        try:
                            # 原视频路径（待删除）
                            original_video = st.session_state.last_video
                            if not os.path.exists(original_video):
                                st.error(f"原视频文件不存在: {original_video}")
                                raise FileNotFoundError(f"原视频不存在: {original_video}")

                            # 确保目标目录存在
                            target_dir = os.path.dirname(save_path)
                            os.makedirs(target_dir, exist_ok=True)

                            # 复制文件到目标路径
                            shutil.copy2(original_video, save_path)

                            # 保存后删除原视频（核心需求）
                            os.remove(original_video)

                            # 更新session_state中的视频路径为新的保存路径
                            st.session_state.last_video = save_path

                            st.success(f"视频已保存至: {save_path}")
                            import logging
                            logging.info(f"视频保存成功，原视频已删除: {save_path}")
                        except Exception as e:
                            st.error(f"保存失败: {str(e)}")
                            import logging
                            logging.error(f"保存视频失败: {e}")

                with col_save2:
                    if st.button("取消保存"):
                        try:
                            # 删除原始临时文件
                            if os.path.exists(st.session_state.last_video):
                                os.remove(st.session_state.last_video)

                            # 清空session state
                            st.session_state.last_video = None
                            st.session_state.recorded_frames = 0
                            st.session_state.save_path = None  # 重置保存路径
                            if hasattr(st.session_state, 'frame_descriptions'):
                                st.session_state.frame_descriptions = []

                            import logging
                            logging.info(f"取消保存并删除视频")
                        except Exception as e:
                            st.error(f"删除失败: {str(e)}")
                            import logging
                            logging.error(f"删除视频失败: {e}")

            with col_score:
                if st.button("分析此视频") and not st.session_state.analyzing:
                    st.session_state.analyzing = True
                    try:
                        # 确保使用最新的视频路径
                        video_path = st.session_state.last_video
                        if not os.path.exists(video_path):
                            st.error(f"视频文件不存在: {video_path}")
                        else:
                            scores = score_selected_video(video_path)
                            if scores and isinstance(scores, dict):
                                st.session_state.video_scores = scores
                                st.session_state.current_analysis = {
                                    "scores": scores,
                                    "video_path": video_path
                                }
                    finally:
                        st.session_state.analyzing = False

    # 显示评分结果
    if 'video_scores' in st.session_state and st.session_state.video_scores:
        from video.analysis_display import show_detailed_analysis
        scores = st.session_state.video_scores
        if not isinstance(scores, dict):
            st.error("分析结果格式异常，无法显示")
            import logging
            logging.error("分析结果格式异常，清除无效数据")
            st.session_state.video_scores = None
        else:
            show_detailed_analysis(scores, st.session_state.current_analysis["video_path"])