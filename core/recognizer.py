"""
LBPH人脸识别器封装
修复版 - 确保标签映射正确
"""

import cv2
import numpy as np
import json
from pathlib import Path
from utils.config import (
    MODEL_DIR, LBPH_RADIUS, LBPH_NEIGHBORS,
    LBPH_GRID_X, LBPH_GRID_Y, LBPH_THRESHOLD,
    TARGET_IMAGE_SIZE
)


class LBPHRecognizer:
    def __init__(self):
        self.model_path = MODEL_DIR / 'lbph_model.yml'
        self.label_map_path = MODEL_DIR / 'label_map.json'
        self.recognizer = None
        self.label_map = {}  # 格式: {"整数标签": "学号"}
        self.threshold = LBPH_THRESHOLD
        self.load_model()

    def load_model(self):
        """加载已训练的模型和标签映射"""
        if self.model_path.exists():
            self.recognizer = cv2.face.LBPHFaceRecognizer_create(
                radius=LBPH_RADIUS,
                neighbors=LBPH_NEIGHBORS,
                grid_x=LBPH_GRID_X,
                grid_y=LBPH_GRID_Y,
                threshold=self.threshold
            )
            self.recognizer.read(str(self.model_path))

            if self.label_map_path.exists():
                with open(self.label_map_path, 'r', encoding='utf-8') as f:
                    self.label_map = json.load(f)
                print(f"[识别器] 加载模型成功，共 {len(self.label_map)} 人")
                print(f"[识别器] 标签映射: {self.label_map}")
            else:
                self.label_map = {}
                print("[识别器] 未找到标签映射文件")
        else:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create(
                radius=LBPH_RADIUS,
                neighbors=LBPH_NEIGHBORS,
                grid_x=LBPH_GRID_X,
                grid_y=LBPH_GRID_Y,
                threshold=self.threshold
            )
            self.label_map = {}
            print("[识别器] 未找到模型，创建新的识别器")

    def preprocess_face(self, face_image):
        """人脸图像预处理"""
        if len(face_image.shape) == 3:
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_image

        equalized = cv2.equalizeHist(gray)
        resized = cv2.resize(equalized, TARGET_IMAGE_SIZE)

        return resized

    def predict(self, face_image):
        """
        预测人脸身份
        返回 (student_id, confidence)
        """
        if self.recognizer is None or len(self.label_map) == 0:
            print("[识别器] 识别器未初始化或无标签映射")
            return None, 999

        # 预处理
        processed_face = self.preprocess_face(face_image)

        # 预测
        label, confidence = self.recognizer.predict(processed_face)

        # 将整数标签转换为学号
        label_str = str(label)
        if label_str in self.label_map:
            student_id = self.label_map[label_str]
            print(f"[识别器] 预测结果: 标签={label}, 学号={student_id}, 置信度={confidence:.2f}")
            return student_id, confidence
        else:
            print(f"[识别器] 未知标签: {label}, 置信度={confidence:.2f}")
            return None, confidence

    def update_model(self, faces, labels):
        """增量训练"""
        if self.recognizer is None:
            return
        if len(faces) > 0:
            processed_faces = [self.preprocess_face(f) for f in faces]
            self.recognizer.update(processed_faces, np.array(labels))
            self.save_model()
            print(f"[识别器] 增量更新完成，新增 {len(faces)} 张图片")

    def save_model(self):
        """保存模型和标签映射"""
        if self.recognizer is not None:
            self.recognizer.save(str(self.model_path))
            with open(self.label_map_path, 'w', encoding='utf-8') as f:
                json.dump(self.label_map, f, ensure_ascii=False, indent=2)
            print(f"[识别器] 模型已保存: {self.model_path}")
            print(f"[识别器] 标签映射已保存: {self.label_map}")

    def set_threshold(self, threshold):
        """动态调整阈值"""
        self.threshold = threshold
        if self.recognizer is not None:
            self.recognizer.setThreshold(threshold)
        print(f"[识别器] 阈值已调整为: {threshold}")

    def get_all_students(self):
        """获取所有已注册学生"""
        return list(self.label_map.values())