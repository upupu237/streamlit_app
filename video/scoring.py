import cv2
import time
import numpy as np
import json
import threading
import websocket
import base64
import datetime
import hashlib
import hmac
from urllib.parse import urlparse, urlencode
from time import mktime
from wsgiref.handlers import format_date_time
import re
from video.analize import BodyLanguageAnalyzer, MicroExpressionAnalyzer


class FusionScorer:
    def __init__(self):
        self.weights = {
            "坐姿端正度": 0.25,
            "微表情自然度": 0.25,
            "肩膀展开度": 0.20,
            "眨眼频率": 0.15,
            "手臂动作协调性": 0.15,
            "表情多样性": 0.0
        }

        self.model_weights = {
            "original": 0.7,
            "spark": 0.3
        }

        self.blink_rate_normal = (12, 25)
        self.posture_threshold = 0.35
        self.min_posture_score = 30

        # 讯飞星火配置
        self.spark_ws_url = "wss://spark-api.xf-yun.com/v1/x1"
        self.spark_appid = "a41d4e53"
        self.spark_api_key = "bea02f89128db159713e9621ef04da0e"
        self.spark_api_secret = "NTdhZDRmODAwZTNkZjVkNWNjNWUwYzkx"
        self.spark_domain = "x1"

        # 响应存储
        self.spark_response = None
        self.spark_reasoning = ""
        self.spark_content = ""
        self.response_received = threading.Event()

    def score_video(self, video_path):
        body_analyzer = BodyLanguageAnalyzer()
        micro_analyzer = MicroExpressionAnalyzer()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"无法打开视频文件: {video_path}")

        shoulder_scores, blink_scores = [], []
        posture_scores, emotion_scores = [], []
        arm_scores, expression_scores = [], []

        frame_descriptions = []
        frame_interval = 10
        frame_count_for_spark = 0

        frame_count = 0
        valid_frames = 0

        prev_expression = None
        expression_changes = 0

        print(f"开始分析面试视频: {video_path}")
        start_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 校验帧数据有效性
            if frame is None:
                print(f"警告: 第{frame_count}帧数据为空，跳过")
                frame_count += 1
                continue

            frame_count += 1
            if frame_count % 5 != 0:
                continue

            # 分析人体姿态
            body_result = body_analyzer.analyze_frame(frame)

            # 校验姿态分析结果（确保body_result是字典）
            if body_result is None:
                print(f"警告: 第{frame_count}帧人体姿态分析失败，结果为None")
                if frame_count < 10:
                    cv2.imwrite(f"error_frame_{frame_count}.jpg", frame)
                continue
            if not isinstance(body_result, dict):
                print(f"警告: 第{frame_count}帧人体姿态结果非字典，类型: {type(body_result)}")
                continue

            if "status" not in body_result:
                print(f"警告: 第{frame_count}帧人体姿态结果无status字段: {body_result}")
                continue

            if body_result["status"] != "检测到人体":
                continue

            valid_frames += 1

            # 关键修改：强制子对象为字典（避免None）
            pose = body_result.get("pose") or {}  # 若pose是None，转为空字典
            if not isinstance(pose, dict):
                print(f"警告: 第{frame_count}帧pose非字典，重置为空字典")
                pose = {}
            shoulder_width = pose.get("shoulder_width", 0)
            shoulder_scores.append(self._calc_shoulder_score(shoulder_width))

            # 关键修改：强制facial为字典
            facial = body_result.get("facial") or {}
            if not isinstance(facial, dict):
                print(f"警告: 第{frame_count}帧facial非字典，重置为空字典")
                facial = {}
            blink_rate = facial.get("blinks_per_minute", 0)
            blink_scores.append(self._calc_blink_score(blink_rate))

            # 关键修改：强制posture为字典
            posture = body_result.get("posture") or {}
            if not isinstance(posture, dict):
                print(f"警告: 第{frame_count}帧posture非字典，重置为空字典")
                posture = {}
            posture_angle = abs(posture.get("angle", 0))
            posture_scores.append(self._calc_posture_score(posture_angle))

            arm_scores.append(body_analyzer.calculate_arm_smoothness())

            # 分析微表情（确保emotion_result是字典）
            emotion_result = micro_analyzer.analyze_frame(frame)
            if emotion_result is None:
                print(f"警告: 第{frame_count}帧微表情分析失败，结果为None")
                emotion_result = {"dominant_emotion": None, "confidence": 0, "weight": 0}
            elif not isinstance(emotion_result, dict):
                print(f"警告: 第{frame_count}帧微表情结果非字典，类型: {type(emotion_result)}")
                emotion_result = {"dominant_emotion": None, "confidence": 0, "weight": 0}

            if emotion_result.get("dominant_emotion"):
                emotion_scores.append(
                    self._calc_emotion_score(
                        emotion_result.get("confidence", 0),
                        emotion_result.get("weight", 0)
                    )
                )

            current_expression = facial.get("expression", "中性")
            expression_scores.append(self._calc_expression_score(current_expression))

            if prev_expression and current_expression != prev_expression:
                expression_changes += 1
            prev_expression = current_expression

            frame_count_for_spark += 1
            if frame_count_for_spark % frame_interval == 0:
                frame_desc = self._generate_frame_description(body_result, emotion_result)
                frame_descriptions.append(frame_desc)
                print(f"已收集帧描述 {len(frame_descriptions)} 条")

        cap.release()

        if valid_frames == 0:
            raise ValueError("视频中未检测到有效人体姿态")

        expression_variety_bonus = min(10, expression_changes * 0.5)

        original_scores = {
            "坐姿端正度": self._average(posture_scores),
            "微表情自然度": self._average(emotion_scores),
            "肩膀展开度": self._average(shoulder_scores),
            "眨眼频率": self._average(blink_scores),
            "手臂动作协调性": self._average(arm_scores),
            "表情多样性": self._average(expression_scores) + expression_variety_bonus,
        }
        original_scores["微表情自然度"] = min(100, original_scores["微表情自然度"] * 0.8 + original_scores[
            "表情多样性"] * 0.2)

        original_total_score = sum(original_scores[dim] * self.weights[dim] for dim in self.weights)
        original_total_score = round(min(max(original_total_score, 0), 100), 2)

        # 帧描述检查
        print(f"准备调用星火模型评分，共收集{len(frame_descriptions)}帧描述")
        for i, desc in enumerate(frame_descriptions[:3]):
            print(f"帧{i + 1}描述示例:\n{desc[:200]}...")

        spark_dim_scores, spark_total_score = self._get_spark_scores(frame_descriptions, original_scores)

        final_total_score = round(
            original_total_score * self.model_weights["original"] +
            spark_total_score * self.model_weights["spark"],
            2
        )

        scores = {
            **original_scores, **spark_dim_scores,
            "原有模型综合评分": original_total_score,
            "讯飞星火模型评分": spark_total_score,
            "综合面试评分": final_total_score
        }

        return scores

    def _generate_frame_description(self, body_result, emotion_result):
        # 安全生成帧描述（确保所有子对象是字典）
        body_result = body_result or {}  # 防止body_result为None
        emotion_result = emotion_result or {}  # 防止emotion_result为None

        desc = f"姿态: {body_result.get('summary', '未知')}\n"
        desc += f"主要情绪: {emotion_result.get('dominant_emotion', '未知')}, 置信度: {emotion_result.get('confidence', 0):.2f}\n"

        facial = body_result.get("facial") or {}  # 强制facial为字典
        desc += f"面部表情: {facial.get('expression', 'N/A')}\n"

        posture = body_result.get("posture") or {}  # 强制posture为字典
        desc += f"坐姿状态: {posture.get('status', 'N/A')}"
        if "angle" in posture:
            desc += f", 倾斜角度: {abs(posture['angle']):.2f}\n"
        else:
            desc += "\n"

        if "blinks_per_minute" in facial:
            desc += f"眨眼频率: {facial['blinks_per_minute']}次/分钟\n"

        return desc

    def _get_spark_scores(self, frame_descriptions, original_scores):
        if not frame_descriptions:
            print("警告: 未收集到帧描述，使用原有模型维度评分作为替代")
            spark_dim_scores = {f"星火_{k}": v for k, v in original_scores.items()}
            spark_total_score = sum(original_scores[dim] * self.weights[dim] for dim in self.weights)
            return spark_dim_scores, round(spark_total_score, 2)

        # 提示词（保持不变）
        prompt = """请作为专业的面试行为分析师，根据提供的视频帧信息，对面试者的以下6个维度进行独立评分（每个维度0-100分）。

评分标准（请严格依据视频帧描述中的客观数据判断）：
- 坐姿端正度：挺直坐姿（角度<5°）100分，轻微弯曲（5°-10°）80分，明显弯腰驼背（>30°）30-50分
- 微表情自然度：自然微笑/中性表情80-100分，紧张/僵硬表情40-60分，无表情30分以下
- 肩膀展开度：完全展开（宽度>0.3m）100分，适度展开（0.2-0.3m）80-99分，含胸驼背（<0.15m）50分以下
- 眨眼频率：正常频率(12-25次/分)100分，过快（>25）按偏离程度扣分，最低60分，过慢按程度给90-100分
- 手臂动作协调性：动作流畅自然100分，轻微僵硬80-99分，明显不协调/过多小动作60分以下
- 表情多样性：表情丰富多变（3种以上）100分，适度变化（2-3种）80分，过于单一（1种）60分以下

请严格按照以下格式返回评分结果（仅返回评分，不要添加任何解释、分析或其他内容）：

坐姿端正度: XX分
微表情自然度: XX分
肩膀展开度: XX分
眨眼频率: XX分
手臂动作协调性: XX分
表情多样性: XX分

视频帧分析数据（包含客观测量值）：
"""

        for i, desc in enumerate(frame_descriptions[:5]):
            prompt += f"\n帧{i + 1}详细数据:\n{desc}"

        try:
            self._call_spark_ws_api(prompt)

            if not self.spark_response:
                raise Exception("未收到星火模型返回结果，使用默认评分")

            print(f"星火模型返回内容:\n{self.spark_response}")

            spark_dim_scores = self._parse_spark_dim_scores(self.spark_response, original_scores)
            # 强制spark_dim_scores为完整字典（无None值）
            for dim in self.weights.keys():
                if dim not in spark_dim_scores or spark_dim_scores[dim] is None:
                    spark_dim_scores[dim] = original_scores[dim]
                    print(f"修复星火评分None值 - {dim}: {original_scores[dim]}")

            spark_total_score = sum(spark_dim_scores[dim] * self.weights[dim] for dim in self.weights)
            spark_total_score = round(min(max(spark_total_score, 0), 100), 2)

            spark_dim_scores = {f"星火_{k}": v for k, v in spark_dim_scores.items()}
            return spark_dim_scores, spark_total_score

        except Exception as e:
            print(f"调用讯飞星火API出错: {e}")
            spark_dim_scores = {f"星火_{k}": v for k, v in original_scores.items()}
            spark_total_score = sum(original_scores[dim] * self.weights[dim] for dim in self.weights)
            return spark_dim_scores, round(spark_total_score, 2)

    def _call_spark_ws_api(self, prompt):
        self.spark_reasoning = ""
        self.spark_content = ""
        self.spark_response = None
        self.response_received = threading.Event()

        def create_ws_url():
            host = urlparse(self.spark_ws_url).netloc
            path = urlparse(self.spark_ws_url).path
            now = datetime.datetime.now()
            date = format_date_time(mktime(now.timetuple()))

            signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
            signature_sha = hmac.new(
                self.spark_api_secret.encode('utf-8'),
                signature_origin.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            signature_base64 = base64.b64encode(signature_sha).decode('utf-8')

            authorization_origin = (
                f'api_key="{self.spark_api_key}", algorithm="hmac-sha256", '
                f'headers="host date request-line", signature="{signature_base64}"'
            )
            authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

            v = {"authorization": authorization, "date": date, "host": host}
            return self.spark_ws_url + '?' + urlencode(v)

        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data['header']['code'] != 0:
                    print(f"API错误: {data['header']['message']}")
                    self.spark_response = f"API错误: {data['header']['message']}"
                    self.response_received.set()
                    return

                if "text" in data["payload"]["choices"]:
                    text_item = data["payload"]["choices"]["text"][0]
                    self.spark_reasoning += text_item.get("reasoning_content", "")
                    self.spark_content += text_item.get("content", "")

                if data["payload"]["choices"]["status"] == 2:
                    raw_content = self.spark_content.strip() or self.spark_reasoning.strip()
                    clean_pattern = re.compile(r'```json?\s*(.*?)\s*```', re.DOTALL | re.IGNORECASE)
                    match = clean_pattern.search(raw_content)
                    self.spark_response = match.group(1).strip() if match else raw_content
                    print(f"星火模型返回内容（清理后）:\n{self.spark_response}")
                    self.response_received.set()

            except Exception as e:
                print(f"解析WebSocket消息出错: {e}")
                self.spark_response = f"解析错误: {str(e)}"
                self.response_received.set()

        def on_error(ws, error):
            print(f"WebSocket错误: {error}")
            self.spark_response = f"WebSocket错误: {str(error)}"
            self.response_received.set()

        def on_close(ws, close_status_code, close_msg):
            print(f"WebSocket关闭: 状态码{close_status_code}, 消息{close_msg}")
            if not self.response_received.is_set():
                self.spark_response = f"WebSocket提前关闭: {close_status_code}"
                self.response_received.set()

        def on_open(ws):
            data = {
                "header": {"app_id": self.spark_appid, "uid": "interview_scorer_v2"},
                "parameter": {
                    "chat": {"domain": self.spark_domain, "temperature": 0.2, "max_tokens": 600, "top_p": 0.9}},
                "payload": {"message": {"text": [{"role": "user", "content": prompt}]}}
            }
            ws.send(json.dumps(data))
            print("请求已发送至星火模型")

        ws_url = create_ws_url()
        ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error,
                                    on_close=on_close)
        ws_thread = threading.Thread(target=ws.run_forever, kwargs={"sslopt": {"check_hostname": True}})
        ws_thread.start()
        self.response_received.wait(timeout=60)
        ws.close()
        ws_thread.join()

    def _parse_spark_dim_scores(self, response, original_scores):
        print(f"开始解析星火模型评分，响应内容:\n{response[:300]}...")
        if not response:
            print("错误: 星火返回为空，使用原有评分")
            return {dim: original_scores[dim] for dim in self.weights.keys()}

        dim_scores = {}
        required_dimensions = list(self.weights.keys())
        lines = [line.strip() for line in response.split('\n') if line.strip()]

        # 提取评分部分
        score_section = None
        for i, line in enumerate(lines):
            if any(dim in line for dim in required_dimensions):
                score_section = lines[i:]
                break
        if not score_section:
            print("未找到评分部分，使用原有评分")
            return {dim: original_scores[dim] for dim in required_dimensions}

        # 解析评分
        for line in score_section:
            for dim in required_dimensions:
                if dim in line and dim not in dim_scores:
                    score_match = re.search(r'(\d+(?:\.\d+)?)\s*分?', line)
                    if score_match:
                        try:
                            score = float(score_match.group(1))
                            if 0 <= score <= 100:
                                dim_scores[dim] = round(score, 2)
                                print(f"解析到{dim}: {score}分")
                        except ValueError:
                            continue

        # 补全缺失维度（确保无None）
        for dim in required_dimensions:
            if dim not in dim_scores or dim_scores[dim] is None:
                dim_scores[dim] = original_scores[dim]
                print(f"补全{dim}评分: {original_scores[dim]}")

        print(f"星火评分解析完成: {dim_scores}")
        return dim_scores

    # 以下方法保持不变
    def _calc_shoulder_score(self, width):
        return min(max((width - 0.12) * 700, 0), 100)

    def _calc_blink_score(self, rate):
        min_rate, max_rate = self.blink_rate_normal
        if min_rate <= rate <= max_rate:
            return 100
        return max(80, 100 - (min_rate - rate) * 2) if rate < min_rate else max(0, 100 - (rate - max_rate) * 3)

    def _calc_posture_score(self, angle):
        if angle < self.posture_threshold * 0.4:
            return 100
        elif angle < self.posture_threshold * 0.7:
            return max(75, 100 - (angle / self.posture_threshold) * 80)
        elif angle < self.posture_threshold:
            return max(50, 75 - (angle - self.posture_threshold * 0.7) / (self.posture_threshold * 0.3) * 25)
        else:
            return max(self.min_posture_score, 50 - (angle - self.posture_threshold) / self.posture_threshold * 20)

    def _calc_emotion_score(self, confidence, weight):
        base = confidence * 100
        bonus = min(0.25, confidence * 1.0) if weight >= 1.0 else -min(0.15, (1.0 - weight) * 0.6)
        return min(100, max(0, base * weight * (1.0 + bonus)))

    def _calc_expression_score(self, expression):
        mapping = {"微笑": 90, "感兴趣": 85, "惊讶": 80, "思考": 75, "中性": 70, "紧张": 60, "说话": 70}
        return mapping.get(expression, 60)

    def _average(self, lst):
        return round(sum(lst) / len(lst), 2) if lst else 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python scoring.py <视频文件路径>")
        sys.exit(1)
    video_file = sys.argv[1]
    scorer = FusionScorer()
    try:
        scores = scorer.score_video(video_file)
        print("\n" + "=" * 50)
        print("面试视频多维度评分结果")
        print("=" * 50)
        original_dims = ["坐姿端正度", "微表情自然度", "肩膀展开度", "眨眼频率", "手臂动作协调性", "表情多样性"]
        print("\n【原始模型评分】")
        for dim in original_dims:
            print(f"{dim}: {scores[dim]:.1f}分")
        print("\n【星火模型评分】")
        for dim in original_dims:
            print(f"{dim}: {scores[f'星火_{dim}']:.1f}分")
        print("\n【综合评分】")
        print(f"原有模型综合评分: {scores['原有模型综合评分']:.1f}分")
        print(f"讯飞星火模型评分: {scores['讯飞星火模型评分']:.1f}分")
        print(f"最终综合评分: {scores['综合面试评分']:.1f}分")
    except Exception as e:
        print(f"评分出错: {e}")
        import traceback

        traceback.print_exc()