# 传统功能实现函数
import wave
from pydub import AudioSegment

# 1. 音频wav转化成pcm
def convert_wav_to_pcm(wav_path, pcm_path):
    try:
        with wave.open(wav_path, 'rb') as wav:
            if wav.getsampwidth() == 2 and wav.getframerate() == 16000 and wav.getnchannels() == 1:
                # 如果 WAV 格式符合要求，直接复制数据
                with open(pcm_path, 'wb') as pcm:
                    pcm.write(wav.readframes(wav.getnframes()))
            else:
                # 如果 WAV 格式不符合要求，使用 pydub 进行转换
                audio = AudioSegment.from_wav(wav_path)
                audio = audio.set_frame_rate(16000).set_sample_width(2).set_channels(1)
                with open(pcm_path, 'wb') as pcm:
                    pcm.write(audio.raw_data)
    except Exception as e:
        print(f"转换过程中出现错误: {e}")

# 1. 根据评分直接生成反馈（不调用AI解析）
def generate_feedback_history(scores, text):
    """根据评分直接生成反馈建议（纯逻辑判断，不调用AI）"""
    feedback = {
        "🌟 能力点评": [],
        "📈 改进建议": []
    }

    # 能力点评（肯定高分项）
    if scores["语言表达能力"] >= 85:
        feedback["🌟 能力点评"].append("语言表达流畅自然，逻辑性强")
    if scores["逻辑思维能力"] >= 85:
        feedback["🌟 能力点评"].append("逻辑清晰，论证有条理")
    if scores["专业知识水平"] >= 85:
        feedback["🌟 能力点评"].append("专业知识扎实，符合岗位要求")
    if scores["技能匹配度"] >= 85:
        feedback["🌟 能力点评"].append("技能与岗位需求高度匹配，案例丰富")
    if scores["应变抗压与创新能力"] >= 85:
        feedback["🌟 能力点评"].append("应对压力和突发问题的能力强，有创新思维")

    # 改进建议（针对中等分数段）
    if 60 <= scores["语言表达能力"] < 85:
        feedback["📈 改进建议"].append("可进一步提高语言简洁性，减少不必要的重复")
    if 60 <= scores["逻辑思维能力"] < 85:
        feedback["📈 改进建议"].append("建议使用「首先...其次...最后」等连接词增强逻辑性")
    if 60 <= scores["专业知识水平"] < 85:
        feedback["📈 改进建议"].append("需补充该领域核心知识点，结合岗位需求深化理解")
    if 60 <= scores["技能匹配度"] < 85:
        feedback["📈 改进建议"].append("可多提及与岗位要求直接相关的技能和项目经验")
    if 60 <= scores["应变抗压与创新能力"] < 85:
        feedback["📈 改进建议"].append("可增加应对突发问题的案例，展示灵活应变能力")

    # 重点改进（针对低分段）
    if scores["语言表达能力"] < 60:
        feedback["📈 改进建议"].append("⚠️ 语言表达连贯性不足，建议通过复述练习提高流畅度")
    if scores["逻辑思维能力"] < 60:
        feedback["📈 改进建议"].append("⚠️ 逻辑结构不清晰，建议用思维导图梳理回答框架")
    if scores["专业知识水平"] < 60:
        feedback["📈 改进建议"].append("⚠️ 专业知识薄弱，建议系统学习该领域核心知识体系")
    if scores["技能匹配度"] < 60:
        feedback["📈 改进建议"].append("⚠️ 技能与岗位需求不匹配，建议针对性提升相关技能")
    if scores["应变抗压与创新能力"] < 60:
        feedback["📈 改进建议"].append("⚠️ 应变能力不足，建议通过模拟压力面试场景加强训练")

    # 针对极差分数（<50）的额外建议
    if scores["语言表达能力"] < 30:
        feedback["📈 改进建议"].append("🚨 语言表达维度较差，建议每日进行即兴演讲练习")
    if scores["逻辑思维能力"] < 30:
        feedback["📈 改进建议"].append("🚨 逻辑思维维度较差，推荐学习《金字塔原理》提升结构化表达")
    if scores["专业知识水平"] < 30:
        feedback["📈 改进建议"].append("🚨 专业知识维度较差，建议报名相关培训课程系统学习")
    if scores["技能匹配度"] < 30:
        feedback["📈 改进建议"].append("🚨 技能匹配度维度较差，建议考取相关专业认证")
    if scores["应变抗压与创新能力"] < 30:
        feedback["📈 改进建议"].append("🚨 应变能力维度较差，可通过角色扮演模拟面试场景训练")

    # 总体建议
    low_dimensions = [dim for dim, score in scores.items() if score < 60]
    if len(low_dimensions) >= 3:
        feedback["📈 改进建议"].append("💡 多个能力维度需要提升，建议先从专业知识和技能匹配度入手")
        feedback["📈 改进建议"].append("💡 可使用本系统的模拟面试功能，针对性训练薄弱环节")

    # 处理空点评/建议的情况
    if not feedback["🌟 能力点评"]:
        feedback["🌟 能力点评"].append("各维度表现中等，需进一步提升优势项")
    if not feedback["📈 改进建议"]:
        feedback["📈 改进建议"].append("整体表现优秀，可保持当前状态并持续优化细节")

    return feedback


