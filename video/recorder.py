import cv2
import numpy as np
import time
import os
import queue
from datetime import datetime
import threading


class VideoRecorder:
    def __init__(self):
        self.cap = None
        self.out = None
        self.is_recording = False
        self.frame_count = 0
        self.fps = 25.0  # 提高默认帧率至25fps，使视频更流畅
        self.width = 640
        self.height = 480
        self.start_time = None  # 录制开始时间
        self.previous_frame = None  # 上一帧备份（用于补帧）
        self.last_successful_read = time.time()
        self.error_count = 0  # 连续错误计数
        self.target_frame_interval = 1.0 / 25.0  # 目标帧间隔，默认25fps
        self.last_frame_time = 0  # 上一帧的时间戳

        # 优化相关
        self.frame_buffer = queue.Queue(maxsize=3)  # 帧缓冲区
        self.capture_thread = None
        self.capture_running = False
        self.next_frame_time = 0
        self.written_frames = 0  # 已写入的帧数
        self.frame_cache = None  # 帧缓存

    def initialize_camera(self):
        try:
            if self.cap:
                self.cap.release()

            # 多次尝试打开摄像头
            for i in range(3):
                self.cap = cv2.VideoCapture(0)
                if self.cap.isOpened():
                    break
                time.sleep(0.5)

            if not self.cap or not self.cap.isOpened():
                return False, "无法打开摄像头"

            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 最小缓冲区

            # 设置摄像头为最高性能模式
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            # 获取实际参数
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if actual_fps > 0:
                self.fps = actual_fps
                self.target_frame_interval = 1.0 / self.fps

            return True, f"摄像头初始化成功 ({self.width}x{self.height}, {self.fps:.1f}fps)"

        except Exception as e:
            return False, f"摄像头初始化失败: {str(e)}"

    def _capture_frames_thread(self):
        """后台线程持续捕获帧"""
        while self.capture_running:
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    # 如果缓冲区满了，丢弃最老的帧
                    try:
                        self.frame_buffer.put_nowait((time.time(), frame.copy()))
                    except queue.Full:
                        try:
                            self.frame_buffer.get_nowait()  # 移除最老的帧
                            self.frame_buffer.put_nowait((time.time(), frame.copy()))
                        except queue.Empty:
                            pass

                    self.frame_cache = frame.copy()
                    self.error_count = 0
                else:
                    self.error_count += 1

            except Exception as e:
                self.error_count += 1

            # 控制捕获频率，避免过度占用CPU
            time.sleep(0.01)

    def start_recording(self, output_path):
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.out = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))

            if not self.out.isOpened():
                return False, "无法创建视频文件"

            self.is_recording = True
            self.frame_count = 0
            self.written_frames = 0
            self.start_time = time.time()
            self.next_frame_time = self.start_time
            self.last_successful_read = self.start_time
            self.error_count = 0
            self.previous_frame = None
            self.frame_cache = None

            # 启动后台捕获线程
            self.capture_running = True
            self.capture_thread = threading.Thread(target=self._capture_frames_thread)
            self.capture_thread.daemon = True
            self.capture_thread.start()

            # 预热：等待第一帧
            for _ in range(10):
                if self.frame_cache is not None:
                    break
                time.sleep(0.1)

            return True, "录制已开始"

        except Exception as e:
            return False, f"录制启动失败: {str(e)}"

    def record_frame(self):
        """高效的帧录制，减少阻塞"""
        if not self.is_recording or not self.cap:
            return False, None

        current_time = time.time()

        # 检查是否到了写入下一帧的时间
        if current_time < self.next_frame_time:
            # 还没到时间，返回缓存的帧用于显示
            if self.frame_cache is not None:
                return True, self.frame_cache
            else:
                return False, None

        # 获取最新的帧
        frame_to_write = None
        frame_timestamp = 0

        # 尝试从缓冲区获取最新帧
        try:
            while not self.frame_buffer.empty():
                frame_timestamp, frame_to_write = self.frame_buffer.get_nowait()
        except queue.Empty:
            pass

        # 如果没有新帧，使用缓存的帧
        if frame_to_write is None:
            if self.frame_cache is not None:
                frame_to_write = self.frame_cache
            else:
                # 创建黑色帧
                frame_to_write = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                cv2.putText(frame_to_write, "Waiting for camera...",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # 写入帧
        if frame_to_write is not None:
            self.out.write(frame_to_write)
            self.written_frames += 1
            self.frame_count += 1

            # 更新下一帧时间
            self.next_frame_time += self.target_frame_interval

            # 如果落后太多，追赶时间
            if self.next_frame_time < current_time - 0.1:
                self.next_frame_time = current_time + self.target_frame_interval

            self.previous_frame = frame_to_write
            return True, frame_to_write

        return False, None

    def stop_recording(self):
        """停止录制并返回成功状态和帧数量"""
        self.is_recording = False

        # 停止后台捕获线程
        if self.capture_running:
            self.capture_running = False
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=1.0)

        # 确保写入足够的帧以匹配录制时间
        if self.out and self.start_time:
            actual_duration = time.time() - self.start_time
            expected_frames = int(actual_duration * self.fps)

            # 如果帧数不足，用最后一帧补齐
            while self.written_frames < expected_frames and self.previous_frame is not None:
                self.out.write(self.previous_frame)
                self.written_frames += 1
                self.frame_count += 1

        if self.out:
            self.out.release()
            self.out = None

        if self.cap:
            self.cap.release()
            self.cap = None

        # 清理缓冲区
        while not self.frame_buffer.empty():
            try:
                self.frame_buffer.get_nowait()
            except queue.Empty:
                break

        return True, self.frame_count


# 视频处理队列和线程相关
frame_queue = queue.Queue(maxsize=10)
result_queue = queue.Queue(maxsize=10)
recording_flag = queue.Queue(maxsize=1)