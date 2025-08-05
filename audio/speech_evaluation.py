# 调用讯飞模型相关函数
import re
import json
from collections import Counter
# 统一使用相对导入（同一audio目录下）
import re

import streamlit as st

from .xf_spark_api import call_spark_x1

def clean_recognition_result(text):
    if not isinstance(text, str) or not text.strip():
        return ""

    prompt = f"""
    请对以下文本进行清洗处理，具体要求：
    1. 去除连续重复的内容（包括字符重复和语义重复）。
    2. 去除冗余标点符号，保留必要断句。
    3. 修正口语化重复，保持核心语义不变。
    4. 仅返回清洗后的文本，无需解释。

    待清洗文本：{text}
    """

    try:
        # 仅传递prompt，无其他参数
        cleaned_text = call_spark_x1(prompt=prompt)  # ✅ 正确调用

        # 二次处理
        cleaned_text = cleaned_text.strip()
        return re.sub(r'\s+', ' ', cleaned_text)  # 合并空格

    except Exception as e:
        print(f"AI清洗失败，使用备用方案：{e}")
        # 降级逻辑（保持不变）
        text = re.sub(r'[\s,\u3000。！？、,.!?\-]+', ' ', text)
        for size in range(3, 10):
            text = re.sub(r'(\w{' + str(size) + r'})\1+', r'\1', text)
        return text.strip()

