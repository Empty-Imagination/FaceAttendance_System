"""
主程序入口 - 完全优化版
"""

import os
import sys
import warnings
import time

# ====== 关键优化：禁用MSMF ======
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
os.environ['OPENCV_VIDEOIO_PRIORITY_DShow'] = '1'
os.environ['OPENCV_OPENCL_DEVICE'] = 'disabled'
# ===============================

import cv2
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont, QColor

# 禁用OpenCL
try:
    cv2.ocl.setUseOpenCL(False)
except:

    pass

# 设置OpenCV线程数
try:
    cv2.setNumThreads(1)
except:
    pass

# 忽略PyQt5的libpng警告
warnings.filterwarnings("ignore", category=UserWarning, module="PyQt5")

from ui.main_window import MainWindow


def show_splash_screen():
    """显示启动画面"""
    splash_pix = QPixmap(600, 300)
    splash_pix.fill(QColor(33, 150, 243))

    splash = QSplashScreen(splash_pix)
    splash.setFont(QFont("Microsoft YaHei", 12))

    splash.show()
    splash.showMessage(
        "🚀 人脸识别考勤系统 正在启动...\n\n"
        f"📦 OpenCV版本: {cv2.__version__}\n"
        f"👤 LBPH模块: {'✅ 可用' if hasattr(cv2.face, 'LBPHFaceRecognizer_create') else '❌ 不可用'}\n"
        f"🎨 界面美化: ✅\n"
        f"📊 轻量化LBPH: ✅ (4x4网格)\n\n"
        "黄山学院 · 温子鸣 毕业设计",
        Qt.AlignCenter | Qt.AlignTop,
        Qt.white
    )

    return splash


def main():
    """主函数"""
    # 启用高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("人脸识别考勤系统")
    app.setApplicationDisplayName("人脸识别考勤系统 · 智慧校园版")
    app.setQuitOnLastWindowClosed(True)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 显示启动画面
    splash = show_splash_screen()
    app.processEvents()

    # 打印系统信息
    print("=" * 60)
    print("             人脸识别考勤系统 v2.0")
    print("=" * 60)
    print(f"🕒 启动时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python版本: {sys.version.split()[0]}")
    print(f"📦 OpenCV版本: {cv2.__version__}")
    print(f"👤 LBPH模块: {'✅ 可用' if hasattr(cv2.face, 'LBPHFaceRecognizer_create') else '❌ 不可用'}")
    print(f"📊 轻量化LBPH: ✅ (网格: 4x4, 特征维度: 4096)")
    print(f"🎨 界面主题: 现代扁平化设计")
    print(f"👨‍🎓 作者: 温子鸣 | 黄山学院")
    print("=" * 60)

    # 创建主窗口
    window = MainWindow()

    # 关闭启动画面，显示主窗口
    splash.finish(window)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()