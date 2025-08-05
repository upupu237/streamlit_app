import logging
import cv2
from video.analize import BodyLanguageAnalyzer, MicroExpressionAnalyzer
from video.scoring import FusionScorer
from video.recorder import frame_queue, result_queue, recording_flag

class SafeBodyLanguageAnalyzer(BodyLanguageAnalyzer):
    def analyze_frame(self, frame):
        try:
            return super().analyze_frame(frame)
        except Exception as e:
            logging.error(f"肢体分析帧失败: {e}")
            return {"状态": "分析失败", "得分": 0, "描述": "无法识别肢体特征"}

    def get_frame_description(self, frame):
        try:
            analysis = self.analyze_frame(frame)
            posture = analysis.get("坐姿", "未知")
            shoulder = analysis.get("肩膀状态", "未知")
            return f"坐姿: {posture}, 肩膀: {shoulder}, 肢体得分: {analysis.get('得分', 0)}"
        except Exception as e:
            logging.warning(f"生成肢体描述失败: {e}")
            return "无法生成肢体特征描述"


class SafeMicroExpressionAnalyzer(MicroExpressionAnalyzer):
    def analyze_frame(self, frame):
        try:
            return super().analyze_frame(frame)
        except Exception as e:
            logging.error(f"微表情分析帧失败: {e}")
            return {"状态": "分析失败", "得分": 0, "情绪": "未知", "置信度": 0}

    def get_frame_description(self, frame):
        try:
            analysis = self.analyze_frame(frame)
            emotion = analysis.get("dominant_emotion", "未知")
            blink = analysis.get("眨眼状态", "正常")
            return f"主要情绪: {emotion}, 眨眼: {blink}, 表情得分: {analysis.get('得分', 0)}"
        except Exception as e:
            logging.warning(f"生成微表情描述失败: {e}")
            return "无法生成微表情特征描述"


class SafeFusionScorer(FusionScorer):
    def __init__(self):
        super().__init__()
        self.body_analyzer = SafeBodyLanguageAnalyzer()
        self.micro_analyzer = SafeMicroExpressionAnalyzer()

    def extract_frame_descriptions(self, video_path, max_frames=30):
        descriptions = []
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logging.error(f"无法打开视频: {video_path}")
                return descriptions

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            logging.info(f"开始提取帧描述: {video_path}, FPS: {fps}, 总帧数: {total_frames}")

            interval = max(1, int(total_frames / min(max_frames, total_frames)))
            if total_frames < 3:
                logging.warning(f"视频过短（{total_frames}帧），可能影响分析")
                interval = 1

            frame_idx = 0
            success_count = 0
            retry_limit = 2

            while frame_idx < total_frames and len(descriptions) < max_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    retry = 0
                    while retry < retry_limit and not ret:
                        logging.warning(f"读取帧 {frame_idx} 失败，重试 {retry + 1}/{retry_limit}")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                        ret, frame = cap.read()
                        retry += 1
                    if not ret:
                        logging.error(f"帧 {frame_idx} 读取失败，跳过")
                        frame_idx += interval
                        continue

                try:
                    frame_resized = cv2.resize(frame, (640, 480))
                    body_desc = self.body_analyzer.get_frame_description(frame_resized)
                    micro_desc = self.micro_analyzer.get_frame_description(frame_resized)
                    timestamp = frame_idx / fps
                    full_desc = f"帧 {frame_idx} (时间: {timestamp:.1f}s): {body_desc}; {micro_desc}"
                    descriptions.append(full_desc)
                    success_count += 1
                    logging.debug(f"生成帧 {frame_idx} 描述成功")
                except Exception as e:
                    logging.error(f"处理帧 {frame_idx} 时出错: {e}")

                frame_idx += interval

            cap.release()
            logging.info(f"帧描述提取完成: 成功 {success_count}/{len(descriptions)} 帧")

            if not descriptions:
                logging.warning("未提取到任何帧描述，添加默认描述")
                descriptions.append("视频帧分析：未识别到有效特征（可能因视频过短或质量问题）")

            return descriptions

        except Exception as e:
            logging.error(f"提取帧描述失败: {e}")
            return ["视频处理错误，无法生成帧描述"]

    def score_video(self, video_path):
        try:
            frame_descriptions = self.extract_frame_descriptions(video_path)
            from streamlit import session_state as st_session_state
            st_session_state.frame_descriptions = frame_descriptions
            logging.info(f"已收集帧描述 {len(frame_descriptions)} 条")

            result = super().score_video(video_path)

            if not isinstance(result, dict):
                raise ValueError("分析结果不是字典")
            required_keys = ["综合面试评分", "坐姿端正度", "微表情自然度", "原有模型综合评分", "讯飞星火模型评分"]
            for key in required_keys:
                if key not in result:
                    raise KeyError(f"缺少必要评分项: {key}")

            result["帧描述数量"] = len(frame_descriptions)
            return result
        except Exception as e:
            logging.error(f"评分失败: {e}")
            return {
                "综合面试评分": 0,
                "原有模型综合评分": 0,
                "讯飞星火模型评分": 0,
                "坐姿端正度": 0,
                "微表情自然度": 0,
                "肩膀展开度": 0,
                "眨眼频率": 0,
                "手臂动作协调性": 0,
                "表情多样性": 0,
                "星火_坐姿端正度": 0,
                "星火_微表情自然度": 0,
                "星火_肩膀展开度": 0,
                "星火_眨眼频率": 0,
                "星火_手臂动作协调性": 0,
                "星火_表情多样性": 0,
                "帧描述数量": len(frame_descriptions)
            }


# 全局分析器实例
body_analyzer = None
micro_analyzer = None
scorer = None

def init_analyzers():
    global body_analyzer, micro_analyzer, scorer
    try:
        body_analyzer = SafeBodyLanguageAnalyzer()
        micro_analyzer = SafeMicroExpressionAnalyzer()
        scorer = SafeFusionScorer()
        logging.info("分析器加载成功")
        return True
    except Exception as e:
        logging.error(f"分析器加载失败: {e}")
        return False


def analyze_frames():
    global body_analyzer, micro_analyzer
    if not body_analyzer or not micro_analyzer:
        logging.warning("分析器未初始化，无法启动分析线程")
        return

    logging.info("启动帧分析线程")
    while True:
        try:
            if not recording_flag.empty():
                frame = frame_queue.get(timeout=1)
                if frame is None:
                    logging.info("收到终止信号，退出分析线程")
                    break

                body_result = body_analyzer.analyze_frame(frame)
                micro_result = micro_analyzer.analyze_frame(frame)

                if not isinstance(body_result, dict):
                    body_result = {"状态": "无效结果", "得分": 0, "描述": "无效肢体分析"}
                if not isinstance(micro_result, dict):
                    micro_result = {"状态": "无效结果", "得分": 0, "描述": "无效表情分析"}

                frame_desc = f"{body_analyzer.get_frame_description(frame)}; {micro_analyzer.get_frame_description(frame)}"
                from streamlit import session_state as st_session_state
                st_session_state.frame_descriptions.append(frame_desc)

                result_queue.put({
                    "timestamp": cv2.getTickCount(),
                    "body": body_result,
                    "micro": micro_result,
                    "description": frame_desc
                })

                frame_queue.task_done()
            else:
                import time
                time.sleep(0.1)
        except Exception as e:
            logging.error(f"帧分析线程异常: {e}")
            continue