# ————————————————————2. 有关评分的所有函数———————————————————
# 2.1上传音频分析和评分函数
def evaluate_text(text, domain, position):
    """调用讯飞星火模型进行智能评分，增强JSON解析容错性"""
    default_scores = {
        "专业知识水平": 50,
        "技能匹配度": 50,
        "语言表达能力": 50,
        "逻辑思维能力": 50,
        "应变抗压与创新能力": 50
    }

    prompt = f"""
    请作为资深面试官，对以下{domain}领域{position}的面试回答进行评分（0-100分）。
    评估维度固定为：
    1. 专业知识水平
    2. 技能匹配度
    3. 语言表达能力
    4. 逻辑思维能力
    5. 应变抗压与创新能力

    回答文本：{text}

    输出要求：
    - 仅返回JSON格式，键为上述5个维度名称，值为整数分数（0-100）
    - 禁止包含任何额外文字、解释、标记
    """

    try:
        # 调用讯飞星火API
        response = call_spark_x1(prompt)
        response_clean = response.strip()

        # 打印原始响应用于调试
        print(f"原始API响应: {response_clean}")

        # 增强JSON提取逻辑 - 处理嵌套代码块
        import re

        # 提取最内层的JSON代码块
        json_blocks = re.findall(r'```json\s*(\{.*\})\s*```', response_clean, re.DOTALL)
        if json_blocks:
            clean_json_str = json_blocks[-1]  # 取最后一个匹配的JSON块
        else:
            # 如果没有找到标准代码块，尝试从混乱文本中提取JSON
            json_match = re.search(r'\{.*\}', response_clean, re.DOTALL)
            if json_match:
                clean_json_str = json_match.group(0)
            else:
                # 如果找不到任何JSON对象，使用宽松匹配
                clean_json_str = response_clean

        # 移除多余的代码块标记和非JSON内容
        clean_json_str = re.sub(r'^```(json)?\s*|\s*```$', '', clean_json_str, flags=re.IGNORECASE)

        # 处理重复键名问题（保留最后一个值）
        clean_json_str = re.sub(r'("专业知识水平":\s*\d+,\s*)("专业知识水平":)', r'\2', clean_json_str)
        clean_json_str = re.sub(r'("技能匹配度":\s*\d+,\s*)("技能匹配度":)', r'\2', clean_json_str)
        clean_json_str = re.sub(r'("语言表达能力":\s*\d+,\s*)("语言表达能力":)', r'\2', clean_json_str)
        clean_json_str = re.sub(r'("逻辑思维能力":\s*\d+,\s*)("逻辑思维能力":)', r'\2', clean_json_str)
        clean_json_str = re.sub(r'("应变抗压与创新能力":\s*\d+,\s*)("应变抗压与创新能力":)', r'\2', clean_json_str)

        # 移除非法控制字符
        clean_json_str = re.sub(r'[\x00-\x1F\x7F]', '', clean_json_str)

        # 规范化引号
        clean_json_str = clean_json_str.replace("'", '"')

        # 确保所有键都用双引号包裹
        clean_json_str = re.sub(r'([\{\s,]+)(\w+)(\s*:)', r'\1"\2"\3', clean_json_str)

        # 打印清洗后的JSON字符串
        print(f"清洗后的JSON字符串: {clean_json_str}")

        # 尝试解析JSON
        try:
            scores = json.loads(clean_json_str)
            print(f"JSON解析成功: {scores}")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            print(f"尝试修复格式错误...")

            # 尝试更激进的格式修复
            clean_json_str = re.sub(r',\s*([\}\]])', r'\1', clean_json_str)  # 移除尾部逗号
            clean_json_str = re.sub(r'"\s*:\s*([0-9]+)\s*,', r'":\1,', clean_json_str)  # 修复数字周围的空格

            # 处理可能的换行和缩进
            clean_json_str = re.sub(r'\s+', ' ', clean_json_str)

            try:
                scores = json.loads(clean_json_str)
                print(f"修复后JSON解析成功: {scores}")
            except json.JSONDecodeError as e2:
                print(f"修复后仍无法解析JSON: {str(e2)}")
                # 作为最后的手段，手动提取分数
                scores = {}
                for dim in default_scores.keys():
                    match = re.search(rf'"{dim}"\s*:\s*(\d+)', clean_json_str)
                    if match:
                        scores[dim] = int(match.group(1))
                    else:
                        scores[dim] = default_scores[dim]
                print(f"手动提取的分数: {scores}")

        # 验证评分维度完整性
        required_dimensions = [
            "专业知识水平", "技能匹配度",
            "语言表达能力", "逻辑思维能力",
            "应变抗压与创新能力"
        ]

        # 确保所有维度都有分数
        for dim in required_dimensions:
            if dim not in scores:
                scores[dim] = default_scores[dim]
                print(f"缺少维度 '{dim}'，使用默认分数")
            else:
                # 确保分数在0-100之间
                try:
                    scores[dim] = max(0, min(100, int(scores[dim])))
                except (ValueError, TypeError):
                    scores[dim] = default_scores[dim]
                    print(f"维度 '{dim}' 的分数无效，使用默认分数")

        return scores

    except Exception as e:
        # 增强错误日志，帮助调试
        print(f"评分获取失败: {str(e)}")
        return default_scores

# 2.2自我介绍专项评分函数
def evaluate_intro_text(text, domain, position):
    """自我介绍专项评分函数（修正维度定义，确保唯一）"""
    # 🌟 核心：使用简洁且唯一的维度名称，避免与其他评分函数冲突
    dimensions = [
        "信息完整性",  # 简化维度名称，去除冗余说明
        "岗位匹配度",
        "语言表达流畅度",
        "时长控制",
        "态度自信度"
    ]

    # 构造提示词（明确维度定义，避免模型返回混乱）
    prompt = f"""
    请作为资深HR，针对{domain}领域{position}的面试自我介绍进行评分。
    评估依据为以下文本内容：{text}

    评分维度及说明（严格按此维度返回）：
    1. 信息完整性：是否包含姓名、学历、核心经历等关键信息
    2. 岗位匹配度：提及的技能、经历与{position}岗位要求的匹配程度
    3. 语言表达流畅度：语句是否连贯，有无卡顿、重复或口头禅
    4. 时长控制：内容长度是否适合60-90秒的口头表达（过短或过长均扣分）
    5. 态度自信度：表达是否体现自信（如肯定句式、自然语气）

    要求：
    - 每个维度单独评分（0-100分，60分为合格线）
    - 结合{domain}领域特点（如技术岗侧重专业经历）
    - 输出格式为JSON，键为上述维度名称（严格一致，不要添加额外说明）
    - 仅返回纯JSON字符串（无代码块、无解释）
    """

    try:
        response = call_spark_x1(prompt)
        response_clean = response.strip()

        # 提取JSON（处理可能的代码块标记）
        import re
        json_pattern = re.compile(r'```json\s*(.*?)\s*```', re.DOTALL)
        match = json_pattern.search(response_clean)
        json_str = match.group(1).strip() if match else response_clean

        # 解析并校验维度
        scores = json.loads(json_str)

        # 缺失维度填充默认分50（并提示）
        for dim in dimensions:
            if dim not in scores:
                scores[dim] = 50
                print(f"警告：模型返回缺少维度「{dim}」，使用默认分50")

        return scores
    except Exception as e:
        print(f"自我介绍评分失败：{e}")
        # 失败时返回默认分
        return {dim: 50 for dim in dimensions}

