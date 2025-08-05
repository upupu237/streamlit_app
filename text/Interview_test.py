#!/usr/bin/env python
# -*- coding:utf-8 -*-

import streamlit as st
import json
import random
import matplotlib.pyplot as plt
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from text.ResumeEvaluator import ResumeEvaluator


# 面试系统核心功能
class InterviewSystem:
    def __init__(self):
        self.job_data = self.load_job_data()
        self.evaluator = ResumeEvaluator()  # 简历评估器

    def load_job_data(self):
        job_data = {}
        for job in ['产品经理', '数据分析', '运维','后端开发','软件测试']:
            try:
                with open(f'data/{job}.json', 'r', encoding='utf-8') as file:
                    job_data[job] = json.load(file)
            except FileNotFoundError:
                st.warning(f"未找到 {job}.json 文件，该岗位数据无法加载")
                job_data[job] = []
        return job_data

    def select_questions(self, job, num_questions=5):
        if job not in self.job_data or len(self.job_data[job]) == 0:
            return []
        return random.sample(self.job_data[job], min(num_questions, len(self.job_data[job])))

    def extract_keywords(self, texts):
        vectorizer = TfidfVectorizer()
        try:
            X = vectorizer.fit_transform(texts)
        except ValueError:
            return [set()] * len(texts)
        feature_names = vectorizer.get_feature_names_out()
        keywords_list = []
        for doc_index in range(X.shape[0]):
            feature_index = X[doc_index, :].nonzero()[1]
            tfidf_scores = zip(feature_index, [X[doc_index, x] for x in feature_index])
            sorted_tfidf_scores = sorted(tfidf_scores, key=lambda x: x[1], reverse=True)
            top_keywords = {feature_names[i] for i, _ in sorted_tfidf_scores[:5]}
            keywords_list.append(top_keywords)
        return keywords_list

    def judge_answer(self, user_answer, correct_answer):
        texts = [user_answer, correct_answer]
        user_keywords, correct_keywords = self.extract_keywords(texts)
        if not correct_keywords:
            return True
        overlap = len(user_keywords.intersection(correct_keywords))
        return overlap / len(correct_keywords) >= 0.5

    def evaluate_user(self, questions, user_answers):
        correct_count = 0
        wrong_questions = []
        for i, (question, user_answer) in enumerate(zip(questions, user_answers)):
            correct_answer = question['答案']
            if self.judge_answer(user_answer, correct_answer):
                correct_count += 1
            else:
                wrong_questions.append(question['问题'])
        total = len(questions)
        accuracy = correct_count / total if total > 0 else 0
        if accuracy >= 0.8:
            level = '优秀'
            match = '高度匹配'
        elif accuracy >= 0.6:
            level = '良好'
            match = '匹配'
        elif accuracy >= 0.4:
            level = '中等'
            match = '部分匹配'
        else:
            level = '较差'
            match = '不匹配'
        return accuracy, level, match, wrong_questions

    def generate_radar_chart(self, accuracy, level):
        labels = ['专业知识水平', '技能匹配度']
        stats = [accuracy, accuracy]

        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        stats = np.concatenate((stats, [stats[0]]))
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(8, 6), subplot_kw=dict(polar=True))

        colors = ['#FF6347', '#40E0D0']
        for i in range(len(labels)):
            ax.plot([angles[i], angles[i + 1]], [0, stats[i]], color=colors[i], label=labels[i], linewidth=2)
            ax.text(angles[i], stats[i] + 0.02, f'{stats[i]:.2f}', color=colors[i], ha='center', va='bottom')

        ax.set_thetagrids(np.degrees(angles[:-1]), labels)
        ax.set_title(f'能力雷达图（{level}）', y=1.1, fontsize=14)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

        return fig


