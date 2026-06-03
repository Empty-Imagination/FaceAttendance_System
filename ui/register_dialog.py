"""
人脸注册对话框
修复版 - 使用通配符导入所有PyQt5组件
"""

import cv2
import os
import threading
import time
from PyQt5.QtWidgets import *  # 一次性导入所有Qt Widgets组件
from PyQt5.QtCore import *      # 一次性导入所有Qt Core组件
from PyQt5.QtGui import *       # 一次性导入所有Qt Gui组件

from core.face_detector import FaceDetector
from core.database import add_student, update_face_count
from utils.config import FACES_DIR, TARGET_IMAGE_SIZE, REGISTER_FACE_COUNT
from utils.helper import is_image_quality_ok


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("人脸注册")
        self.setGeometry(200, 200, 900, 650)
        self.setMinimumSize(800, 550)

        print("[注册] 初始化注册对话框")

        # 注册状态
        self.collected_count = 0
        self.target_count = REGISTER_FACE_COUNT
        self.current_student_id = None
        self.current_name = None
        self.is_capturing = False

        # 摄像头控制
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.camera_opened = False

        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                color: white;
            }
            QPushButton#startBtn {
                background-color: #4CAF50;
            }
            QPushButton#startBtn:hover {
                background-color: #45a049;
            }
            QPushButton#stopBtn {
                background-color: #f44336;
            }
            QPushButton#stopBtn:hover {
                background-color: #da190b;
            }
            QPushButton#closeBtn {
                background-color: #757575;
            }
            QPushButton#closeBtn:hover {
                background-color: #616161;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QGroupBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2196F3;
            }
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #E0E0E0;
                height: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)

        self.init_ui()
        self.detector = FaceDetector()

        # 延迟打开摄像头
        QTimer.singleShot(500, self.start_camera)

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("📸 人脸注册")
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #263238;
            padding: 10px;
        """)
        layout.addWidget(title_label)

        # ===== 摄像头预览区域 =====
        camera_group = QGroupBox("摄像头预览")
        camera_layout = QVBoxLayout()
        camera_layout.setContentsMargins(15, 25, 15, 15)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 400)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                background-color: #1a1a1a;
                color: white;
                font-size: 14px;
            }
        """)
        self.video_label.setText("📷 正在启动摄像头...")
        camera_layout.addWidget(self.video_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.target_count)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("采集进度: %v/%m")
        camera_layout.addWidget(self.progress_bar)

        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)

        # ===== 信息输入区域 =====
        info_group = QGroupBox("人员信息")
        info_layout = QGridLayout()
        info_layout.setContentsMargins(20, 25, 20, 20)
        info_layout.setSpacing(15)

        # 学号
        info_layout.addWidget(QLabel("学号："), 0, 0)
        self.edit_id = QLineEdit()
        self.edit_id.setPlaceholderText("请输入学号")
        self.edit_id.setMinimumWidth(200)
        info_layout.addWidget(self.edit_id, 0, 1)

        # 姓名
        info_layout.addWidget(QLabel("姓名："), 0, 2)
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("请输入姓名")
        self.edit_name.setMinimumWidth(200)
        info_layout.addWidget(self.edit_name, 0, 3)

        # 采集张数
        info_layout.addWidget(QLabel("采集张数："), 1, 0)
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 10)
        self.spin_count.setValue(self.target_count)
        self.spin_count.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        info_layout.addWidget(self.spin_count, 1, 1)

        # 提示信息
        self.tip_label = QLabel("请输入学号和姓名，点击「开始采集」")
        self.tip_label.setStyleSheet("""
            QLabel {
                color: #2196F3;
                font-size: 13px;
                padding: 5px;
            }
        """)
        info_layout.addWidget(self.tip_label, 1, 2, 1, 2)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # ===== 按钮区域 =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_start = QPushButton("▶ 开始采集")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_capture)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⬛ 停止采集")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_capture)
        btn_layout.addWidget(self.btn_stop)

        btn_layout.addStretch()

        self.btn_close = QPushButton("✖️ 关闭")
        self.btn_close.setObjectName("closeBtn")
        self.btn_close.setMinimumHeight(40)
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def start_camera(self):
        """打开摄像头"""
        try:
            print("[注册] 正在打开摄像头...")

            # 尝试打开摄像头
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                self.camera_opened = True
                self.timer.start(30)
                self.video_label.setText("")
                self.btn_start.setEnabled(True)
                self.tip_label.setText("✅ 摄像头已就绪，请输入信息后开始采集")
                print("[注册] 摄像头打开成功")
            else:
                self.video_label.setText("❌ 无法打开摄像头，请检查设备")
                self.tip_label.setText("❌ 摄像头初始化失败")
                print("[注册] 摄像头打开失败")

        except Exception as e:
            print(f"[注册] 摄像头打开异常: {e}")
            self.video_label.setText(f"❌ 摄像头错误")

    def update_frame(self):
        """更新摄像头画面"""
        if not self.camera_opened or self.cap is None:
            return

        try:
            ret, frame = self.cap.read()
            if ret:
                # 检测人脸并绘制矩形
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_eq = cv2.equalizeHist(gray)
                faces = self.detector.detect(gray_eq)

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    if self.is_capturing:
                        cv2.putText(frame, "采集中...", (x, y-10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 转换为Qt显示
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                scaled_pixmap = pixmap.scaled(
                    self.video_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation
                )
                self.video_label.setPixmap(scaled_pixmap)
                self.video_label.setText("")

                # 如果在采集中，尝试保存人脸
                if self.is_capturing:
                    self.try_capture_face(gray_eq, faces)
            else:
                print("[注册] 读取帧失败")
        except Exception as e:
            print(f"[注册] 更新画面错误: {e}")

    def try_capture_face(self, gray, faces):
        """尝试采集合格的人脸"""
        if len(faces) == 0:
            self.tip_label.setText("❌ 未检测到人脸，请正对摄像头")
            return

        largest = max(faces, key=lambda rect: rect[2]*rect[3])
        x, y, w, h = largest
        face_roi = gray[y:y+h, x:x+w]

        ok, msg = is_image_quality_ok(face_roi)
        if not ok:
            self.tip_label.setText(f"⚠️ 照片不合格：{msg}")
            return

        face_resized = cv2.resize(face_roi, TARGET_IMAGE_SIZE)
        filename = f"{self.current_student_id}_{self.collected_count+1}.jpg"
        filepath = FACES_DIR / filename
        cv2.imwrite(str(filepath), face_resized)

        self.collected_count += 1
        self.progress_bar.setValue(self.collected_count)
        self.tip_label.setText(f"✅ 已采集 {self.collected_count}/{self.target_count} 张")

        if self.collected_count >= self.target_count:
            self.finish_capture()

    def start_capture(self):
        """开始采集"""
        student_id = self.edit_id.text().strip()
        name = self.edit_name.text().strip()

        if not student_id or not name:
            QMessageBox.warning(self, "提示", "学号和姓名不能为空")
            return

        self.current_student_id = student_id
        self.current_name = name
        self.target_count = self.spin_count.value()
        self.collected_count = 0

        add_student(student_id, name)

        self.is_capturing = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setRange(0, self.target_count)
        self.progress_bar.setValue(0)
        self.tip_label.setText(f"▶ 开始采集，目标 {self.target_count} 张")

    def stop_capture(self):
        """停止采集"""
        self.is_capturing = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.tip_label.setText("⏹️ 采集已停止")

    def finish_capture(self):
        """采集完成"""
        self.is_capturing = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        update_face_count(self.current_student_id, self.collected_count)

        self.tip_label.setText(f"✅ 注册成功！已保存 {self.collected_count} 张照片")
        QMessageBox.information(
            self,
            "注册成功",
            f"✅ 学生 {self.current_name} 注册成功！\n"
            f"学号：{self.current_student_id}\n"
            f"采集照片：{self.collected_count} 张"
        )

    def closeEvent(self, event):
        """关闭窗口时释放摄像头"""
        print("[注册] 关闭对话框，释放摄像头...")

        if self.timer.isActive():
            self.timer.stop()

        if self.cap:
            self.cap.release()

            self.cap = None

        self.camera_opened = False
        print("[注册] 摄像头已释放")

        event.accept()