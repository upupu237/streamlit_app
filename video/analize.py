import cv2
import numpy as np
import time
import math
import mediapipe as mp
from collections import deque
from fer import FER


class BodyLanguageAnalyzer:
    def __init__(self):
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.face = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.eye_aspect_ratio_threshold = 0.2
        self.eye_aspect_ratio_consecutive_frames = 3
        self.counter = 0
        self.total_blinks = 0
        self.last_blink_time = 0
        self.blink_rate = 0
        self.start_time = time.time()

        self.slouch_threshold = 0.15
        self.mouth_aspect_ratio_threshold = 0.35
        self.smile_threshold = 0.18

        self.arm_angle_history = deque(maxlen=10)

    def analyze_frame(self, frame):
        analysis_result = {
            "status": "未检测到人体",
            "pose": None,
            "arms": None,
            "posture": None,
            "facial": None,
            "summary": None  # 新增总览字段，方便打印
        }

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_results = self.pose.process(rgb_frame)

        if pose_results.pose_landmarks:
            analysis_result["status"] = "检测到人体"

            pose_analysis = self._analyze_pose(pose_results.pose_landmarks)
            arms_analysis = self._analyze_arms(pose_results.pose_landmarks)
            posture_analysis = self._analyze_posture(pose_results.pose_landmarks)

            analysis_result["pose"] = pose_analysis
            analysis_result["arms"] = arms_analysis
            analysis_result["posture"] = posture_analysis

            face_results = self.face.process(rgb_frame)
            facial_analysis = None
            if face_results.multi_face_landmarks:
                facial_analysis = self._analyze_facial(face_results.multi_face_landmarks[0])
            analysis_result["facial"] = facial_analysis

            # 生成总结描述
            summary = self._generate_summary(pose_analysis, arms_analysis, posture_analysis, facial_analysis)
            analysis_result["summary"] = summary

        return analysis_result

    def _analyze_pose(self, landmarks):
        left_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        shoulder_width = abs(left_shoulder.x - right_shoulder.x)

        # 简单判断肩膀状态（示例阈值）
        if shoulder_width > 0.17:
            shoulder_state = "姿态良好，自然大方"
        elif shoulder_width > 0.12:
            shoulder_state = "姿态一般，稍显紧张"
        else:
            shoulder_state = "姿态较差，肩膀内收"

        return {
            "shoulder_width": shoulder_width,
            "shoulder_state": shoulder_state
        }

    def _analyze_arms(self, landmarks):
        left_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        left_elbow = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_ELBOW]
        left_wrist = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_WRIST]

        right_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        right_elbow = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_ELBOW]
        right_wrist = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]

        left_arm_angle = self._calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_arm_angle = self._calculate_angle(right_shoulder, right_elbow, right_wrist)

        self.arm_angle_history.append((left_arm_angle, right_arm_angle))

        def arm_position(angle):
            if angle > 140:
                return "放下"
            elif angle > 100:
                return "自然弯曲"
            else:
                return "举起"

        left_pos = arm_position(left_arm_angle)
        right_pos = arm_position(right_arm_angle)

        # 手臂建议示例（如果手臂举得过高）
        arm_suggestion = ""
        if left_arm_angle < 50 or right_arm_angle < 50:
            arm_suggestion = "手臂举起过高，可能显得过于强势"
        elif left_arm_angle > 160 and right_arm_angle > 160:
            arm_suggestion = "手臂自然放下，状态良好"
        else:
            arm_suggestion = "手臂动作协调，自然大方"

        return {
            "left_arm_angle": left_arm_angle,
            "right_arm_angle": right_arm_angle,
            "left_arm_position": left_pos,
            "right_arm_position": right_pos,
            "arm_suggestion": arm_suggestion
        }

    def _calculate_angle(self, a, b, c):
        ax, ay = a.x, a.y
        bx, by = b.x, b.y
        cx, cy = c.x, c.y

        angle = math.degrees(math.atan2(cy - by, cx - bx) - math.atan2(ay - by, ax - bx))
        if angle < 0:
            angle += 360
        if angle > 180:
            angle = 360 - angle
        return angle

    def _analyze_posture(self, landmarks):
        left_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_HIP]

        shoulder_center = ((left_shoulder.x + right_shoulder.x) / 2, (left_shoulder.y + right_shoulder.y) / 2)
        hip_center = ((left_hip.x + right_hip.x) / 2, (left_hip.y + right_hip.y) / 2)

        angle = math.degrees(math.atan2(hip_center[1] - shoulder_center[1], hip_center[0] - shoulder_center[0]))

        # 坐姿判断（示例阈值）
        if abs(angle) < self.slouch_threshold:
            posture_state = "良好"
        else:
            posture_state = "不良 (坐姿不端正，可能有弯腰驼背现象，建议坐直)"

        return {"angle": angle, "posture_state": posture_state}

    def _analyze_facial(self, landmarks):
        left_eye = [landmarks.landmark[i] for i in [159, 145, 133, 153, 157, 158]]
        right_eye = [landmarks.landmark[i] for i in [386, 374, 362, 403, 380, 381]]
        mouth = [landmarks.landmark[i] for i in [13, 14, 61, 291, 0]]

        left_ear = self._eye_aspect_ratio(left_eye)
        right_ear = self._eye_aspect_ratio(right_eye)
        ear = (left_ear + right_ear) / 2.0

        blink_detected = False
        if ear < self.eye_aspect_ratio_threshold:
            self.counter += 1
        else:
            if self.counter >= self.eye_aspect_ratio_consecutive_frames:
                self.total_blinks += 1
                blink_detected = True
                current_time = time.time()
                time_since_last_blink = current_time - self.last_blink_time
                if time_since_last_blink > 0:
                    self.blink_rate = 60.0 / time_since_last_blink
                    self.last_blink_time = current_time
            self.counter = 0

        elapsed_time = time.time() - self.start_time
        blinks_per_minute = (self.total_blinks / elapsed_time) * 60 if elapsed_time > 0 else 0

        # 眨眼状态描述
        if blinks_per_minute < 8:
            blink_status = "眨眼次数过少，可能需要放松眼睛"
        elif blinks_per_minute > 30:
            blink_status = "眨眼频率过高，可能紧张或疲劳"
        else:
            blink_status = "眨眼频率正常"

        expression = self._classify_expression(landmarks)

        smile_ratio = self._smile_ratio(mouth)

        return {
            "total_blinks": self.total_blinks,
            "blinks_per_minute": blinks_per_minute,
            "blink_status": blink_status,
            "expression": expression,
            "smile_ratio": smile_ratio
        }

    def _classify_expression(self, landmarks):
        left_eye = [landmarks.landmark[i] for i in [159, 145, 133, 153, 157, 158]]
        right_eye = [landmarks.landmark[i] for i in [386, 374, 362, 403, 380, 381]]
        left_eyebrow = [landmarks.landmark[i] for i in [27, 28, 29, 30, 105]]
        right_eyebrow = [landmarks.landmark[i] for i in [257, 258, 259, 260, 334]]
        mouth = [landmarks.landmark[i] for i in [13, 14, 61, 291, 0, 17, 314, 146]]

        left_ear = self._eye_aspect_ratio(left_eye)
        right_ear = self._eye_aspect_ratio(right_eye)
        ear = (left_ear + right_ear) / 2.0

        left_eyebrow_height = left_eyebrow[2].y - left_eye[0].y
        right_eyebrow_height = right_eyebrow[2].y - right_eye[0].y
        eyebrow_height = (left_eyebrow_height + right_eyebrow_height) / 2.0

        mouth_open = np.linalg.norm(np.array([mouth[0].x, mouth[0].y]) - np.array([mouth[1].x, mouth[1].y]))
        mouth_width = np.linalg.norm(np.array([mouth[2].x, mouth[2].y]) - np.array([mouth[3].x, mouth[3].y]))
        mar = mouth_open / mouth_width if mouth_width > 0 else 0

        left_smile = abs(mouth[2].y - mouth[4].y)
        right_smile = abs(mouth[3].y - mouth[4].y)
        smile_ratio = (left_smile + right_smile) / (2.0 * mouth_width) if mouth_width > 0 else 0

        if smile_ratio > self.smile_threshold:
            return "微笑"
        elif mar > 0.3:
            return "惊讶" if eyebrow_height > 0.03 else "说话"
        elif ear < 0.18:
            return "思考" if eyebrow_height > 0.02 else "紧张"
        elif eyebrow_height > 0.04:
            return "感兴趣"
        else:
            return "中性"

    def _eye_aspect_ratio(self, eye):
        A = np.linalg.norm(np.array([eye[1].x, eye[1].y]) - np.array([eye[5].x, eye[5].y]))
        B = np.linalg.norm(np.array([eye[2].x, eye[2].y]) - np.array([eye[4].x, eye[4].y]))
        C = np.linalg.norm(np.array([eye[0].x, eye[0].y]) - np.array([eye[3].x, eye[3].y]))
        return (A + B) / (2.0 * C)

    def _smile_ratio(self, mouth):
        left_smile = abs(mouth[2].y - mouth[4].y)
        right_smile = abs(mouth[3].y - mouth[4].y)
        mouth_width = abs(mouth[2].x - mouth[3].x)
        return (left_smile + right_smile) / (2.0 * mouth_width)

    def calculate_arm_smoothness(self):
        if len(self.arm_angle_history) < 2:
            return 70

        angle_diffs = []
        for i in range(1, len(self.arm_angle_history)):
            prev_left, prev_right = self.arm_angle_history[i - 1]
            curr_left, curr_right = self.arm_angle_history[i]
            left_diff = abs(curr_left - prev_left)
            right_diff = abs(curr_right - prev_right)
            angle_diffs.append((left_diff + right_diff) / 2)

        std_dev = np.std(angle_diffs)
        return max(0, min(100, 100 - std_dev * 2.5))

    def _generate_summary(self, pose_analysis, arms_analysis, posture_analysis, facial_analysis):
        if not all([pose_analysis, arms_analysis, posture_analysis, facial_analysis]):
            return "信息不足，无法生成完整分析"

        summary = (
            f"姿态分析:\n"
            f"  肩膀状态: {pose_analysis['shoulder_state']}\n"
            f"  手臂状态: 左-{arms_analysis['left_arm_position']}, 右-{arms_analysis['right_arm_position']}\n"
            f"  手臂建议: {arms_analysis['arm_suggestion']}\n"
            f"  坐姿状态: {posture_analysis['posture_state']}\n"
            f"  眨眼频率: {facial_analysis['blinks_per_minute']:.1f} 次/分钟\n"
            f"  眨眼状态: {facial_analysis['blink_status']}\n"
            f"  检测到情绪: {facial_analysis['expression']} (置信度: N/A)\n"
        )
        return summary


class MicroExpressionAnalyzer:
    def __init__(self):
        self.detector = FER(mtcnn=True)
        self.emotion_map = {
            'neutral': '中性',
            'happy': '快乐',
            'sad': '悲伤',
            'surprise': '惊讶',
            'fear': '恐惧',
            'disgust': '厌恶',
            'angry': '愤怒',
            'contempt': '轻蔑'
        }
        self.emotion_weights = {
            'happy': 1.4,
            'neutral': 0.9,
            'surprise': 1.2,
            'sad': 0.6,
            'fear': 0.5,
            'disgust': 0.4,
            'angry': 0.3,
            'contempt': 0.3
        }

    def analyze_frame(self, frame):
        results = self.detector.detect_emotions(frame)
        if not results:
            return {"dominant_emotion": None, "confidence": 0}

        emotions = results[0]["emotions"]
        dominant_emotion = max(emotions, key=emotions.get)
        confidence = emotions[dominant_emotion]

        return {
            "dominant_emotion": self.emotion_map.get(dominant_emotion, dominant_emotion),
            "confidence": confidence,
            "weight": self.emotion_weights.get(dominant_emotion, 1.0)
        }