def start_interview():
    st.title("开始笔试")
    user = st.session_state.current_user

    # 检查是否上传了简历
    resume = st.session_state.user_manager.get_resume(user)
    if not resume:
        st.warning("请先完成简历评分再开始笔试")
        st.stop()

    # 选择岗位
    st.subheader("选择笔试岗位")
    job_options = list(st.session_state.interview_system.job_data.keys())
    job = st.selectbox("请选择岗位", job_options)

    # 选择题目数量
    num_questions = st.slider("选择题目数量", 5, 10, 7)

    if st.button("开始笔试"):
        st.session_state.current_job = job
        st.session_state.current_questions = st.session_state.interview_system.select_questions(job, num_questions)
        st.session_state.user_answers = ["" for _ in range(num_questions)]
        st.success(f"已为您生成 {len(st.session_state.current_questions)} 道 {job} 岗位的笔试题")
        st.info("请依次回答以下问题，完成后点击提交答案")

    # 显示问题和答案输入框
    if st.session_state.current_questions:
        st.subheader(f"{st.session_state.current_job} 岗位笔试")

        for i, question in enumerate(st.session_state.current_questions):
            st.markdown(f"### 问题 {i + 1}")
            st.markdown(question["问题"])

            # 保存用户答案
            answer = st.text_area(f"您的回答 ({i + 1}/{len(st.session_state.current_questions)})",
                                  value=st.session_state.user_answers[i],
                                  height=200)
            st.session_state.user_answers[i] = answer

        # 提交答案
        if st.button("提交答案"):
            if any(not answer.strip() for answer in st.session_state.user_answers):
                st.error("请回答所有问题")
            else:
                # 评估用户回答
                accuracy, level, match, wrong_questions = st.session_state.interview_system.evaluate_user(
                    st.session_state.current_questions, st.session_state.user_answers
                )

                # 保存面试历史
                st.session_state.user_manager.add_interview_history(
                    st.session_state.current_user,
                    st.session_state.current_job,
                    accuracy,
                    level,
                    match
                )

                # 显示结果
                st.success("笔试完成，以下是您的评估结果：")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("正确率", f"{accuracy * 100:.2f}%")
                with col2:
                    st.metric("专业知识水平", level)
                with col3:
                    st.metric("技能匹配度", match)

                # 显示雷达图
                fig = st.session_state.interview_system.generate_radar_chart(accuracy, level)
                st.pyplot(fig)

                # 显示错误问题
                if wrong_questions:
                    st.subheader("需要改进的问题")
                    for i, q in enumerate(wrong_questions, 1):
                        st.markdown(f"{i}. {q}")

                # 改进建议
                st.subheader("改进建议")
                recommendation = get_recommendation(accuracy, job)
                if isinstance(recommendation, tuple):
                    status, message = recommendation
                    if status == "warning":
                        st.warning(message)
                    elif status == "info":
                        st.info(message)
                    elif status == "success":
                        st.success(message)
                else:
                    st.info(recommendation)

                # 重置面试状态
                st.session_state.current_questions = []
                st.session_state.user_answers = []
                st.session_state.current_job = None


# 推荐资源映射表
RESOURCE_MAPPING = {
    "产品经理": {
        "初级": "推荐资源：\n- 《产品经理面试攻略》\n- 《人人都是产品经理》\n- 《结网 @改变世界的互联网产品经理》\n- 《About Face 3 交互设计精髓》",
        "中级": "推荐资源：\n- 网站:PMCAFF \n- 网站：三节课 \n- 课程：Product School \n- 实战：51CTO 学堂 - 产品经理核心 20 问项目实战训练"
    },
    "后端开发": {
        "初级": "推荐资源：\n- 《Effective Java》\n- 《Fluent Python》\n- 《SQL Performance Explained》",
        "中级": "推荐资源：\n- 视频:计算机科学速成课\n- 视频:操作系统 - 清华大学 \n- 课程:Java Backend Development \n- 课程:Meta Back-End Developer Professional Certificate"
    },
    "数据分析": {
        "初级": "推荐资源：\n-《利用 Python 进行数据分析》\n-《数据挖掘与分析 概念与算法》\n-《精益数据分析》",
        "中级": "推荐资源：\n- 网站:Coursera \n- 网站:Kaggle \n- 网站:阿里天池 \n- 论坛:Reddit 的 Data Science \n- 社区:知乎专栏：数据分析侠"
    },
    "软件测试": {
        "初级": "推荐资源：\n- 《Selenium 自动化测试》\n-《移动 app 测试实战》\n-《Web 接口开发与自动化测试》",
        "中级": "推荐资源：\n- 课程:Test Automation University \n- 课程:黑马程序员软件测试教程 \n- 网站:Postman Learning Center \n- 网站:JSONPlaceholder"
    },
    "其他": {
        "初级": "推荐资源：\n- 《鸟哥的 Linux 私房菜：基础学习篇》\n-《Ansible 自动化运维：技术与最佳实践》\n-《DevOps 实践指南》",
        "中级": "推荐资源：\n- 实验平台:Linux 命令行练习平台 \n- 实验平台: Katacoda \n- 实验平台: 阿里云开发者实验室 \n- 社区:DevOps Weekly"
    }
}


def get_recommendation(accuracy, job):
    """根据准确率和岗位获取推荐信息"""
    if accuracy < 0.6:
        level = "初级"
        status = "warning"
        message = "建议系统学习岗位核心知识，优先补足薄弱环节"
    elif accuracy < 0.8:
        level = "中级"
        status = "info"
        message = "继续深化专业知识，多参与实际项目积累经验"
    else:
        return ("success", "您的表现非常出色，继续保持！")

    # 获取岗位推荐，不存在则使用默认
    job_recommendations = RESOURCE_MAPPING.get(job, RESOURCE_MAPPING["其他"])
    recommendation = job_recommendations.get(level, job_recommendations["初级"])

    return (status, f"{message}\n\n{recommendation}")