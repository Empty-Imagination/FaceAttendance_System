"""
模型训练模块
修复版 - 确保标签分配正确
"""

import cv2
import numpy as np
from pathlib import Path
from utils.config import FACES_DIR, TARGET_IMAGE_SIZE
from core.recognizer import LBPHRecognizer
import logging
from PyQt5.QtCore import QObject, pyqtSignal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainSignals(QObject):
    """训练信号类"""
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool)


class ModelTrainer:
    def __init__(self):
        self.recognizer = LBPHRecognizer()
        self.signals = TrainSignals()

    def preprocess_training_image(self, img):
        """训练图像的预处理"""
        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            equalized = cv2.equalizeHist(gray)

            # CLAHE 增强
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(equalized)

            resized = cv2.resize(enhanced, TARGET_IMAGE_SIZE)
            return resized
        except Exception as e:
            logger.error(f"图像预处理失败: {e}")
            return None

    def train_full(self, progress_callback=None, status_callback=None):
        """全量训练"""
        try:
            if status_callback:
                status_callback("正在扫描人脸图片...")
            if self.signals:
                self.signals.status.emit("正在扫描人脸图片...")

            face_files = list(FACES_DIR.glob('*.jpg'))

            if not face_files:
                error_msg = "没有找到任何人脸图片，请先注册"
                logger.warning(error_msg)
                if status_callback:
                    status_callback(error_msg)
                if self.signals:
                    self.signals.status.emit(error_msg)
                    self.signals.finished.emit(False)
                return False

            if status_callback:
                status_callback(f"找到 {len(face_files)} 张图片，开始处理...")

            faces = []
            labels = []

            # 建立学号到整数标签的映射
            student_to_label = {}
            next_label = 0

            total = len(face_files)
            success_count = 0

            for idx, img_path in enumerate(face_files):
                if progress_callback:
                    progress_callback(idx + 1, total)
                if self.signals:
                    self.signals.progress.emit(idx + 1, total)

                # 从文件名提取学号（格式：学号_序号.jpg）
                filename = img_path.stem
                parts = filename.split('_')
                if len(parts) >= 1:
                    student_id = parts[0]
                else:
                    logger.warning(f"文件名格式错误: {img_path.name}")
                    continue

                if not student_id:
                    logger.warning(f"无法提取学号: {img_path.name}")
                    continue

                # 为每个学生分配唯一的整数标签
                if student_id not in student_to_label:
                    student_to_label[student_id] = next_label
                    next_label += 1
                    print(f"[训练] 分配标签: {student_id} -> {student_to_label[student_id]}")

                # 读取图片
                img = cv2.imread(str(img_path))
                if img is None:
                    logger.warning(f"无法读取图片: {img_path}")
                    continue

                processed_img = self.preprocess_training_image(img)
                if processed_img is None:
                    logger.warning(f"预处理失败: {img_path}")
                    continue

                faces.append(processed_img)
                labels.append(student_to_label[student_id])
                success_count += 1

            if len(faces) == 0:
                error_msg = "没有有效的人脸图片"
                if status_callback:
                    status_callback(error_msg)
                return False

            if status_callback:
                status_callback(f"正在训练模型，共 {len(student_to_label)} 人，{len(faces)} 张图片...")

            # 训练模型
            self.recognizer.recognizer.train(faces, np.array(labels))

            # 保存标签映射（整数标签 -> 学号）
            self.recognizer.label_map = {str(v): k for k, v in student_to_label.items()}
            self.recognizer.save_model()

            success_msg = f"训练完成！共 {len(student_to_label)} 人，{len(faces)} 张图片"
            logger.info(success_msg)
            print(f"[训练] 最终标签映射: {self.recognizer.label_map}")

            if status_callback:
                status_callback(success_msg)
            if self.signals:
                self.signals.status.emit(success_msg)
                self.signals.finished.emit(True)

            return True

        except Exception as e:
            error_msg = f"训练出错: {str(e)}"
            logger.error(error_msg)
            if status_callback:
                status_callback(error_msg)
            if self.signals:
                self.signals.status.emit(error_msg)
                self.signals.finished.emit(False)
            return False