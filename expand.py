import cv2, numpy as np
from pathlib import Path

src_dir = Path(r"图片/女书_new")
dst_dir = Path(r"图片/女书_new_aug"); dst_dir.mkdir(exist_ok=True)

def augments(img):
    h,w = img.shape
    yield cv2.flip(img, 1)
    ang = np.random.uniform(-6,6)
    M = cv2.getRotationMatrix2D((w/2,h/2), ang, 1)
    yield cv2.warpAffine(img, M, (w,h), borderValue=255)
    a = np.random.uniform(0.8,1.2); b = np.random.uniform(-20,20)
    yield np.clip(a*img+b, 0, 255).astype(np.uint8)

for fp in src_dir.rglob("*.jp*g"):
    raw = np.fromfile(fp, dtype=np.uint8)          # 关键行，避免中文路径问题
    img = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
    if img is None or img.size == 0:
        print(f"⚠️ 跳过坏文件 {fp}"); continue

    base = fp.stem                                  # 文件名前缀，用于取 ID
    cv2.imencode(".jpg", img)[1].tofile(dst_dir/f"{base}.jpg")

    for i,im in enumerate(augments(img)):
        cv2.imencode(".jpg", im)[1].tofile(dst_dir/f"{base}_{i}.jpg")

print("✅ 数据增广完成")