"""
人脸检测模块
优化版 - 增强图像预处理
"""

import cv2
import os
import tempfile
import shutil
import numpy as np
from utils.config import HAAR_CASCADE_PATH


class FaceDetector:
    def __init__(self):
        cascade_path_str = str(HAAR_CASCADE_PATH)
        self.cascade = cv2.CascadeClassifier(cascade_path_str)

        if self.cascade.empty() and os.path.exists(cascade_path_str):
            temp_dir = tempfile.gettempdir()
            temp_xml = os.path.join(temp_dir, 'haarcascade_frontalface_default.xml')
            try:
                shutil.copy2(cascade_path_str, temp_xml)
                self.cascade = cv2.CascadeClassifier(temp_xml)
            except:
                pass

        if self.cascade.empty():
            opencv_path = r'C:\Users\LENOVO\AppData\Local\Programs\Python\Python311\Lib\site-packages\cv2\data\haarcascade_frontalface_default.xml'
            if os.path.exists(opencv_path):
                self.cascade = cv2.CascadeClassifier(opencv_path)

        if self.cascade.empty():
            raise FileNotFoundError("无法加载Haar cascade文件")

    def preprocess_image(self, image_gray):
        """
        增强图像预处理
        包括：直方图均衡化、高斯滤波、对比度增强
        """
        # 1. 直方图均衡化（增强对比度）
        equalized = cv2.equalizeHist(image_gray)

        # 2. 高斯滤波（去噪）
        blurred = cv2.GaussianBlur(equalized, (3, 3), 0)

        # 3. CLAHE 自适应直方图均衡化（比普通均衡化更好）
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)

        return enhanced

    def detect(self, image_gray, fast_mode=True):
        """增强版人脸检测"""
        # 预处理
        processed = self.preprocess_image(image_gray)

        if fast_mode:
            height, width = processed.shape
            scale = 240 / max(height, width)

            if scale < 1:
                new_width = int(width * scale)
                new_height = int(height * scale)
                small_img = cv2.resize(processed, (new_width, new_height))

                faces = self.cascade.detectMultiScale(
                    small_img,
                    scaleFactor=1.1,
                    minNeighbors=4,      # 降低要求，提高检出率
                    minSize=(50, 50),    # 更小人脸
                    flags=cv2.CASCADE_SCALE_IMAGE
                )

                if len(faces) > 0:
                    faces = [(int(x/scale), int(y/scale),
                             int(w/scale), int(h/scale)) for (x,y,w,h) in faces]
            else:
                faces = self.cascade.detectMultiScale(
                    processed,
                    scaleFactor=1.1,
                    minNeighbors=4,
                    minSize=(50, 50),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
        else:
            faces = self.cascade.detectMultiScale(
                processed,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(50, 50),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

        return faces

    def detect_largest_face(self, image_gray):
        """返回最大的人脸（用于注册时）"""
        processed = self.preprocess_image(image_gray)
        faces = self.detect(processed, fast_mode=False)
        if len(faces) == 0:
            return None
        return max(faces, key=lambda rect: rect[2] * rect[3])