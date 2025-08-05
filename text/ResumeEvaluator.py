#!/usr/bin/env python
# -*- coding:utf-8 -*-
import matplotlib.pyplot as plt
import numpy as np

# 简历评估类
class ResumeEvaluator:
    def __init__(self):
        # 定义各岗位的关键词要求
        self.job_keywords = {
            '产品经理': [
                "用户需求", "市场分析", "产品规划", "原型设计", "项目管理",
                "用户体验", "竞品分析", "产品生命周期", "需求文档", "数据分析",
                "敏捷开发", "产品路线图", "用户调研", "商业化", "产品优化"
            ],
            '数据分析': [
                "数据挖掘", "统计分析", "SQL", "Python", "数据可视化",
                "机器学习", "数据清洗", "数据建模", "Tableau", "Excel",
                "预测模型", "AB测试", "数据仓库", "BI工具", "数据驱动"
            ],
            '运维': [
                "Linux", "网络管理", "服务器配置", "Shell脚本", "监控系统",
                "容器化", "Docker", "Kubernetes", "CI/CD", "自动化运维",
                "故障排除", "安全防护", "负载均衡", "高可用", "性能优化"
            ],
            '后端开发': [
                "Java", "Python", "数据库设计", "RESTful API", "Spring框架",
                "Django框架", "Flask框架", "数据库优化", "微服务架构", "分布式系统"
            ],
            '软件测试': [
                "测试用例设计", "自动化测试", "功能测试", "性能测试", "缺陷管理",
                "测试框架", "Selenium", "JUnit", "Postman", "TestNG"
            ]

        }

        # 简历各部分权重
        self.section_weights = {
            "contact": 0.1,
            "education": 0.2,
            "experience": 0.3,
            "projects": 0.2,
            "skills": 0.2
        }

    def evaluate_resume(self, resume_data, job):
        """评估简历并生成报告"""
        evaluation = {
            "job": job,
            "scores": {},
            "missing_keywords": [],
            "recommendations": []
        }

        # 计算完整性分数
        completeness_score = self.calculate_completeness(resume_data)
        evaluation["scores"]["completeness"] = completeness_score

        # 关键词匹配度分析
        keyword_score, missing_keywords = self.analyze_keywords(resume_data, job)
        evaluation["scores"]["keyword_match"] = keyword_score
        evaluation["missing_keywords"] = missing_keywords

        # 技能相关性分析
        skill_score, skill_recommendations = self.analyze_skills(resume_data, job)
        evaluation["scores"]["skill_relevance"] = skill_score
        evaluation["recommendations"].extend(skill_recommendations)

        # 整体评分
        evaluation["scores"]["overall"] = (
                completeness_score * 0.3 +
                keyword_score * 0.4 +
                skill_score * 0.3
        )

        # 生成改进建议
        self.generate_recommendations(evaluation, resume_data)

        return evaluation

    def calculate_completeness(self, resume_data):
        """计算简历完整性分数"""
        completeness = 0
        total_weight = 0

        # 检查基本信息
        contact_score = 0
        if resume_data["name"] != "未识别":
            contact_score += 0.5
        if resume_data["contact"]["email"] != "未识别" or resume_data["contact"]["phone"] != "未识别":
            contact_score += 0.5
        completeness += contact_score * self.section_weights["contact"]

        # 检查教育经历
        edu_score = 0
        for edu in resume_data["education"]:
            edu_sub_score = 0
            if edu["school"] != "未识别":
                edu_sub_score += 0.5
            if edu["degree"] != "未识别":
                edu_sub_score += 0.5
            if edu.get("major") != "未识别":
                edu_sub_score += 0.2  # 新增专业信息检查
            edu_score += edu_sub_score
        if resume_data["education"]:
            completeness += min(edu_score / (len(resume_data["education"]) * 1.2), 1.0) * self.section_weights["education"]

        # 检查工作经验
        exp_score = 0
        for exp in resume_data["experience"]:
            exp_sub_score = 0
            if exp["company"] != "未识别":
                exp_sub_score += 0.3
            if exp["position"] != "未识别":
                exp_sub_score += 0.3
            if exp["description"] != "未识别":
                exp_sub_score += 0.4
            if exp.get("start_date") != "未识别" and exp.get("end_date") != "未识别":
                exp_sub_score += 0.1  # 新增工作时间检查
            exp_score += exp_sub_score
        if resume_data["experience"]:
            completeness += min(exp_score / (len(resume_data["experience"]) * 1.1), 1.0) * self.section_weights["experience"]

        # 检查项目经历
        project_score = 0
        for project in resume_data.get("projects", []):
            project_sub_score = 0
            if project["name"] != "未识别":
                project_sub_score += 0.4
            if project["description"] != "未识别":
                project_sub_score += 0.6
            if project.get("project_duration") != "未识别":
                project_sub_score += 0.1  # 新增项目时长检查
            project_score += project_sub_score
        if resume_data.get("projects"):
            completeness += min(project_score / (len(resume_data["projects"]) * 1.1), 1.0) * self.section_weights["projects"]

        # 检查技能部分
        skills = self.extract_skills(resume_data)
        if skills:
            completeness += self.section_weights["skills"]

        return min(completeness * 100, 100)  # 转换为百分比

    def analyze_keywords(self, resume_data, job):
        """分析关键词匹配度"""
        if job not in self.job_keywords:
            return 0, []

        # 提取简历文本
        resume_text = self.flatten_resume(resume_data)
        required_keywords = self.job_keywords[job]

        # 计算匹配的关键词
        matched_keywords = []
        for keyword in required_keywords:
            if keyword in resume_text:
                matched_keywords.append(keyword)

        # 优化：考虑关键词出现的频率
        keyword_frequency = {}
        for keyword in required_keywords:
            keyword_frequency[keyword] = resume_text.count(keyword)

        # 计算匹配分数，考虑频率权重
        total_frequency = sum(keyword_frequency.values())
        match_score = sum([keyword_frequency[keyword] for keyword in matched_keywords]) / total_frequency * 100 if total_frequency > 0 else 0

        # 找出缺失的关键词
        missing_keywords = [kw for kw in required_keywords if kw not in matched_keywords]

        return match_score, missing_keywords

    def extract_skills(self, resume_data):
        """从简历中提取技能"""
        skills = []

        # 从技能描述中提取
        skills.extend(resume_data.get("skills", []))

        # 从教育经历中提取
        for edu in resume_data["education"]:
            if "主修课程" in edu["degree"]:
                # 尝试提取课程中的技能
                courses = edu["degree"].split("主修课程:")[-1]
                skills.extend([c.strip() for c in courses.split(",") if c.strip()])

        # 从工作经历中提取
        for exp in resume_data["experience"]:
            # 尝试提取描述中的技能
            exp_text = exp["description"].lower()
            for skill in self.get_all_skills():
                if skill.lower() in exp_text:
                    skills.append(skill)

        # 从项目经历中提取
        for project in resume_data.get("projects", []):
            project_text = project["description"].lower()
            for skill in self.get_all_skills():
                if skill.lower() in project_text:
                    skills.append(skill)

        return list(set(skills))

    def get_all_skills(self):
        """获取所有岗位的技能列表"""
        all_skills = []
        for job_skills in self.job_keywords.values():
            all_skills.extend(job_skills)
        return list(set(all_skills))

    def analyze_skills(self, resume_data, job):
        """分析技能相关性"""
        if job not in self.job_keywords:
            return 0, []

        skills = self.extract_skills(resume_data)
        if not skills:
            return 0, ["简历中未发现明确的技能描述"]

        # 计算技能相关性
        required_skills = self.job_keywords[job]
        relevant_skills = [skill for skill in skills if skill in required_skills]

        # 计算相关性分数
        relevance_score = len(relevant_skills) / len(required_skills) * 100 if required_skills else 0

        # 生成改进建议
        recommendations = []
        if relevance_score < 70:
            missing_skills = [skill for skill in required_skills if skill not in skills]
            if missing_skills:
                recommendations.append(f"建议添加岗位相关技能: {', '.join(missing_skills[:3])}")
            if len(relevant_skills) < 3:
                recommendations.append("建议突出显示至少3项与岗位相关的关键技能")

        return relevance_score, recommendations

    def flatten_resume(self, resume_data):
        """将简历内容拼接成字符串"""
        text = f"{resume_data['name']} "
        text += f"{resume_data['contact']['email']} {resume_data['contact']['phone']} "

        for edu in resume_data["education"]:
            text += f"{edu['school']} {edu['degree']} {edu.get('major', '')} {edu['time']} "

        for exp in resume_data["experience"]:
            text += f"{exp['company']} {exp['position']} {exp.get('start_date', '')} {exp.get('end_date', '')} {exp['description']} "

        for project in resume_data.get("projects", []):
            text += f"{project['name']} {project.get('project_duration', '')} {project['role']} {project['description']} "

        # 添加技能描述
        text += " ".join(resume_data.get("skills", []))

        return text

    def generate_recommendations(self, evaluation, resume_data):
        """生成改进建议"""
        scores = evaluation["scores"]

        # 完整性建议
        if scores["completeness"] < 80:
            missing_parts = []
            if resume_data["name"] == "未识别":
                missing_parts.append("姓名")
            if resume_data["contact"]["email"] == "未识别" and resume_data["contact"]["phone"] == "未识别":
                missing_parts.append("联系方式")
            if not resume_data["education"] or all(edu["school"] == "未识别" for edu in resume_data["education"]):
                missing_parts.append("教育经历")
            if not resume_data["experience"] or all(exp["company"] == "未识别" for exp in resume_data["experience"]):
                missing_parts.append("工作经验")
            if not resume_data.get("projects") or all(
                    project["name"] == "未识别" for project in resume_data.get("projects", [])):
                missing_parts.append("项目经历")
            if resume_data["education"] and all(edu.get("major") == "未识别" for edu in resume_data["education"]):
                missing_parts.append("专业信息")
            if resume_data["experience"] and all(exp.get("start_date") == "未识别" for exp in resume_data["experience"]):
                missing_parts.append("工作开始时间")
            if resume_data["experience"] and all(exp.get("end_date") == "未识别" for exp in resume_data["experience"]):
                missing_parts.append("工作结束时间")
            if resume_data.get("projects") and all(project.get("project_duration") == "未识别" for project in resume_data.get("projects", [])):
                missing_parts.append("项目时长")

            if missing_parts:
                evaluation["recommendations"].append(
                    f"简历完整性不足，请补充: {', '.join(missing_parts)}"
                )

        # 关键词建议
        if evaluation["missing_keywords"]:
            evaluation["recommendations"].append(
                f"建议在简历中添加关键词: {', '.join(evaluation['missing_keywords'][:5])}"
            )

        # 整体建议
        if scores["overall"] < 60:
            evaluation["recommendations"].append("简历整体匹配度较低，建议根据岗位要求全面优化")
        elif scores["overall"] < 80:
            evaluation["recommendations"].append("简历匹配度良好，仍有优化空间")
        else:
            evaluation["recommendations"].append("简历匹配度很高，继续保持！")

    def visualize_evaluation(self, evaluation):
        """可视化评估结果"""
        # 创建雷达图
        categories = ['完整性', '关键词匹配', '技能相关', '整体评分']
        scores = [
            evaluation["scores"]["completeness"],
            evaluation["scores"]["keyword_match"],
            evaluation["scores"]["skill_relevance"],
            min(evaluation["scores"]["overall"], 100)  # 确保不超过100%
        ]

        # 雷达图数据准备
        num_vars = len(categories)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        scores += scores[:1]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(3, 2), subplot_kw=dict(polar=True))

        # 绘制雷达图
        ax.plot(angles, scores, color='#1f77b4', linewidth=2)
        ax.fill(angles, scores, color='#1f77b4', alpha=0.25)

        # 设置标签
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        # 修改标签字体大小为原来的一半
        ax.set_thetagrids(np.degrees(angles[:-1]), categories, fontsize=6 / 2)

        # 设置坐标轴
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        # 修改坐标轴刻度标签字体大小为原来的一半
        ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=6 / 2)

        # 设置标题
        plt.title(f"简历评估雷达图 - {evaluation['job']}岗位", size=6, y=1.1)

        return fig
