# -*- coding: utf-8 -*-
"""
KNN_model.py  – 训练 / 评估 / 保存 女书 OCR 的 KNN 分类器
默认从  图片/女书_new_aug  读取 220×480 灰度小图
文件名可为 32.jpg, 32_0.jpg, 32_a.jpg …   解析出的数字前缀为类别 ID
生成 model_KNN.joblib 供 translate.py 调用
"""

import re, cv2, joblib
import numpy as np
from pathlib import Path
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# ------------ 参数 ------------
IMG_DIR = Path(r"图片/女书_new_aug")   # 数据目录，可按需修改
IMG_SIZE = (220, 480)                # (w,h) – 与切图保持一致
K        = 3                         # KNN 超参数 (1/3/5)
TEST_RATIO = 0.3
RANDOM_SEED = 42
MODEL_PATH  = "model_KNN.joblib"
# ------------------------------

def data_process(img: np.ndarray) -> np.ndarray:
    """灰度 → 0-1 → flatten"""
    return (img.astype(np.float32) / 255.).flatten()

def load_data(img_dir: Path):
    images, labels = [], []
    # rglob 同时匹配 jpg/JPG/jpeg/png
    for fp in img_dir.rglob("*.[jJpP][pPnN][gG]"):
        raw = np.fromfile(fp, dtype=np.uint8)                 # 防中文路径
        img = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
        if img is None or img.size == 0:
            print(f"⚠️ 跳过坏图 {fp}");  continue
        img = cv2.resize(img, IMG_SIZE[::-1])                 # (w,h)
        images.append(data_process(img))

        m = re.search(r"(\d+)", fp.stem)                      # 提取数字前缀
        if not m:
            print(f"⚠️ 跳过无法解析 ID 的文件 {fp}");  continue
        labels.append(int(m.group(1)))

    images = np.asarray(images)
    labels = np.asarray(labels)
    print(f"数据统计：样本 {len(labels)}，类别 {labels.max()+1}")
    return images, labels

def create_and_save_model(X_train, y_train, X_test, y_test):
    knn = KNeighborsClassifier(n_neighbors=K, weights='distance', n_jobs=-1)
    knn.fit(X_train, y_train)
    joblib.dump(knn, MODEL_PATH)
    print(f"✅ 模型已保存 → {MODEL_PATH}")

    y_pred = knn.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"✅ 测试集 Top-1 accuracy = {acc:.4f}")

def main():
    if not IMG_DIR.exists():
        raise FileNotFoundError(f"找不到数据目录：{IMG_DIR}")

    imgs, lbls = load_data(IMG_DIR)
    X_train, X_test, y_train, y_test = train_test_split(
        imgs, lbls, test_size=TEST_RATIO,
        stratify=lbls, random_state=RANDOM_SEED)

    print(f"训练集维度：{X_train.shape}, 测试集维度：{X_test.shape}")
    create_and_save_model(X_train, y_train, X_test, y_test)

if __name__ == "__main__":
    main()