# ————————————————————3. 有关反馈报告的所有函数———————————————————
# 3.1上传音频反馈报告
def generate_feedback(scores, text, domain, position):
    """
    调用讯飞星火大模型生成通用面试反馈（适配自我介绍、问题回答等场景）
    """
    # 构造通用提示词，兼容多种面试内容类型
    prompt = f"""
    请作为资深HR，针对以下面试内容生成简洁专业的反馈：

    一、基础信息：
    - 面试内容（可能是自我介绍或问题回答）：{text[:500]}  # 限制长度避免冗余
    - 能力得分：{json.dumps(scores, ensure_ascii=False)}
    - 低分阈值：60分（<60分为待改进项）

    二、反馈要求：
    1. 先判断内容类型（自我介绍/问题回答），再针对性点评：
       - 低分维度（<60分）：结合内容具体举例说明问题（如逻辑混乱可指"未按时间线介绍经历"）
       - 高分维度（>80分）：肯定亮点（如"技术术语使用准确"）

    2. 改进建议：
       - 对低分维度给1-2个可操作方法（如"自我介绍可增加岗位匹配度说明"）
       - 结合{domain}领域和{position}特点（如"技术岗建议补充项目细节"）

    3. 输出格式：
       - 分2部分："🌟 内容点评"、"📈 改进建议"（每部分1-2条）
       - 语言口语化，总字数≤200字，避免专业术语堆砌

    无需寒暄，直接输出反馈。
    """

    try:
        # 调用模型
        feedback = call_spark_x1(prompt)
        feedback = feedback.strip()

        # 清洗代码块标记
        if feedback.startswith("```") and feedback.endswith("```"):
            feedback = feedback.split("```")[1].strip()

        # 确保包含必要的标记
        if "🌟 内容点评" not in feedback or "📈 改进建议" not in feedback:
            # 若格式不完整，尝试自动分类
            lines = feedback.splitlines()
            comment_lines = []
            suggestion_lines = []
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 智能分类（根据关键词）
                if "点评" in line or "类型判断" in line or "分析" in line:
                    current_section = "点评"
                elif "建议" in line or "改进" in line or "提升" in line:
                    current_section = "建议"
                elif current_section:
                    if current_section == "点评":
                        comment_lines.append(line)
                    elif current_section == "建议":
                        suggestion_lines.append(line)

            # 重组反馈（确保格式正确）
            feedback = (
                "🌟 内容点评\n" +
                "\n".join([f"{i+1}. {line}" for i, line in enumerate(comment_lines)]) +
                "\n\n📈 改进建议\n" +
                "\n".join([f"{i+1}. {line}" for i, line in enumerate(suggestion_lines)])
            )

        # 调试打印：输出最终生成的反馈文本（包含关键词检查）
        print("="*50)
        print("generate_feedback返回的原始反馈：")
        print(feedback)
        print("\n关键词检查：")
        print(f"是否包含'🌟 内容点评'：{'🌟 内容点评' in feedback}")
        print(f"是否包含'📈 改进建议'：{'📈 改进建议' in feedback}")
        print("="*50)

        return feedback

    except Exception as e:
        # 改进降级方案，确保格式正确
        print(f"反馈生成失败：{e}")
        low_scores = [k for k, v in scores.items() if v < 60]

        comment = "🌟 内容点评\n"
        if low_scores:
            comment += f"1. 待改进：{', '.join(low_scores)}"
        else:
            comment += "1. 各维度表现合格"

        suggestion = (
            "📈 改进建议\n"
            f"1. 针对低分维度进行针对性练习\n"
            f"2. 结合{position}要求，增加{domain}领域相关细节"
        )

        feedback = f"{comment}\n\n{suggestion}"

        # 调试打印：降级方案生成的反馈
        print("="*50)
        print("降级方案生成的反馈：")
        print(feedback)
        print("="*50)

        return feedback


