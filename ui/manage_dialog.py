"""
人脸管理对话框
修复版 - 正确显示系统时间
"""

import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from core.database import get_all_students, get_student_by_id, update_face_count, delete_student
from utils.config import FACES_DIR


class ManageDialog(QDialog):
    """人脸管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("人脸管理 - 删除注册信息")
        self.setGeometry(200, 200, 900, 550)
        self.setMinimumSize(800, 450)

        self.deleted = False

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
            QPushButton#deleteBtn {
                background-color: #f44336;
            }
            QPushButton#deleteBtn:hover {
                background-color: #d32f2f;
            }
            QPushButton#refreshBtn {
                background-color: #2196F3;
            }
            QPushButton#refreshBtn:hover {
                background-color: #1976D2;
            }
            QPushButton#closeBtn {
                background-color: #757575;
            }
            QPushButton#closeBtn:hover {
                background-color: #616161;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                font-size: 13px;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #0D47A1;
            }
            QHeaderView::section {
                background-color: #EEEEEE;
                padding: 12px;
                font-weight: bold;
                border: none;
                border-right: 1px solid #E0E0E0;
                border-bottom: 1px solid #E0E0E0;
                font-size: 13px;
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
        """)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("👥 已注册人员管理")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #263238;
            padding: 10px;
        """)
        layout.addWidget(title_label)

        # 提示信息
        info_label = QLabel(
            "⚠️ 提示：删除人员将同时删除其所有人脸照片和考勤记录，且不可恢复！"
        )
        info_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3E0;
                color: #E65100;
                padding: 12px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 人员表格
        group_box = QGroupBox("📋 已注册人员列表")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(15, 25, 15, 15)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["学号", "姓名", "照片数", "注册时间", "操作"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget::alternate-row {
                background-color: #FAFAFA;
            }
        """)

        group_layout.addWidget(self.table)
        group_box.setLayout(group_layout)
        layout.addWidget(group_box, 1)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.btn_refresh = QPushButton("🔄 刷新列表")
        self.btn_refresh.setObjectName("refreshBtn")
        self.btn_refresh.clicked.connect(self.load_data)
        btn_layout.addWidget(self.btn_refresh)

        btn_layout.addStretch()

        self.btn_delete = QPushButton("🗑️ 删除选中")
        self.btn_delete.setObjectName("deleteBtn")
        self.btn_delete.clicked.connect(self.delete_selected)
        btn_layout.addWidget(self.btn_delete)

        self.btn_close = QPushButton("✖️ 关闭")
        self.btn_close.setObjectName("closeBtn")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def format_time(self, time_value):
        """
        格式化时间为 'YYYY-MM-DD HH:MM:SS' 格式
        """
        if time_value is None:
            return "未知"

        try:
            # 如果是字符串，直接返回前19个字符
            if isinstance(time_value, str):
                if len(time_value) >= 19:
                    return time_value[:19]
                return time_value

            # 如果是datetime对象，格式化
            if hasattr(time_value, 'strftime'):
                return time_value.strftime('%Y-%m-%d %H:%M:%S')

            return str(time_value)
        except Exception as e:
            print(f"[格式化时间错误] {e}")
            return str(time_value)

    def load_data(self):
        """加载已注册人员数据"""
        try:
            students = get_all_students()
            self.table.setRowCount(len(students))

            for row, student in enumerate(students):
                student_id = student['student_id']
                stu_info = get_student_by_id(student_id)

                if stu_info:
                    # 学号
                    self.table.setItem(row, 0, QTableWidgetItem(student_id))
                    # 姓名
                    self.table.setItem(row, 1, QTableWidgetItem(stu_info['name']))
                    # 照片数
                    face_count = stu_info.get('face_count', 0)
                    count_item = QTableWidgetItem(str(face_count))
                    if face_count == 0:
                        count_item.setForeground(QColor(255, 0, 0))
                    self.table.setItem(row, 2, count_item)
                    # 注册时间 - 使用格式化函数
                    create_time = stu_info.get('create_time', None)
                    time_str = self.format_time(create_time)
                    time_item = QTableWidgetItem(time_str)
                    time_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 3, time_item)

                    # 操作按钮
                    btn_widget = QWidget()
                    btn_layout = QHBoxLayout()
                    btn_layout.setContentsMargins(5, 2, 5, 2)
                    btn_layout.setSpacing(5)

                    btn_delete = QPushButton("删除")
                    btn_delete.setStyleSheet("""
                        QPushButton {
                            background-color: #f44336;
                            color: white;
                            padding: 5px 15px;
                            border-radius: 4px;
                            font-size: 12px;
                            min-width: 60px;
                        }
                        QPushButton:hover {
                            background-color: #d32f2f;
                        }
                    """)
                    btn_delete.clicked.connect(lambda checked, sid=student_id: self.delete_single(sid))
                    btn_layout.addWidget(btn_delete)

                    btn_widget.setLayout(btn_layout)
                    self.table.setCellWidget(row, 4, btn_widget)
        except Exception as e:
            print(f"[人脸管理] 加载数据失败: {e}")
            QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")

    def delete_single(self, student_id):
        """删除单个人员"""
        try:
            stu_info = get_student_by_id(student_id)
            name = stu_info['name'] if stu_info else '未知'

            reply = QMessageBox.question(
                self,
                "确认删除",
                f"⚠️ 确定要删除【{name} ({student_id})】吗？\n\n"
                f"此操作将删除：\n"
                f"• 该学生的所有人脸照片\n"
                f"• 该学生的所有考勤记录\n"
                f"• 数据库中的学生信息\n\n"
                f"此操作不可恢复！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self._delete_student_data(student_id)
        except Exception as e:
            print(f"[人脸管理] 删除失败: {e}")
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def delete_selected(self):
        """删除选中的人员"""
        try:
            selected_rows = set()
            for item in self.table.selectedItems():
                selected_rows.add(item.row())

            if not selected_rows:
                QMessageBox.warning(self, "提示", "请先选择要删除的人员")
                return

            student_ids = []
            student_names = []
            for row in selected_rows:
                student_id = self.table.item(row, 0).text()
                name = self.table.item(row, 1).text()
                student_ids.append(student_id)
                student_names.append(f"{name} ({student_id})")

            reply = QMessageBox.question(
                self,
                "确认批量删除",
                f"⚠️ 确定要删除以下 {len(student_ids)} 名人员吗？\n\n"
                f"{chr(10).join(student_names[:5])}"
                f"{'...' if len(student_names) > 5 else ''}\n\n"
                f"此操作将删除所有人脸照片和考勤记录，不可恢复！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                success_count = 0
                for student_id in student_ids:
                    if self._delete_student_data(student_id, show_message=False):
                        success_count += 1

                QMessageBox.information(
                    self,
                    "删除完成",
                    f"✅ 成功删除 {success_count} 名人员\n"
                    f"❌ 失败 {len(student_ids) - success_count} 名"
                )
                self.deleted = True
                self.load_data()
        except Exception as e:
            print(f"[人脸管理] 批量删除失败: {e}")
            QMessageBox.critical(self, "错误", f"批量删除失败: {str(e)}")

    def _delete_student_data(self, student_id, show_message=True):
        """执行删除操作"""
        try:
            # 1. 删除人脸图片文件
            face_files = list(FACES_DIR.glob(f"{student_id}_*.jpg"))
            deleted_count = 0
            for face_file in face_files:
                try:
                    os.remove(face_file)
                    deleted_count += 1
                except Exception as e:
                    print(f"[人脸管理] 删除文件失败: {face_file} - {e}")

            # 2. 从数据库删除学生记录（同时删除考勤记录）
            success = delete_student(student_id)

            if success:
                if show_message:
                    QMessageBox.information(
                        self,
                        "删除成功",
                        f"✅ 已删除人员\n"
                        f"学号：{student_id}\n"
                        f"共删除 {deleted_count} 张人脸照片"
                    )
                self.deleted = True
                return True
            else:
                if show_message:
                    QMessageBox.critical(self, "删除失败", f"❌ 数据库删除失败")
                return False

        except Exception as e:
            print(f"[人脸管理] 删除操作异常: {e}")
            if show_message:
                QMessageBox.critical(self, "错误", f"❌ 删除失败: {str(e)}")
            return False

    def closeEvent(self, event):
        """关闭窗口"""
        event.accept()