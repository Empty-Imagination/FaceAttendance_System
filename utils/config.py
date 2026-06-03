"""
全局配置参数
优化版 - 调整识别阈值
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据存储目录
DATA_DIR = BASE_DIR / 'data'
FACES_DIR = DATA_DIR / 'faces'
MODEL_DIR = DATA_DIR / 'model'
DB_PATH = DATA_DIR / 'attendance.db'

# 确保目录存在
for d in [FACES_DIR, MODEL_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Haar级联分类器路径
HAAR_CASCADE_PATH = BASE_DIR / 'assets' / 'haarcascade_frontalface_default.xml'

# 摄像头配置
CAMERA_ID = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ========== 人脸检测参数优化 ==========
FACE_SCALE_FACTOR = 1.1      # 图像缩放比例
FACE_MIN_NEIGHBORS = 5       # 最小相邻矩形数
FACE_MIN_SIZE = (60, 60)     # 最小人脸尺寸（降低以便检测更小人脸）

# ========== 图像预处理 ==========
TARGET_IMAGE_SIZE = (100, 100)   # 统一缩放尺寸

# ========== LBPH算法参数优化 ==========
LBPH_RADIUS = 1
LBPH_NEIGHBORS = 8
LBPH_GRID_X = 8      # 改回8x8，提高特征维度，提升识别准确率
LBPH_GRID_Y = 8

# ========== 置信度阈值调整（关键！）==========
# 原阈值65（值越小越严格，越大越宽松）
# 调整为85，让识别更宽松，更容易识别出来
LBPH_THRESHOLD = 85.0

# ========== 注册参数 ==========
REGISTER_FACE_COUNT = 8    # 增加到8张，提高模型质量

# ========== 防重复打卡 ==========
ATTENDANCE_DUPLICATE_INTERVAL = 300   # 5分钟