"""
摄像头视频采集线程
修复版 - 增强资源释放
"""

import cv2
import queue
import threading
import time
from utils.config import FRAME_WIDTH, FRAME_HEIGHT

class CameraThread(threading.Thread):
    def __init__(self, frame_queue, stop_event):
        super().__init__()
        self.frame_queue = frame_queue
        self.stop_event = stop_event
        self.cap = None
        self.daemon = True
        self.camera_id = 0
        self.is_running = False

    def run(self):
        self.is_running = True
        print("[摄像头] 正在初始化...")

        # 尝试多个摄像头索引
        camera_ids = [0, 1]
        for cam_id in camera_ids:
            try:
                # 强制使用DirectShow后端
                if hasattr(cv2, 'CAP_DSHOW'):
                    self.cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
                else:
                    self.cap = cv2.VideoCapture(cam_id)

                if self.cap and self.cap.isOpened():
                    print(f"[摄像头] 成功打开摄像头 {cam_id}")
                    self.camera_id = cam_id
                    break
            except Exception as e:
                print(f"[摄像头] 尝试打开摄像头 {cam_id} 失败: {e}")
                continue

        if not self.cap or not self.cap.isOpened():
            print("[摄像头] 错误：无法打开任何摄像头")
            self.is_running = False
            return

        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        print(f"[摄像头] 初始化成功，分辨率: {FRAME_WIDTH}x{FRAME_HEIGHT}")

        while not self.stop_event.is_set() and self.is_running:
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    # 队列管理
                    if self.frame_queue.qsize() > 1:
                        try:
                            self.frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.frame_queue.put(frame)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"[摄像头] 读取错误: {e}")
                time.sleep(0.1)

        # 释放摄像头资源
        self._release_camera()
        self.is_running = False

    def _release_camera(self):
        """释放摄像头资源"""
        try:
            if self.cap:
                # 清空缓冲区
                for _ in range(5):
                    self.cap.grab()

                self.cap.release()
                self.cap = None
                print(f"[摄像头] 已释放摄像头 {self.camera_id}")
        except Exception as e:
            print(f"[摄像头] 释放资源时出错: {e}")

    def stop(self):
        """停止摄像头线程"""
        print("[摄像头] 正在停止...")
        self.stop_event.set()
        self.is_running = False
        self._release_camera()