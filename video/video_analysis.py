import os
import json
import logging
import streamlit as st
from datetime import datetime
from video.analyzers import scorer
def score_selected_video(video_path):
    if st.session_state.analyzing_video:
        st.warning("⌛ 正在分析中，请稍候...")
        return None

    if not os.path.exists(video_path):
        st.error("视频文件不存在")
        logging.error(f"视频文件不存在: {video_path}")
        return None
    if os.path.getsize(video_path) < 1024:
        st.error("视频文件无效或损坏（体积过小）")
        logging.error(f"无效视频文件: {video_path} (大小: {os.path.getsize(video_path)}字节)")
        return None

    st.session_state.analyzing_video = True
    try:
        from video.analyzers import scorer
        with st.spinner("正在分析视频，请稍候..."):
            logging.info(f"开始分析视频: {video_path}")
            scores = scorer.score_video(video_path)

            if scores is None:
                st.error("分析失败，未生成有效评分")
                logging.error(f"分析 {video_path} 未返回结果")
                return None

            if not isinstance(scores, dict):
                st.error("分析结果格式异常，不是有效的字典")
                logging.error(f"分析 {video_path} 结果格式错误: {type(scores)}")
                return None

            required_keys = ["综合面试评分", "坐姿端正度", "微表情自然度", "原有模型综合评分", "讯飞星火模型评分"]
            missing_keys = [k for k in required_keys if k not in scores]
            if missing_keys:
                st.error(f"分析结果缺少必要项: {', '.join(missing_keys)}")
                logging.error(f"分析 {video_path} 缺少关键项: {missing_keys}")
                return None

            desc_count = scores.get("帧描述数量", 0)
            st.info(f"视频分析完成，共提取 {desc_count} 条帧描述")
            if desc_count == 0:
                st.warning("未提取到有效帧描述，可能影响星火模型评分准确性")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"analysis_reports/report_{timestamp}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "video_path": video_path,
                    "analysis_time": timestamp,
                    "scores": scores,
                    "frame_descriptions": st.session_state.frame_descriptions
                }, f, ensure_ascii=False, indent=2)
            logging.info(f"分析报告已保存: {report_path}")

            st.session_state.saved_analyses[report_path] = {
                "video": os.path.basename(video_path),
                "time": timestamp,
                "scores": scores,
                "frame_descriptions": st.session_state.frame_descriptions
            }

            return scores
    except Exception as e:
        st.error(f"分析出错: {str(e)}")
        logging.error(f"分析 {video_path} 出错: {e}", exc_info=True)
        return None
    finally:
        st.session_state.analyzing_video = False