# 3.2模拟自我介绍反馈报告
import re
import json
import json

def generate_feedback_intro(scores, text, target_position, ideal_version, is_intro=True):
    """
    纯后端反馈生成函数（无前端代码，确保无undefined相关问题）
    """
    dimensions = ["信息完整性", "岗位匹配度", "语言表达流畅度", "时长控制", "态度自信度"]

    # 1. 强化提示词（明确格式要求）
    prompt = f"""
    作为{target_position}岗位面试官，生成5条自我介绍改进建议：
    1. 按"信息完整性→岗位匹配度→语言表达流畅度→时长控制→态度自信度"顺序
    2. 每条格式："序号. 维度：具体建议（分数：X分，[需改进/优势/待提升]）"
    3. 分数<60标"需改进"，≥80标"优势"，60-79标"待提升"
    4. 基于评分：{json.dumps(scores, ensure_ascii=False)}
    5. 基于回答内容：{text}
    6. 禁止返回JSON、代码块，仅返回纯文本建议
    """

    try:
        # 生成反馈
        feedback = call_spark_x1(prompt).strip()
        print("\n===== 后端反馈日志 =====")
        print(f"模型原始输出：\n{feedback}\n")

        # 2. 格式校验与修复（仅后端逻辑）
        # 检测并处理JSON格式
        if feedback.startswith("{") and feedback.endswith("}"):
            print("检测到JSON格式，手动生成建议")
            feedback_lines = []
            for i, dim in enumerate(dimensions):
                score = scores[dim]
                tag = "需改进" if score < 60 else "优势" if score >= 80 else "待提升"
                feedback_lines.append(f"{i+1}. {dim}：{tag}（{score}分），需补充岗位相关信息")
            feedback = "\n".join(feedback_lines)

        # 清理代码块标记
        if feedback.startswith("```") and feedback.endswith("```"):
            feedback = feedback.split("```")[1].strip()
            print(f"清理代码块后：\n{feedback}\n")

        # 分割为行并过滤空行
        lines = [line.strip() for line in feedback.splitlines() if line.strip()]

        # 确保5条建议（补充缺失维度）
        if len(lines) < 5:
            existing_dims = [dim for line in lines for dim in dimensions if dim in line]
            for i, dim in enumerate(dimensions):
                if dim not in existing_dims:
                    lines.insert(i, f"{i+1}. {dim}：自动补充建议（{scores[dim]}分，需改进）")
            lines = lines[:5]

        # 最终处理
        final_feedback = "\n".join(lines)
        print(f"最终反馈：\n{final_feedback}")
        print("===========================\n")
        return final_feedback

    except Exception as e:
        print(f"异常：{str(e)}，触发兜底逻辑")
        # 异常时手动生成建议
        error_feedback = [
            f"{i+1}. {dim}：生成失败（{scores[dim]}分，{['需改进','优势'][scores[dim]>=60]}），参考理想版本优化"
            for i, dim in enumerate(dimensions)
        ]
        error_feedback = "\n".join(error_feedback)
        print(f"兜底反馈：\n{error_feedback}")
        return error_feedback