from typing import Dict, List

# 全局配置：分数档划分（0-100分）
SCORE_LEVELS = {
    "优秀": (80, 100),  # 80-100分
    "良好": (60, 79),  # 60-79分
    "一般": (40, 59),  # 40-59分
    "较差": (0, 39)  # 0-39分
}

# 离线建议模板（按维度和分数档预设）
FEEDBACK_TEMPLATES = {
    # 1. 回答正确性模板（基于是否匹配问题核心）
    "回答正确性": {
        "优秀": ["1. 回答完全正确，精准覆盖问题核心要点，逻辑严谨。", "2. 对问题的理解透彻，技术细节描述准确。"],
        "良好": ["1. 回答基本正确，但部分细节不够完善。", "2. 对问题的核心概念有正确理解，但展开不够充分。"],
        "一般": ["1. 回答部分正确，存在概念模糊或理解偏差。", "2. 未完全抓住问题核心，需加强对问题的分析能力。"],
        "较差": ["1. 回答错误或完全偏离问题核心。", "2. 未理解问题本质，需重新学习相关基础概念。"]
    },
    # 2. 能力点评模板（按技术岗核心能力）
    "能力点评": {
        "优秀": ["1. 专业知识扎实，技术术语使用准确。", "2. 逻辑清晰，表达流畅，岗位匹配度高。"],
        "良好": ["1. 具备基础专业知识，能应对常规技术问题。", "2. 逻辑基本清晰，需提升复杂问题的分析能力。"],
        "一般": ["1. 专业知识存在漏洞，核心概念掌握不牢固。", "2. 逻辑不够连贯，表达缺乏层次感。"],
        "较差": ["1. 专业知识薄弱，存在明显知识盲区。", "2. 逻辑混乱，无法清晰表达观点，岗位匹配度低。"]
    },
    # 3. 改进建议模板（分档给出可操作方法）
    "改进建议": {
        "优秀": ["1. 保持现有学习节奏，可深入研究领域前沿技术。", "2. 尝试将知识应用到复杂项目中，提升实战能力。"],
        "良好": ["1. 针对薄弱知识点进行专项练习，强化理解。", "2. 多参与技术讨论，提升表达的严谨性。"],
        "一般": ["1. 系统学习基础理论，构建知识框架。", "2. 练习结构化表达，按“问题-分析-结论”框架组织思路。"],
        "较差": ["1. 从基础概念开始学习，推荐入门教材和课程。", "2. 先模仿优秀回答的结构，逐步形成自己的逻辑。"]
    },
    # 4. 推荐资源模板（分档推荐学习材料）
    "推荐资源": {
        "优秀": ["1. 领域顶会论文（如NeurIPS、ICML最新论文）。", "2. 开源项目源码阅读（如GitHub热门仓库）。"],
        "良好": ["1. 进阶教材（如《深度学习进阶》《机器学习实战》）。", "2. 专业技术博客（如TowardsDataScience、机器之心）。"],
        "一般": ["1. 基础教材（如《深度学习入门》《机器学习基础》）。", "2. 在线课程（如Coursera入门课程、B站系统课）。"],
        "较差": ["1. 零基础入门书籍（如《Python深度学习》《机器学习通俗解释》）。", "2. 入门视频教程（如MOOC基础课、菜鸟教程）。"]
    }
}


