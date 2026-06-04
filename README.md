# Face Attendance System

基于 OpenCV + PyQt5 的人脸识别考勤系统

---

## 项目简介

本项目为本科毕业设计，实现了基于计算机视觉的人脸识别考勤管理系统。  
系统功能包括：

- 人脸采集
- 人脸训练
- 实时人脸识别
- 自动考勤记录
- 考勤数据查询与导出
- 用户管理

项目适合作为校园或企业内部考勤演示系统。

---

## 技术栈

| 技术 | 用途 |
|------|------|
| Python | 开发语言 |
| OpenCV | 人脸检测与识别 |
| LBPH | 人脸识别算法 |
| PyQt5 | 图形界面开发 |
| SQLite | 数据存储 |
| Pandas | 数据处理与导出 |

---

## 项目结构

```text
FaceAttendance_System/
├── assets/          # 模型、图标等资源
├── core/            # 核心业务逻辑
├── ui/              # 界面代码
├── utils/           # 工具类
├── data/            # 数据库 & 模型（注意已清理敏感人脸数据）
├── main.py          # 程序入口
└── requirements.txt # Python 依赖
```

---

## 安装依赖

```bash
pip install -r requirements.txt
```

---

## 运行方法

```bash
python main.py
```

---

## 注意事项

- `data/faces/` 已从仓库移除，保护隐私  
- 本地可保留用于训练的照片，但不要上传到公开仓库  
- `.idea/`、数据库和 Excel 文件已从仓库移除

---

## 作者

**Empty-Imagination**
