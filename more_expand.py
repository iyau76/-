import cv2
import numpy as np
from pathlib import Path
from scipy.ndimage import map_coordinates
import random

def elastic_distortion(img, alpha=20, sigma=5):
    h, w = img.shape
    dx = np.random.uniform(-1, 1, (h,w)) * alpha
    dy = np.random.uniform(-1, 1, (h,w)) * alpha
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    indices = (np.reshape(y+dy, (-1,1)), np.reshape(x+dx, (-1,1)))
    return map_coordinates(img, indices, order=1, mode='reflect').reshape(h,w).astype(np.uint8)

def random_occlusion(img, max_occlusion_size=0.3):
    h, w = img.shape
    occlusion_w = int(w * random.uniform(0.1, max_occlusion_size))
    occlusion_h = int(h * random.uniform(0.1, max_occlusion_size))
    x = random.randint(0, w - occlusion_w)
    y = random.randint(0, h - occlusion_h)
    img[y:y+occlusion_h, x:x+occlusion_w] = 255
    return img

def random_perspective(img):
    """修复后的透视变换函数"""
    h, w = img.shape
    # 定义原始4个角点（必须为float32）
    pts1 = np.float32([[0,0], [w-1,0], [0,h-1], [w-1,h-1]])
    # 生成目标点（限制在图像范围内）
    margin = min(w, h) * 0.1
    pts2 = pts1 + np.random.uniform(-margin, margin, size=(4,2))
    pts2 = np.clip(pts2, [0,0], [w-1, h-1]).astype(np.float32)
    # 确保点集不共线（通过面积检查）
    area = cv2.contourArea(pts2.reshape(-1,1,2))
    if area < 100:  # 如果面积太小，重新生成
        return random_perspective(img)
    M = cv2.getPerspectiveTransform(pts1, pts2)
    return cv2.warpPerspective(img, M, (w,h), borderMode=cv2.BORDER_REFLECT)

def augments(img):
    h, w = img.shape
    yield img  # 原始图像
    
    for _ in range(20):  # 生成20个增强样本
        augmented = img.copy()
        transforms = random.sample([
            lambda x: cv2.flip(x, 1),
            lambda x: cv2.warpAffine(
                x, 
                cv2.getRotationMatrix2D((w/2,h/2), random.uniform(-15,15), 1),
                (w,h), borderMode=cv2.BORDER_REFLECT
            ),
            lambda x: cv2.warpAffine(
                x,
                np.float32([[1,0,random.uniform(-0.1,0.1)*w], 
                          [0,1,random.uniform(-0.1,0.1)*h]]),
                (w,h), borderMode=cv2.BORDER_REFLECT
            ),
            lambda x: elastic_distortion(x),
            lambda x: random_occlusion(x),
            lambda x: random_perspective(x),
            lambda x: cv2.GaussianBlur(x, (3,3), random.uniform(0,0.2)),
            lambda x: np.clip(x * random.uniform(0.8,1.2) + random.uniform(-10,10), 0, 255).astype(np.uint8)
        ], k=random.randint(2,4))
        
        for transform in transforms:
            augmented = transform(augmented)
        yield augmented

# 处理文件
src_dir = Path(r"图片/女书_merge")
dst_dir = Path(r"图片/女书_new_merge_5x")
dst_dir.mkdir(exist_ok=True)

for fp in src_dir.rglob("*.*"):
    if fp.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
        continue
        
    raw = np.fromfile(fp, dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
    if img is None or img.size == 0:
        print(f"⚠️ 跳过坏文件 {fp}")
        continue

    base, ext = fp.stem, fp.suffix.lower()
    for i, aug_img in enumerate(augments(img)):
        cv2.imencode(ext, aug_img)[1].tofile(dst_dir/f"{base}_aug{i:02d}{ext}")

print("✅ 20倍数据增强完成")