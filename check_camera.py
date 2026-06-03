"""
检测可用摄像头
直接打印结果，不依赖任何外部库（除了cv2）
"""

import cv2
import sys

print("=" * 60)
print("摄像头检测工具")
print("=" * 60)
print(f"Python版本: {sys.version}")
print(f"OpenCV版本: {cv2.__version__}")
print("=" * 60)

available_cameras = []

# 检测索引0-9
for i in range(10):
    try:
        print(f"正在检测摄像头 [{i}]...", end=" ")
        # Windows系统使用DirectShow后端
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)

        if cap.isOpened():
            # 尝试读取一帧
            ret, frame = cap.read()
            if ret:
                print(f"✓ 可用 (可正常读取)")
                available_cameras.append(i)
            else:
                print(f"⚠ 可打开但无法读取画面")
            cap.release()
        else:
            print(f"✗ 不可用")
    except Exception as e:
        print(f"✗ 错误: {e}")

print("=" * 60)
if available_cameras:
    print(f"✅ 找到可用摄像头索引: {available_cameras}")
    print(f"👉 建议在 config.py 中设置 CAMERA_ID = {available_cameras[0]}")
else:
    print("❌ 未找到任何可用摄像头！")
    print("\n可能的原因:")
    print("1. 电脑没有连接摄像头")
    print("2. 摄像头驱动未安装")
    print("3. 摄像头被其他程序占用")
    print("4. 虚拟机环境没有摄像头权限")
    print("\n解决方案:")
    print("- 笔记本: 检查摄像头开关是否打开")
    print("- 台式机: 连接USB摄像头")
    print("- 虚拟机: 在VMware/VirtualBox中启用摄像头")
    print("- 手机: 安装DroidCam充当无线摄像头")
print("=" * 60)

input("\n按回车键退出...")