def display_resume_evaluation(st, session_state):
    st.title("简历评价")
    user = session_state.current_user
    # 检查是否有简历
    resume = session_state.user_manager.get_resume(user)
    if not resume:
        st.warning("请先上传简历再进行评价")
        st.stop()
    # 获取解析后的简历数据
    user_data = session_state.user_manager.users.get(user, {})
    parsed_data = user_data.get("parsed_resume")
    if parsed_data is None:
        st.warning("请先在简历管理页面解析您的简历")
        st.stop()
    # 选择评价岗位
    st.subheader("选择评价岗位")
    job_options = list(session_state.interview_system.job_data.keys())
    job = st.selectbox("请选择要评价的岗位", job_options)
    # 检查是否有该岗位的评估历史
    evaluations = user_data.get("resume_evaluations", {})
    existing_evaluation = evaluations.get(job) if evaluations else None
    # 评价按钮
    if st.button("生成简历评价报告"):
        with st.spinner("正在分析简历..."):
            # 进行简历评估
            evaluation = session_state.interview_system.evaluator.evaluate_resume(parsed_data, job)
            # 保存评估结果
            session_state.user_manager.save_resume_evaluation(user, job, evaluation)
            session_state.user_manager.save_users()
            st.success("简历评价完成！")
            existing_evaluation = evaluation

    # 显示评估结果
    if existing_evaluation:
        st.subheader(f"简历评价报告 - {job}岗位")

        # 显示评分卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("完整性评分", f"{existing_evaluation['scores']['completeness']:.1f}%")
        with col2:
            st.metric("关键词匹配度", f"{existing_evaluation['scores']['keyword_match']:.1f}%")
        with col3:
            st.metric("技能相关性", f"{existing_evaluation['scores']['skill_relevance']:.1f}%")
        with col4:
            st.metric("整体评分", f"{existing_evaluation['scores']['overall']:.1f}%")

        # 显示雷达图
        st.subheader("能力维度分析")
        fig = session_state.interview_system.evaluator.visualize_evaluation(existing_evaluation)
        st.pyplot(fig)

        # 显示关键词分析
        st.subheader("关键词匹配分析")
        if existing_evaluation["missing_keywords"]:
            st.warning(f"简历中缺失以下{len(existing_evaluation['missing_keywords'])}个重要关键词:")
            cols = st.columns(3)
            for i, keyword in enumerate(existing_evaluation["missing_keywords"]):
                cols[i % 3].write(f"- {keyword}")
        else:
            st.success("简历包含所有岗位相关关键词！")

        # 显示改进建议
        st.subheader("改进建议")
        for i, recommendation in enumerate(existing_evaluation["recommendations"], 1):
            st.markdown(f"{i}. {recommendation}")
    else:
        st.info("请点击上方按钮生成简历评价报告")