def get_score_level(score: int) -> str:
    """根据分数判断所属档次，确保分数在有效范围内"""
    # 限制分数在0-100之间，避免无效分数导致的错误
    score = max(0, min(100, score))
    for level, (min_score, max_score) in SCORE_LEVELS.items():
        if min_score <= score <= max_score:
            return level
    return "较差"  # 默认最低档


def generate_feedback_test(scores: Dict, text: str, domain: str, position: str, question: str = None) -> List:
    """
    离线生成反馈：基于分数档返回结构化建议，添加索引安全检查
    """
    print(f"生成离线反馈（问题：{question[:20]}...）")
    feedback = []

    # 确保scores不是空字典，避免后续处理出错
    if not scores:
        scores = {"专业知识水平": 0}

    # 1. 回答正确性（根据问题与回答的匹配度评分）
    try:
        if len(text.strip()) < 20 or text.strip().lower() in ["不知道", "没学过", "不清楚"]:
            correctness_level = "较差"
        else:
            # 实际应用中可根据关键词匹配度计算分数
            correctness_level = get_score_level(scores.get("专业知识水平", 0))  # 复用专业知识分数档

        feedback.append("回答正确性")
        # 安全获取模板内容，确保索引有效
        if correctness_level in FEEDBACK_TEMPLATES["回答正确性"]:
            feedback.extend(FEEDBACK_TEMPLATES["回答正确性"][correctness_level])
        else:
            feedback.extend(FEEDBACK_TEMPLATES["回答正确性"]["较差"])
        feedback.append("")  # 章节间空行
    except Exception as e:
        feedback.append("回答正确性")
        feedback.append("1. 无法生成评估，存在数据错误")
        feedback.append("")
        print(f"回答正确性生成错误: {e}")

    # 2. 能力点评（基于各维度分数）
    try:
        feedback.append("能力点评")
        # 取最低分的2个维度重点点评，确保至少有1个维度
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])[:min(2, len(scores))]

        for i, (dim, score) in enumerate(sorted_scores, 1):
            level = get_score_level(score)
            # 安全访问模板，确保列表索引存在
            if level in FEEDBACK_TEMPLATES["能力点评"] and FEEDBACK_TEMPLATES["能力点评"][level]:
                # 分割字符串时确保包含分隔符
                template_parts = FEEDBACK_TEMPLATES["能力点评"][level][0].split('：')
                template_text = template_parts[1] if len(template_parts) > 1 else template_parts[0]
                feedback.append(f"{i}. {dim}（{score}分，{level}）：{template_text}")
            else:
                feedback.append(f"{i}. {dim}（{score}分，{level}）：需要加强该方面能力")

        feedback.append("")
    except Exception as e:
        feedback.append("能力点评")
        feedback.append("1. 无法生成点评，存在数据错误")
        feedback.append("")
        print(f"能力点评生成错误: {e}")

    # 3. 改进建议（基于最低分维度）
    try:
        feedback.append("改进建议")
        # 安全获取最差维度，确保列表非空
        if scores:
            worst_dim = sorted(scores.items(), key=lambda x: x[1])[0][0]
            worst_level = get_score_level(scores[worst_dim])
        else:
            worst_level = "较差"

        # 安全获取模板内容
        if worst_level in FEEDBACK_TEMPLATES["改进建议"]:
            feedback.extend(FEEDBACK_TEMPLATES["改进建议"][worst_level])
        else:
            feedback.extend(FEEDBACK_TEMPLATES["改进建议"]["较差"])
        feedback.append("")
    except Exception as e:
        feedback.append("改进建议")
        feedback.append("1. 无法生成建议，存在数据错误")
        feedback.append("")
        print(f"改进建议生成错误: {e}")

    # 4. 推荐资源（基于整体分数水平）
    try:
        feedback.append("推荐资源")
        if scores:
            avg_score = sum(scores.values()) / len(scores)
            avg_level = get_score_level(int(avg_score))
        else:
            avg_level = "较差"

        # 安全获取模板内容
        if avg_level in FEEDBACK_TEMPLATES["推荐资源"]:
            feedback.extend(FEEDBACK_TEMPLATES["推荐资源"][avg_level])
        else:
            feedback.extend(FEEDBACK_TEMPLATES["推荐资源"]["较差"])
    except Exception as e:
        feedback.append("推荐资源")
        feedback.append("1. 无法生成推荐，存在数据错误")
        print(f"推荐资源生成错误: {e}")

    return feedback
