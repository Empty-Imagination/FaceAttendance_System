"""
考勤记录查询与导出对话框
修复版 - 正确显示本地时间
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from core.database import query_attendance, get_all_students
import pandas as pd
from datetime import datetime


class QueryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("考勤记录查询")
        self.setGeometry(200, 200, 1100, 650)
        self.setMinimumSize(1000, 550)

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
            QPushButton#queryBtn {
                background-color: #2196F3;
            }
            QPushButton#queryBtn:hover {
                background-color: #1976D2;
            }
            QPushButton#exportBtn {
                background-color: #4CAF50;
            }
            QPushButton#exportBtn:hover {
                background-color: #45a049;
            }
            QPushButton#resetBtn {
                background-color: #FF9800;
            }
            QPushButton#resetBtn:hover {
                background-color: #F57C00;
            }
            QDateEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 13px;
                min-width: 140px;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 13px;
                min-width: 180px;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                font-size: 13px;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 10px;
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
        self.load_student_list()

        # 默认查询今天的记录
        self.date_start.setDate(QDate.currentDate())
        self.date_end.setDate(QDate.currentDate())
        self.query_records()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # ===== 标题区域 =====
        title_layout = QHBoxLayout()
        title_label = QLabel("📊 考勤记录查询")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #1565C0;
            padding: 10px 0;
        """)
        title_layout.addWidget(title_label)

        # 当前时间显示
        self.current_time_label = QLabel()
        self.current_time_label.setStyleSheet("""
            QLabel {
                color: #546E7A;
                font-size: 13px;
                padding: 10px;
                background-color: #F5F5F5;
                border-radius: 5px;
            }
        """)
        title_layout.addStretch()
        title_layout.addWidget(self.current_time_label)
        layout.addLayout(title_layout)

        # 更新时间
        self.update_current_time()

        # ===== 查询条件区域 =====
        query_group = QGroupBox("🔍 查询条件")
        query_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 15px 0 15px;
                color: #2196F3;
                background-color: white;
            }
        """)
        query_layout = QGridLayout()
        query_layout.setContentsMargins(25, 30, 25, 25)
        query_layout.setSpacing(20)

        # 开始日期
        start_label = QLabel("📅 开始日期：")
        start_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #37474F;")
        query_layout.addWidget(start_label, 0, 0)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate())
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setStyleSheet("""
            QDateEdit {
                padding: 10px;
                border: 1px solid #BDBDBD;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QDateEdit:hover {
                border: 2px solid #2196F3;
            }
        """)
        query_layout.addWidget(self.date_start, 0, 1)

        # 结束日期
        end_label = QLabel("📅 结束日期：")
        end_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #37474F;")
        query_layout.addWidget(end_label, 0, 2)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setStyleSheet("""
            QDateEdit {
                padding: 10px;
                border: 1px solid #BDBDBD;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QDateEdit:hover {
                border: 2px solid #2196F3;
            }
        """)
        query_layout.addWidget(self.date_end, 0, 3)

        # 学号筛选
        student_label = QLabel("👤 学号筛选：")
        student_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #37474F;")
        query_layout.addWidget(student_label, 1, 0)

        self.combo_student = QComboBox()
        self.combo_student.addItem("全部人员", None)
        self.combo_student.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #BDBDBD;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QComboBox:hover {
                border: 2px solid #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """)
        query_layout.addWidget(self.combo_student, 1, 1, 1, 3)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_query = QPushButton("🔍 查询记录")
        self.btn_query.setObjectName("queryBtn")
        self.btn_query.setMinimumHeight(45)
        self.btn_query.setStyleSheet("""
            QPushButton#queryBtn {
                background-color: #2196F3;
                font-size: 14px;
                padding: 10px 30px;
                border-radius: 8px;
            }
            QPushButton#queryBtn:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_query.clicked.connect(self.query_records)
        btn_layout.addWidget(self.btn_query)

        self.btn_export = QPushButton("📥 导出Excel")
        self.btn_export.setObjectName("exportBtn")
        self.btn_export.setMinimumHeight(45)
        self.btn_export.setStyleSheet("""
            QPushButton#exportBtn {
                background-color: #4CAF50;
                font-size: 14px;
                padding: 10px 30px;
                border-radius: 8px;
            }
            QPushButton#exportBtn:hover {
                background-color: #45a049;
            }
        """)
        self.btn_export.clicked.connect(self.export_excel)
        btn_layout.addWidget(self.btn_export)

        self.btn_reset = QPushButton("🔄 重置条件")
        self.btn_reset.setObjectName("resetBtn")
        self.btn_reset.setMinimumHeight(45)
        self.btn_reset.setStyleSheet("""
            QPushButton#resetBtn {
                background-color: #FF9800;
                font-size: 14px;
                padding: 10px 30px;
                border-radius: 8px;
            }
            QPushButton#resetBtn:hover {
                background-color: #F57C00;
            }
        """)
        self.btn_reset.clicked.connect(self.reset_query)
        btn_layout.addWidget(self.btn_reset)

        btn_layout.addStretch()
        query_layout.addLayout(btn_layout, 2, 0, 1, 4)

        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        # ===== 统计信息区域 =====
        stats_layout = QHBoxLayout()

        self.stats_label = QLabel("📊 共查询到 0 条考勤记录")
        self.stats_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E3F2FD, stop:1 #BBDEFB);
                color: #0D47A1;
                padding: 15px 20px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        stats_layout.addWidget(self.stats_label)

        stats_layout.addStretch()

        # 显示查询时间
        self.query_time_label = QLabel()
        self.query_time_label.setStyleSheet("""
            QLabel {
                color: #546E7A;
                font-size: 13px;
                padding: 10px 20px;
                background-color: #F5F5F5;
                border-radius: 8px;
            }
        """)
        stats_layout.addWidget(self.query_time_label)

        layout.addLayout(stats_layout)

        # ===== 记录表格区域 =====
        table_group = QGroupBox("📋 考勤记录详情")
        table_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 15px 0 15px;
                color: #2196F3;
                background-color: white;
            }
        """)
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(20, 30, 20, 20)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "学号", "姓名", "考勤时间", "状态", "置信度"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget::alternate-row {
                background-color: #FAFAFA;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #0D47A1;
            }
        """)

        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group, 1)

        self.setLayout(layout)

        # 启动定时器更新时间
        self.start_time_timer()

    def start_time_timer(self):
        """启动定时器，每秒更新一次时间"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_current_time)
        self.timer.start(1000)

    def update_current_time(self):
        """更新当前时间显示"""
        current_time = QDateTime.currentDateTime()
        time_str = current_time.toString("yyyy-MM-dd HH:mm:ss")
        self.current_time_label.setText(f"🕒 系统时间: {time_str}")

    def load_student_list(self):
        """加载学生列表"""
        try:
            students = get_all_students()
            self.combo_student.clear()
            self.combo_student.addItem("📋 全部人员", None)
            for stu in students:
                display_text = f"{stu['student_id']} - {stu['name']}"
                self.combo_student.addItem(display_text, stu['student_id'])
        except Exception as e:
            print(f"[错误] 加载学生列表失败: {e}")

    def reset_query(self):
        """重置查询条件"""
        self.date_start.setDate(QDate.currentDate())
        self.date_end.setDate(QDate.currentDate())
        self.combo_student.setCurrentIndex(0)
        self.query_records()

    def query_records(self):
        """查询考勤记录"""
        try:
            start = self.date_start.date().toString("yyyy-MM-dd")
            end = self.date_end.date().toString("yyyy-MM-dd")
            student_id = self.combo_student.currentData()

            # 确保结束日期包含当天
            end_dt = QDate.fromString(end, "yyyy-MM-dd")
            end_dt = end_dt.addDays(1)
            end = end_dt.toString("yyyy-MM-dd")

            records = query_attendance(start, end, student_id)

            self.table.setRowCount(len(records))

            for row, rec in enumerate(records):
                # ID
                id_item = QTableWidgetItem(str(rec['id']))
                id_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, id_item)

                # 学号
                stu_id_item = QTableWidgetItem(rec['student_id'])
                stu_id_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, stu_id_item)

                # 姓名
                name_item = QTableWidgetItem(rec['name'])
                name_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, name_item)

                # ===== 考勤时间 - 直接显示数据库中的本地时间 =====
                check_time = rec['check_time']
                if isinstance(check_time, str):
                    # 已经是字符串格式，直接截取前19个字符
                    time_str = check_time[:19] if len(check_time) >= 19 else check_time
                else:
                    # 如果是datetime对象，格式化
                    time_str = check_time.strftime('%Y-%m-%d %H:%M:%S')

                time_item = QTableWidgetItem(time_str)
                time_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, time_item)
                # ================================================

                # 状态
                status = "✅ 正常" if rec['status'] == 1 else "⚠️ 迟到"
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                if rec['status'] == 1:
                    status_item.setForeground(QColor(46, 125, 50))
                else:
                    status_item.setForeground(QColor(211, 47, 47))
                self.table.setItem(row, 4, status_item)

                # 置信度
                conf = rec['confidence']
                if conf:
                    conf_text = f"{conf:.1f}"
                    conf_item = QTableWidgetItem(conf_text)
                    if conf < 50:
                        conf_item.setForeground(QColor(46, 125, 50))
                    elif conf < 65:
                        conf_item.setForeground(QColor(255, 152, 0))
                    else:
                        conf_item.setForeground(QColor(211, 47, 47))
                else:
                    conf_item = QTableWidgetItem("-")
                conf_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, conf_item)

            # 更新统计信息
            self.stats_label.setText(f"📊 共查询到 {len(records)} 条考勤记录")
            self.query_time_label.setText(f"🕒 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            print(f"[错误] 查询考勤记录失败: {e}")
            QMessageBox.critical(self, "查询失败", f"❌ 查询考勤记录失败：{str(e)}")

    def export_excel(self):
        """导出考勤记录到Excel"""
        try:
            if self.table.rowCount() == 0:
                QMessageBox.warning(self, "提示", "⚠️ 没有数据可导出")
                return

            # 获取表格数据
            records = []
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        text = item.text().replace("✅ ", "").replace("⚠️ ", "")
                        row_data.append(text)
                    else:
                        row_data.append('')
                records.append(row_data)

            columns = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            df = pd.DataFrame(records, columns=columns)

            start_date = self.date_start.date().toString("yyyyMMdd")
            end_date = self.date_end.date().toString("yyyyMMdd")
            current_time = QDateTime.currentDateTime().toString("HHmmss")
            default_name = f"考勤记录_{start_date}_至_{end_date}_{current_time}.xlsx"

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "导出Excel",
                default_name,
                "Excel文件 (*.xlsx)"
            )

            if filename:
                if not filename.endswith('.xlsx'):
                    filename += '.xlsx'

                df.to_excel(filename, index=False, engine='openpyxl')

                QMessageBox.information(
                    self,
                    "导出成功",
                    f"✅ 成功导出 {len(records)} 条考勤记录到：\n{filename}"
                )

        except Exception as e:
            print(f"[错误] 导出Excel失败: {e}")
            QMessageBox.critical(self, "导出失败", f"❌ 导出Excel失败：{str(e)}")

    def closeEvent(self, event):
        """关闭窗口时停止定时器"""
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        event.accept()