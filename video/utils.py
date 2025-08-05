import os
import sys
import shutil
import json
import streamlit as st
import cv2
import logging
from datetime import datetime

def get_latest_video():
    video_dir = "video"
    if not os.path.exists(video_dir):
        return None

    mp4_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
    if not mp4_files:
        return None

    mp4_files.sort(key=lambda f: os.path.getmtime(os.path.join(video_dir, f)), reverse=True)
    return os.path.join(video_dir, mp4_files[0])


def delete_all_videos():
    video_dir = "video"
    if os.path.exists(video_dir):
        file_count = 0
        for file in os.listdir(video_dir):
            file_path = os.path.join(video_dir, file)
            try:
                if os.path.isfile(file_path) and file.endswith(".mp4"):
                    os.unlink(file_path)
                    file_count += 1
            except Exception as e:
                st.error(f"删除文件出错: {e}")
                logging.error(f"删除 {file_path} 失败: {e}")
        st.success(f"所有视频已删除（共 {file_count} 个）")
        logging.info(f"删除所有视频，共 {file_count} 个文件")
    else:
        st.info("没有视频文件可删除")


def export_analysis(scores, video_path):
    if not scores or not isinstance(scores, dict):
        st.warning("没有可导出的有效分析结果")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"面试分析报告_{timestamp}.json"
    data = {
        "视频文件": os.path.basename(video_path),
        "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "评分结果": scores,
        "帧描述数量": len(st.session_state.frame_descriptions),
        "帧描述样本": st.session_state.frame_descriptions[:5],
        "评分说明": {
            "坐姿端正度": "评估坐姿是否端正，是否有弯腰驼背现象",
            "微表情自然度": "评估面部表情的自然程度和适宜性",
            "肩膀展开度": "评估肩膀姿态，是否自然展开",
            "眨眼频率": "评估眨眼频率是否在正常范围内",
            "手臂动作协调性": "评估手臂动作的流畅性和协调性",
            "表情多样性": "评估表情变化的丰富程度",
            "原有模型综合评分": "原始模型对各项指标的综合评分",
            "讯飞星火模型评分": "讯飞星火模型对各项指标的综合评分",
            "综合面试评分": "综合原始模型和讯飞星火模型的最终评分"
        }
    }

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button(
        label="下载分析报告",
        data=json_str,
        file_name=filename,
        mime="application/json",
        key="download_report"
    )


def open_folder(path):
    try:
        if not os.path.exists(path):
            st.error(f"文件夹不存在: {path}")
            logging.error(f"打开不存在的文件夹: {path}")
            return

        if os.name == 'nt':
            os.startfile(path)
        elif os.name == 'posix':
            os.system(f'open "{path}"' if sys.platform == 'darwin' else f'xdg-open "{path}"')
        st.success(f"已打开文件夹: {path}")
        logging.info(f"打开文件夹: {path}")
    except Exception as e:
        st.error(f"打开文件夹失败: {str(e)}")
        logging.error(f"打开文件夹 {path} 失败: {e}")


def load_saved_reports():
    reports_dir = "analysis_reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir, exist_ok=True)
        return

    for file in os.listdir(reports_dir):
        if file.endswith('.json'):
            file_path = os.path.join(reports_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'scores' in data and isinstance(data['scores'], dict):
                    st.session_state.saved_analyses[file_path] = {
                        "video": data.get("video_path", "未知视频"),
                        "time": data.get("analysis_time", "未知时间"),
                        "scores": data["scores"],
                        "frame_descriptions": data.get("frame_descriptions", [])
                    }
            except Exception as e:
                logging.error(f"加载报告 {file} 失败: {e}")