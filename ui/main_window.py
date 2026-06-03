"""
主窗口：实时摄像头预览、考勤控制、状态显示
修复版 - 正确识别不同人脸
"""

import sys
import cv2
import numpy as np
import queue
import threading
import time
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 用于中文显示
from PIL import Image, ImageDraw, ImageFont

from core.camera import CameraThread
from core.face_detector import FaceDetector
from core.recognizer import LBPHRecognizer
from core.database import add_attendance_record, get_student_by_id
from utils.helper import is_duplicate_attendance
from utils.config import TARGET_IMAGE_SIZE
from ui.register_dialog import RegisterDialog
from ui.query_dialog import QueryDialog
from ui.manage_dialog import ManageDialog


class DisplayThread(QThread):
    """独立的显示线程"""
    update_pixmap = pyqtSignal(QPixmap)

    def __init__(self, display_queue, stop_event):
        super().__init__()
        self.display_queue = display_queue
        self.stop_event = stop_event
        self.daemon = True

    def run(self):
        while not self.stop_event.is_set():
            try:
                frame = None
                while not self.display_queue.empty():
                    try:
                        frame = self.display_queue.get_nowait()
                    except queue.Empty:
                        break

                if frame is not None:
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)
                    self.update_pixmap.emit(pixmap)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"[显示线程] 错误: {e}")
                time.sleep(0.01)


class RecognitionSuccessDialog(QDialog):
    """识别成功确认对话框"""

    def __init__(self, name, student_id, confidence, is_recorded=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("考勤成功")
        self.setModal(True)
        self.setFixedSize(400, 320)

        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
                border-radius: 15px;
            }
            QLabel {
                color: #263238;
                font-size: 14px;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                color: white;
                min-width: 120px;
            }
            QPushButton#continueBtn {
                background-color: #4CAF50;
            }
            QPushButton#continueBtn:hover {
                background-color: #45a049;
            }
            QPushButton#stopBtn {
                background-color: #f44336;
            }
            QPushButton#stopBtn:hover {
                background-color: #da190b;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 成功图标
        icon_label = QLabel("✅")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 成功信息
        info_label = QLabel("考勤成功！")
        info_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # 人员信息
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detail_label = QLabel(
            f"<b>姓名：</b>{name}<br>"
            f"<b>学号：</b>{student_id}<br>"
            f"<b>置信度：</b>{confidence:.1f}<br>"
            f"<b>时间：</b>{current_time}"
        )
        detail_label.setStyleSheet("background-color: white; padding: 15px; border-radius: 10px;")
        detail_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(detail_label)

        # 是否记录考勤的提示
        if not is_recorded:
            warn_label = QLabel("⚠️ 该学生5分钟内已打卡，本次未重复记录")
            warn_label.setStyleSheet("color: #FF9800; font-size: 12px;")
            warn_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(warn_label)

        # 询问信息
        ask_label = QLabel("是否继续识别下一个人？")
        ask_label.setStyleSheet("font-size: 14px; color: #666;")
        ask_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(ask_label)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        self.continue_btn = QPushButton("继续识别")
        self.continue_btn.setObjectName("continueBtn")
        self.continue_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.continue_btn)

        self.stop_btn = QPushButton("停止考勤")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)


