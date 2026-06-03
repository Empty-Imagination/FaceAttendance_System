"""
调试工具：测试人脸识别置信度
"""

import cv2
import numpy as np
from pathlib import Path
from core.recognizer import LBPHRecognizer
from core.face_detector import FaceDetector
from utils.config import TARGET_IMAGE_SIZE

def test_recognition():
    print("=" * 50)
    print("人脸识别调试工具")
    print("=" * 50)
    
    # 初始化
    recognizer = LBPHRecognizer()
    detector = FaceDetector()
    
    if not recognizer.recognizer:
        print("错误：模型未加载，请先训练模型！")
        return
    
    print(f"当前阈值: {recognizer.threshold}")
    print(f"已注册人员: {list(recognizer.label_map.values())}")
    
    # 打开摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    print("\n按 'q' 退出，按 't' 调整阈值")
    print("按 's' 保存当前帧用于分析")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 人脸检测
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detect(gray)
        
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_roi, TARGET_IMAGE_SIZE)
            
            # 识别
            student_id, confidence = recognizer.predict(face_resized)
            
            if student_id:
                label = f"识别成功: {student_id} (置信度: {confidence:.1f})"
                color = (0, 255, 0)
            else:
                label = f"陌生人 (置信度: {confidence:.1f})"
                color = (0, 0, 255)
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 显示当前阈值
        cv2.putText(frame, f"Threshold: {recognizer.threshold}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Debug - Face Recognition", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('t'):
            # 调整阈值
            new_threshold = recognizer.threshold + 5
            if new_threshold > 150:
                new_threshold = 50
            recognizer.set_threshold(new_threshold)
            print(f"阈值调整为: {new_threshold}")
        elif key == ord('s'):
            # 保存当前帧
            timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"debug_{timestamp}.jpg", frame)
            print(f"已保存: debug_{timestamp}.jpg")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_recognition()