"""
辅助工具函数：图像质量评估、防重复打卡检查等
"""

import cv2
import numpy as np
import json
from datetime import datetime, timedelta
from utils.config import ATTENDANCE_DUPLICATE_INTERVAL
from core.database import get_last_attendance_time


def is_image_quality_ok(face_roi):
    """
    判断人脸图像质量是否合格
    :param face_roi: 灰度人脸图像
    :return: (bool, str) 是否合格，不合格原因
    """
    # 1. 清晰度检测（Laplacian方差）
    laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
    if laplacian_var < 50:
        return False, f"图像模糊 (Laplacian方差={laplacian_var:.1f} < 50)"

    # 2. 亮度检测（平均灰度）
    mean_brightness = np.mean(face_roi)
    if mean_brightness < 40 or mean_brightness > 210:
        return False, f"光照异常 (平均亮度={mean_brightness:.1f})"

    return True, "合格"


def is_duplicate_attendance(student_id):
    """
    检查该学生是否在防重复间隔内已打卡
    :param student_id: 学号
    :return: True=已打卡（需跳过），False=未打卡（可记录）
    """
    last_time = get_last_attendance_time(student_id)
    if last_time is None:
        return False
    # 计算时间差
    now = datetime.now()
    delta = now - last_time
    return delta.total_seconds() < ATTENDANCE_DUPLICATE_INTERVAL


def load_label_map(json_path):
    """加载标签映射文件（整数标签 -> 学号）"""
    with open(json_path, 'r') as f:
        return json.load(f)


def save_label_map(label_map, json_path):
    """保存标签映射文件"""
    with open(json_path, 'w') as f:
        json.dump(label_map, f)


def format_timestamp(timestamp):
    """格式化时间戳用于显示"""
    return timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else ''