class NoFaceDetectedDialog(QDialog):
    """未检测到人脸提示对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("提示")
        self.setModal(True)
        self.setFixedSize(350, 200)

        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
                border-radius: 15px;
            }
            QLabel {
                color: #263238;
                font-size: 14px;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: #2196F3;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 警告图标
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 提示信息
        info_label = QLabel("识别失败")
        info_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF9800;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        msg_label = QLabel("连续5秒未检测到人脸！\n请确保人脸正对摄像头，且光线充足。")
        msg_label.setStyleSheet("color: #666;")
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # 按钮
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        layout.addWidget(self.ok_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    recognition_success = pyqtSignal(str, str, float, bool)
    no_face_detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("人脸识别考勤系统 · 智慧校园版")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: #2196F3;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
            QLabel {
                color: #263238;
                font-size: 13px;
            }
            QStatusBar {
                background-color: #E3F2FD;
                color: #0D47A1;
                font-size: 12px;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px 0 10px;
                color: #2196F3;
            }
        """)

        # 初始化组件
        self.detector = FaceDetector()
        self.recognizer = LBPHRecognizer()

        # 线程控制
        self.frame_queue = queue.Queue(maxsize=2)
        self.display_queue = queue.Queue(maxsize=2)
        self.stop_event = threading.Event()
        self.display_stop_event = threading.Event()
        self.camera_thread = None
        self.recognition_running = False
        self.recognition_paused = False

        # 性能统计
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0

        # 人脸检测计时器
        self._last_face_detect_time = None
        self._no_face_timer_started = False

        # 初始化中文字体
        self._init_font()

        # 界面
        self.init_ui()

        # 启动显示线程
        self.display_thread = DisplayThread(self.display_queue, self.display_stop_event)
        self.display_thread.update_pixmap.connect(self.set_video_pixmap)
        self.display_thread.start()

        # 连接信号
        self.recognition_success.connect(self.on_recognition_success)
        self.no_face_detected.connect(self.on_no_face_detected)

        # 启动摄像头
        QTimer.singleShot(100, self.start_camera)

        print("[系统] 主窗口初始化完成")

    def _init_font(self):
        """初始化中文字体"""
        font_paths = [
            'C:/Windows/Fonts/msyh.ttc',
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/simsun.ttc',
        ]
        self.font = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    self.font = ImageFont.truetype(path, 18)
                    break
                except:
                    pass
        if self.font is None:
            self.font = ImageFont.load_default()

    def draw_chinese(self, img, text, pos, color_bgr):
        """绘制中文"""
        try:
            color_rgb = (color_bgr[2], color_bgr[1], color_bgr[0])
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            for ox, oy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                draw.text((pos[0]+ox, pos[1]+oy), text, font=self.font, fill=(0,0,0))
            draw.text(pos, text, font=self.font, fill=color_rgb)
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        except:
            return img

    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ============= 左侧：摄像头显示区域 =============
        camera_group = QGroupBox("📷 实时监控画面")
        camera_layout = QVBoxLayout()
        camera_layout.setContentsMargins(15, 25, 15, 15)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                background-color: #1a1a1a;
                color: white;
                font-size: 16px;
            }
        """)
        self.video_label.setText("📷 等待摄像头启动...")
        camera_layout.addWidget(self.video_label)

        status_frame = QFrame()
        status_frame.setStyleSheet("QFrame { background-color: #E3F2FD; border-radius: 8px; padding: 8px; }")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)

        self.cam_status_label = QLabel("● 摄像头在线")
        self.cam_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        status_layout.addWidget(self.cam_status_label)

        status_layout.addStretch()

        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 13px;")
        status_layout.addWidget(self.fps_label)

        camera_layout.addWidget(status_frame)
        camera_group.setLayout(camera_layout)
        main_layout.addWidget(camera_group, 7)

        # ============= 右侧：控制面板 =============
        right_panel = QWidget()
        right_panel.setMaximumWidth(350)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # 考勤控制卡片
        attendance_card = QGroupBox("📋 考勤控制")
        attendance_layout = QVBoxLayout()
        attendance_layout.setSpacing(12)

        self.btn_start_recog = QPushButton("▶ 开始考勤")
        self.btn_start_recog.setStyleSheet("background-color: #4CAF50; font-size: 16px; padding: 15px; border-radius: 10px;")
        self.btn_start_recog.clicked.connect(self.start_recognition)
        attendance_layout.addWidget(self.btn_start_recog)

        self.btn_stop_recog = QPushButton("⬛ 停止考勤")
        self.btn_stop_recog.setStyleSheet("background-color: #f44336; font-size: 16px; padding: 15px; border-radius: 10px;")
        self.btn_stop_recog.clicked.connect(self.stop_recognition)
        self.btn_stop_recog.setEnabled(False)
        attendance_layout.addWidget(self.btn_stop_recog)

        attendance_card.setLayout(attendance_layout)
        right_layout.addWidget(attendance_card)

        # 人员管理卡片
        manage_card = QGroupBox("👥 人员管理")
        manage_layout = QGridLayout()
        manage_layout.setSpacing(10)

        self.btn_register = QPushButton("➕ 人脸注册")
        self.btn_register.setStyleSheet("background-color: #FF9800;")
        self.btn_register.clicked.connect(self.open_register_dialog)
        manage_layout.addWidget(self.btn_register, 0, 0)

        self.btn_manage = QPushButton("🗑️ 人脸管理")
        self.btn_manage.setStyleSheet("background-color: #9C27B0;")
        self.btn_manage.clicked.connect(self.open_manage_dialog)
        manage_layout.addWidget(self.btn_manage, 0, 1)

        self.btn_train = QPushButton("⚙️ 训练模型")
        self.btn_train.setStyleSheet("background-color: #607D8B;")
        self.btn_train.clicked.connect(self.train_model)
        manage_layout.addWidget(self.btn_train, 1, 0, 1, 2)

        manage_card.setLayout(manage_layout)
        right_layout.addWidget(manage_card)

        # 数据管理卡片
        data_card = QGroupBox("📊 数据管理")
        data_layout = QVBoxLayout()
        data_layout.setSpacing(10)

        self.btn_query = QPushButton("📅 考勤查询")
        self.btn_query.setStyleSheet("background-color: #9C27B0;")
        self.btn_query.clicked.connect(self.open_query_dialog)
        data_layout.addWidget(self.btn_query)

        self.btn_exit = QPushButton("🚪 退出系统")
        self.btn_exit.setStyleSheet("background-color: #757575;")
        self.btn_exit.clicked.connect(self.close)
        data_layout.addWidget(self.btn_exit)

        data_card.setLayout(data_layout)
        right_layout.addWidget(data_card)

        # 状态信息卡片
        info_card = QGroupBox("ℹ️ 系统状态")
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        self.status_label = QLabel("● 系统就绪")
        self.status_label.setStyleSheet("background-color: #E8F5E9; color: #2E7D32; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.status_label)

        self.last_attendance_label = QLabel("📌 最近考勤：无")
        self.last_attendance_label.setStyleSheet("background-color: #E3F2FD; color: #0D47A1; padding: 12px; border-radius: 8px; font-size: 13px;")
        self.last_attendance_label.setWordWrap(True)
        info_layout.addWidget(self.last_attendance_label)

        self.recog_status_label = QLabel("⚪ 等待开始考勤")
        self.recog_status_label.setStyleSheet("background-color: #FFF8E1; color: #FF8F00; padding: 12px; border-radius: 8px; font-size: 13px; font-weight: bold;")
        info_layout.addWidget(self.recog_status_label)

        sys_info = QLabel(f"OpenCV: {cv2.__version__} | LBPH: 轻量化版 | 黄山学院")
        sys_info.setStyleSheet("background-color: #FAFAFA; color: #616161; padding: 10px; border-radius: 8px; font-size: 12px;")
        info_layout.addWidget(sys_info)

        info_card.setLayout(info_layout)
        right_layout.addWidget(info_card)

        right_layout.addStretch()
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel, 3)

        central_widget.setLayout(main_layout)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("✨ 欢迎使用人脸识别考勤系统 | 黄山学院 温子鸣")

    def set_video_pixmap(self, pixmap):
        """更新视频画面"""
        try:
            if self.recognition_running and not self.recognition_paused:
                scaled_pixmap = pixmap.scaled(
                    self.video_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation
                )
                self.video_label.setPixmap(scaled_pixmap)
                self.video_label.setText("")
                self.cam_status_label.setText("● 考勤识别中")
                self.cam_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")

                self.frame_count += 1
                if self.frame_count % 30 == 0:
                    now = time.time()
                    self.fps = 30 / (now - self.last_fps_time)
                    self.last_fps_time = now
                    self.fps_label.setText(f"FPS: {self.fps:.1f}")
        except Exception as e:
            print(f"[UI] 更新画面错误: {e}")

    def start_camera(self):
        """启动摄像头"""
        try:
            self.stop_event.clear()
            self.camera_thread = CameraThread(self.frame_queue, self.stop_event)
            self.camera_thread.start()
            self.cam_status_label.setText("● 摄像头在线")
            self.cam_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            print("[系统] 摄像头线程已启动")
        except Exception as e:
            print(f"[系统] 摄像头启动失败: {e}")

    def pause_camera(self):
        """暂停摄像头"""
        print("[系统] 正在暂停摄像头...")
        if self.recognition_running:
            self.stop_recognition()

        if self.camera_thread:
            self.stop_event.set()
            self.camera_thread.stop()
            self.camera_thread = None

        self.cam_status_label.setText("● 摄像头已暂停")
        self.cam_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        print("[系统] 摄像头已暂停")

    def start_recognition(self):
        """启动考勤识别"""
        if self.recognition_running:
            return

        self.recognition_running = True
        self.recognition_paused = False
        self._last_face_detect_time = None
        self._no_face_timer_started = False
        self.btn_start_recog.setEnabled(False)
        self.btn_stop_recog.setEnabled(True)
        self.status_label.setText("● 考勤识别中...")
        self.recog_status_label.setText("🔍 识别中...")
        self.recog_status_label.setStyleSheet("background-color: #E8F5E9; color: #2E7D32; padding: 12px; border-radius: 8px; font-size: 13px; font-weight: bold;")

        self.video_label.setText("")
        self.recog_thread = threading.Thread(target=self.recognition_loop, daemon=True)
        self.recog_thread.start()
        print("[系统] 考勤识别已启动")

    def stop_recognition(self):
        """停止考勤识别"""
        self.recognition_running = False
        self.recognition_paused = False
        self._last_face_detect_time = None
        self._no_face_timer_started = False
        self.btn_start_recog.setEnabled(True)
        self.btn_stop_recog.setEnabled(False)
        self.status_label.setText("● 考勤已停止")
        self.status_label.setStyleSheet("background-color: #FFEBEE; color: #B71C1C; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        self.recog_status_label.setText("⚪ 考勤已停止")
        self.recog_status_label.setStyleSheet("background-color: #F5F5F5; color: #757575; padding: 12px; border-radius: 8px; font-size: 13px; font-weight: bold;")

        self.cam_status_label.setText("● 摄像头在线（考勤停止）")
        self.cam_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        print("[系统] 考勤已停止")

    def continue_recognition(self):
        """继续识别"""
        self.recognition_paused = False
        self._last_face_detect_time = None
        self._no_face_timer_started = False
        self.recog_status_label.setText("🔍 识别中...")
        self.recog_status_label.setStyleSheet("background-color: #E8F5E9; color: #2E7D32; padding: 12px; border-radius: 8px; font-size: 13px; font-weight: bold;")
        print("[系统] 继续识别下一个人")

    def on_recognition_success(self, name, student_id, confidence, is_recorded):
        """识别成功处理 - 弹出确认对话框"""
        dialog = RecognitionSuccessDialog(name, student_id, confidence, is_recorded, self)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            self.continue_recognition()
        else:
            self.stop_recognition()

    def on_no_face_detected(self):
        """未检测到人脸处理 - 弹窗提示"""
        if not hasattr(self, '_last_no_face_time'):
            self._last_no_face_time = 0

        current = time.time()
        if current - self._last_no_face_time > 2:
            self._last_no_face_time = current

            dialog = NoFaceDetectedDialog(self)
            result = dialog.exec_()

            if result == QDialog.Accepted:
                reply = QMessageBox.question(
                    self,
                    "提示",
                    "是否继续识别？\n点击「是」继续识别，点击「否」停止考勤。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self._last_face_detect_time = None
                    self._no_face_timer_started = False
                    self.recognition_paused = False
                    self.recog_status_label.setText("🔍 识别中...")
                else:
                    self.stop_recognition()

    def recognition_loop(self):
        """识别线程主循环 - 修复版"""
        frame_count = 0
        skip_frames = 2

        while self.recognition_running:
            # 如果处于暂停状态，跳过识别处理
            if self.recognition_paused:
                try:
                    frame = self.frame_queue.get(timeout=0.1)
                    if frame is not None and self.display_queue.qsize() < 2:
                        self.display_queue.put(frame)
                except queue.Empty:
                    pass
                continue

            try:
                frame = self.frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            frame_count += 1

            # 跳帧处理
            if frame_count % (skip_frames + 1) != 0:
                if self.display_queue.qsize() < 2:
                    self.display_queue.put(frame)
                continue

            try:
                small_frame = cv2.resize(frame, (320, 240))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                gray_eq = cv2.equalizeHist(gray)

                faces = self.detector.detect(gray_eq)

                scale_x = frame.shape[1] / 320
                scale_y = frame.shape[0] / 240

                recognized = False
                recognized_name = ""
                recognized_id = ""
                recognized_conf = 0
                is_recorded = False
                stranger_detected = False

                # 人脸检测计时器
                if len(faces) > 0:
                    self._last_face_detect_time = time.time()
                    self._no_face_timer_started = False
                else:
                    if self._last_face_detect_time is None:
                        self._last_face_detect_time = time.time()
                        self._no_face_timer_started = True
                    elif self._no_face_timer_started:
                        elapsed = time.time() - self._last_face_detect_time
                        if elapsed >= 5.0:
                            print(f"[识别] 连续{elapsed:.1f}秒未检测到人脸")
                            self.no_face_detected.emit()
                            self._last_face_detect_time = None
                            self._no_face_timer_started = False

                for (x, y, w, h) in faces:
                    x = int(x * scale_x)
                    y = int(y * scale_y)
                    w = int(w * scale_x)
                    h = int(h * scale_y)

                    x = max(0, min(x, frame.shape[1] - 1))
                    y = max(0, min(y, frame.shape[0] - 1))
                    w = min(w, frame.shape[1] - x)
                    h = min(h, frame.shape[0] - y)

                    if w > 30 and h > 30:
                        face_roi = frame[y:y+h, x:x+w]
                        face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                        face_gray = cv2.equalizeHist(face_gray)
                        face_resized = cv2.resize(face_gray, TARGET_IMAGE_SIZE)

                        student_id, confidence = self.recognizer.predict(face_resized)

                        if student_id:
                            # 从数据库获取学生信息
                            stu = get_student_by_id(student_id)
                            if stu:
                                name = stu['name']
                                print(f"[识别] 识别成功: student_id={student_id}, name={name}, confidence={confidence:.1f}")
                            else:
                                name = '未知'
                                print(f"[识别] 警告: 数据库中没有学号 {student_id} 的学生信息")

                            # 防重复打卡检查（5分钟内只记录一次）
                            if not is_duplicate_attendance(student_id):
                                self.add_attendance_task(student_id, name, confidence)
                                is_recorded = True
                                print(f"[考勤] {name} ({student_id}) 打卡成功，置信度: {confidence:.1f}")
                            else:
                                is_recorded = False
                                print(f"[考勤] {name} ({student_id}) 5分钟内已打卡，本次不重复记录")

                            # 只要识别成功就触发弹窗
                            recognized = True
                            recognized_name = name
                            recognized_id = student_id
                            recognized_conf = confidence

                            color = (0, 255, 0)
                            label = f"{name} ({confidence:.1f})"

                            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                            frame = self.draw_chinese(frame, label, (x, y-25), color)
                            frame = self.draw_chinese(frame, "已注册", (x, y+h+5), color)

                            if not is_recorded:
                                frame = self.draw_chinese(frame, "今日已打卡", (x, y+h+25), (255, 165, 0))

                        else:
                            stranger_detected = True
                            color = (0, 0, 255)
                            label = "陌生人"

                            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                            frame = self.draw_chinese(frame, label, (x, y-25), color)
                            frame = self.draw_chinese(frame, "未注册", (x, y+h+5), color)

                # 时间戳
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # 识别状态
                status = "考勤中" if self.recognition_running and not self.recognition_paused else "暂停"
                cv2.putText(frame, f"状态: {status}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # 显示无脸倒计时
                if self._no_face_timer_started and self._last_face_detect_time:
                    elapsed = time.time() - self._last_face_detect_time
                    if elapsed < 5:
                        cv2.putText(frame, f"未检测到人脸: {5-int(elapsed)}秒后将提示",
                                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                if status == "暂停":
                    frame = self.draw_chinese(frame, "等待确认", (frame.shape[1]-120, 60), (255, 165, 0))

                # 陌生人提示
                if stranger_detected:
                    frame = self.draw_chinese(frame, "检测到未注册人员", (frame.shape[1]-210, 50), (0, 0, 255))

                # 识别成功处理
                if recognized:
                    frame = self.draw_chinese(frame, f"考勤成功: {recognized_name}", (frame.shape[1]-250, 90), (0, 255, 0))
                    frame = self.draw_chinese(frame, "已记录考勤" if is_recorded else "今日已打卡",
                                             (frame.shape[1]-200, 120), (0, 255, 0) if is_recorded else (255, 165, 0))
                    frame = self.draw_chinese(frame, "请确认是否继续", (frame.shape[1]-250, 150), (255, 165, 0))

                    current_time = datetime.now().strftime("%H:%M:%S")
                    self.last_attendance_label.setText(
                        f"✅ 最近考勤：{recognized_name} ({recognized_id})\n"
                        f"⏰ 时间：{current_time}\n"
                        f"📊 置信度：{recognized_conf:.1f}"
                    )

                    self.recog_status_label.setText(f"✅ 考勤成功：{recognized_name} | 请确认是否继续")
                    self.recog_status_label.setStyleSheet("background-color: #E8F5E9; color: #2E7D32; padding: 12px; border-radius: 8px; font-size: 13px; font-weight: bold;")

                    # 发射成功信号
                    self.recognition_success.emit(recognized_name, recognized_id, recognized_conf, is_recorded)
                    # 暂停识别，等待用户选择
                    self.recognition_paused = True

            except Exception as e:
                print(f"[识别] 错误: {e}")

            if self.display_queue.qsize() < 2:
                self.display_queue.put(frame)

    def add_attendance_task(self, student_id, name, confidence):
        """添加考勤记录"""
        try:
            add_attendance_record(student_id, name, confidence)
        except Exception as e:
            print(f"[错误] 写入考勤记录失败: {e}")

    def open_register_dialog(self):
        """打开注册对话框"""
        print("[系统] 打开人脸注册对话框")
        self.pause_camera()
        QTimer.singleShot(500, self._show_register_dialog)

    def _show_register_dialog(self):
        """显示注册对话框"""
        try:
            dlg = RegisterDialog(self)
            result = dlg.exec_()
            print(f"[系统] 注册对话框关闭，结果: {result}")
        except Exception as e:
            print(f"[错误] 打开注册对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开注册对话框失败: {str(e)}")
        finally:
            QTimer.singleShot(1000, self.start_camera)

    def open_manage_dialog(self):
        """打开人脸管理对话框"""
        print("[系统] 打开人脸管理对话框")
        try:
            dlg = ManageDialog(self)
            dlg.exec_()
            if hasattr(dlg, 'deleted') and dlg.deleted:
                reply = QMessageBox.question(
                    self,
                    "提示",
                    "已删除人脸数据，是否立即重新训练模型？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.train_model()
        except Exception as e:
            print(f"[错误] 打开人脸管理对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开人脸管理对话框失败: {str(e)}")

    def train_model(self):
        """训练模型"""
        from core.trainer import ModelTrainer
        self.status_label.setText("⚙️ 正在训练模型...")
        self.btn_train.setEnabled(False)

        def train_task():
            try:
                trainer = ModelTrainer()
                success = trainer.train_full()
                if success:
                    self.recognizer.load_model()
                    self.status_label.setText("✅ 模型训练完成")
                    QMessageBox.information(self, "成功", "✅ 模型训练完成！")
                else:
                    self.status_label.setText("❌ 训练失败（无人脸数据）")
                    QMessageBox.warning(self, "失败", "没有找到人脸图片，请先注册")
            except Exception as e:
                self.status_label.setText("❌ 训练出错")
                QMessageBox.critical(self, "错误", f"训练失败: {str(e)}")
            finally:
                self.btn_train.setEnabled(True)

        threading.Thread(target=train_task, daemon=True).start()

    def open_query_dialog(self):
        """打开考勤查询"""
        print("[系统] 打开考勤查询对话框")
        try:
            dlg = QueryDialog(self)
            dlg.exec_()
        except Exception as e:
            print(f"[错误] 打开考勤查询对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开考勤查询对话框失败: {str(e)}")

    def closeEvent(self, event):
        """关闭事件"""
        print("[系统] 正在关闭...")
        self.recognition_running = False
        self.stop_event.set()
        self.display_stop_event.set()

        if self.camera_thread:
            self.camera_thread.stop()

        if hasattr(self, 'display_thread'):
            self.display_thread.wait(1000)

        print("[系统] 已关闭")
        event.accept()