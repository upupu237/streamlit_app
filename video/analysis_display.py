import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from video.utils import export_analysis

def show_detailed_analysis(scores, video_path):
    if not scores or not isinstance(scores, dict):
        st.error("分析结果数据异常")
        return

    st.markdown("""
    <h3 class='sub-header'>详细分析结果</h3>
    """, unsafe_allow_html=True)

    # 关键指标卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="score-card" style="background-color: #3498DB; color: white;">
            <div style="font-size: 0.9rem;">综合评分</div>
            <div style="font-size: 2rem; font-weight: bold;">{scores.get('综合面试评分', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="score-card" style="background-color: #2ECC71; color: white;">
            <div style="font-size: 0.9rem;">原有模型评分</div>
            <div style="font-size: 2rem; font-weight: bold;">{scores.get('原有模型综合评分', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="score-card" style="background-color: #F39C12; color: white;">
            <div style="font-size: 0.9rem;">讯飞星火模型评分</div>
            <div style="font-size: 2rem; font-weight: bold;">{scores.get('讯飞星火模型评分', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

    # 雷达图对比
    original_labels = [
        "坐姿端正度", "微表情自然度", "肩膀展开度",
        "眨眼频率", "手臂动作协调性", "表情多样性"
    ]
    spark_labels = [f"星火_{label}" for label in original_labels]

    original_values = [scores.get(label, 0) for label in original_labels]
    spark_values = [scores.get(label, 0) for label in spark_labels]

    if original_labels and original_values and spark_values:
        fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'polar'}, {'type': 'polar'}]],
                            subplot_titles=('原有模型评分', '讯飞星火模型评分'))

        fig.add_trace(go.Scatterpolar(
            r=original_values,
            theta=original_labels,
            fill='toself',
            line=dict(color='#3498DB'),
            name='原有模型'
        ), 1, 1)

        fig.add_trace(go.Scatterpolar(
            r=spark_values,
            theta=original_labels,
            fill='toself',
            line=dict(color='#F39C12'),
            name='讯飞星火模型'
        ), 1, 2)

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            polar2=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    # 详细评分对比
    st.subheader("详细评分对比")
    with st.expander("查看详情", expanded=True):
        comparison_data = {
            "评分维度": original_labels,
            "原有模型评分": original_values,
            "讯飞星火模型评分": spark_values,
            "平均评分": [(o + s) / 2 for o, s in zip(original_values, spark_values)]
        }
        st.table(comparison_data)

        # 评分建议
        st.subheader("评分建议")
        for i, label in enumerate(original_labels):
            original_score = original_values[i]
            spark_score = spark_values[i]
            avg_score = (original_score + spark_score) / 2

            st.markdown(f"**{label}**: 平均 {avg_score:.1f} 分")

            if avg_score < 60:
                st.markdown("""
                <div class="alert alert-danger" role="alert">
                    建议：需要重点改进此维度表现
                </div>
                """, unsafe_allow_html=True)
            elif avg_score < 80:
                st.markdown("""
                <div class="alert alert-warning" role="alert">
                    建议：有提升空间，可以进一步优化
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert alert-success" role="alert">
                    很好：此维度表现优秀，保持即可
                </div>
                """, unsafe_allow_html=True)

    # 导出报告
    export_analysis(scores, video_path)