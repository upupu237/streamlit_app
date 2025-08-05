import streamlit as st
import os
import json
from video.utils import open_folder
from video.analysis_display import show_detailed_analysis


def render_reports_page():
    st.markdown("""
    <h2 class='sub-header'>分析报告管理</h2>
    """, unsafe_allow_html=True)

    if st.session_state.saved_analyses:
        st.write(f"共 {len(st.session_state.saved_analyses)} 份报告")

        sorted_reports = sorted(
            st.session_state.saved_analyses.items(),
            key=lambda x: x[1]["time"],
            reverse=True
        )

        for report_path, report_data in sorted_reports:
            if not isinstance(report_data, dict) or 'scores' not in report_data:
                with st.expander(f"无效报告", expanded=False):
                    st.error("报告数据格式错误，无法显示")
                continue

            scores = report_data['scores']
            if not isinstance(scores, dict) or '综合面试评分' not in scores:
                with st.expander(f"无效报告: {report_data.get('video', '未知视频')}", expanded=False):
                    st.error("评分数据格式错误")
                continue

            with st.expander(
                    f"报告: {os.path.basename(report_data['video'])} "
                    f"({report_data['time']}) | 综合评分: {scores['综合面试评分']}",
                    expanded=False
            ):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown(f"**分析时间:** {report_data['time']}")
                    st.markdown(f"**关联视频:** {os.path.basename(report_data['video'])}")
                    st.markdown(f"**原始模型评分:** {scores.get('原有模型综合评分', 'N/A')}")
                    st.markdown(f"**星火模型评分:** {scores.get('讯飞星火模型评分', 'N/A')}")
                    st.markdown(f"**帧描述数量:** {len(report_data.get('frame_descriptions', []))}")

                    if st.button(f"查看详情", key=f"view_{report_path}"):
                        st.session_state.video_scores = scores
                        st.session_state.current_analysis = {
                            "scores": scores,
                            "video_path": report_data['video']
                        }
                        st.session_state.frame_descriptions = report_data.get('frame_descriptions', [])
                        st.session_state.show_analysis_detail = True

                    report_dir = os.path.dirname(report_path)
                    if st.button(f"打开报告文件夹", key=f"open_report_{report_path}"):
                        open_folder(report_dir)

                    if st.button(f"删除报告", key=f"del_report_{report_path}", type="secondary"):
                        try:
                            if os.path.exists(report_path):
                                os.remove(report_path)
                            del st.session_state.saved_analyses[report_path]
                            st.success("报告已删除")
                            import logging
                            logging.info(f"删除报告: {report_path}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除失败: {str(e)}")
                            import logging
                            logging.error(f"删除报告 {report_path} 失败: {e}")

                with col2:
                    original_labels = [
                        "坐姿端正度", "微表情自然度", "肩膀展开度"
                    ]
                    spark_labels = [f"星火_{label}" for label in original_labels]

                    original_values = [scores.get(label, 0) for label in original_labels]
                    spark_values = [scores.get(label, 0) for label in spark_labels]

                    st.table({
                        "评分维度": original_labels,
                        "原有模型评分": original_values,
                        "星火模型评分": spark_values,
                        "平均评分": [(o + s) / 2 for o, s in zip(original_values, spark_values)]
                    })

        if st.session_state.show_analysis_detail and 'current_analysis' in st.session_state:
            show_detailed_analysis(
                st.session_state.current_analysis["scores"],
                st.session_state.current_analysis["video_path"]
            )

            if st.button("关闭详情"):
                st.session_state.show_analysis_detail = False
                st.session_state.video_scores = None
                st.rerun()
    else:
        st.info("暂无保存的分析报告，请先分析视频")