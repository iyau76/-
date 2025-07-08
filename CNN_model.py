# -*- coding: utf-8 -*-
"""
CNN_model.py   —   女书手写 OCR  (streaming + periodic checkpoint)
"""

from pathlib import Path
import re, cv2, numpy as np, tensorflow as tf, keras, albumentations as A
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

# ---------------- 全局参数 ----------------
IMG_DIR      = Path("/content/Women_Books-main/图片/女书_new_aug")
IMG_SIZE     = (220, 480)
BATCH_SIZE   = 24
EPOCHS       = 100
SEED         = 42
MODEL_PATH   = "model_CNN.h5"
CKPT_DIR     = Path("checkpoints")          # ← 保存中间模型目录
CKPT_DIR.mkdir(exist_ok=True)
SAVE_EVERY_N = 5                           # ← 每 N 个 epoch 保存一次
# -----------------------------------------

# ------------ Albumentations 变换 ----------
alb_transform = A.Compose([
    A.Rotate(limit=10, border_mode=cv2.BORDER_CONSTANT, border_value=255, p=0.6),
    A.Perspective(scale=(0.05, 0.1), fit_output=True, p=0.4),
    A.RandomBrightnessContrast(0.1, 0.1, p=0.4),
    A.GaussNoise(var_limit=(5, 20), p=0.3),
])

# ------------ 数据收集 ---------------------
def collect_paths_labels(root: Path):
    paths, labels = [], []
    for fp in root.rglob("*.[jJpP][pPnN][gG]"):
        if m := re.search(r"(\d+)", fp.stem):
            paths.append(str(fp))
            labels.append(int(m.group(1)))
    return np.array(paths), np.array(labels, dtype="int32")

# ----------- numpy_function 封装 ----------
def alb_aug_numpy(gray_img: np.ndarray) -> np.ndarray:
    aug = alb_transform(image=gray_img)["image"]
    aug = cv2.resize(aug, IMG_SIZE[::-1])
    aug = cv2.equalizeHist(aug)
    aug = aug.astype("float32") / 255.0
    return np.expand_dims(aug, -1)

def load_and_preprocess(path: tf.Tensor, label: tf.Tensor, num_classes: int):
    def _py(p_bytes: bytes):
        img = cv2.imdecode(np.fromfile(p_bytes.decode(), np.uint8),
                           cv2.IMREAD_GRAYSCALE)
        return alb_aug_numpy(img)
    img = tf.numpy_function(_py, [path], tf.float32)
    img.set_shape([IMG_SIZE[0], IMG_SIZE[1], 1])
    return img, tf.one_hot(label, num_classes)

# --------------- Focal Loss ---------------
def focal_loss(gamma=2.0, alpha=0.25):
    def _loss(y_true, y_pred):
        ce  = keras.losses.categorical_crossentropy(y_true, y_pred)
        p_t = tf.reduce_sum(y_true * y_pred, axis=-1)
        return alpha * tf.pow(1. - p_t, gamma) * ce
    return _loss

# -------------- 构建模型 ------------------
def build_model(num_classes: int):
    inputs = keras.Input(shape=(*IMG_SIZE, 1))
    x = inputs
    for f in [32, 64, 128, 256]:
        x = keras.layers.Conv2D(f, 3, padding="same", activation="relu")(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.MaxPool2D(2)(x)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.3)(x)
    outputs = keras.layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs)
    model.compile(optimizer=keras.optimizers.Adam(1e-4),
                  loss=focal_loss(),
                  metrics=["accuracy"])
    return model

# ---------- 自定义回调: 周期性保存 ----------
class PeriodicSaver(keras.callbacks.Callback):
    def __init__(self, every_n: int, out_dir: Path):
        super().__init__()
        self.every_n = every_n
        self.out_dir = out_dir

    def on_epoch_end(self, epoch, logs=None):
        if (epoch + 1) % self.every_n == 0:
            path = self.out_dir / f"epoch-{epoch+1:03d}.keras"
            self.model.save(path)
            print(f"💾 Saved checkpoint: {path}")

# --------------- 主入口 -------------------
def main():
    if not IMG_DIR.exists():
        raise FileNotFoundError(f"数据目录不存在: {IMG_DIR}")

    paths, labels = collect_paths_labels(IMG_DIR)
    num_classes = labels.max() + 1
    p_train, p_val, l_train, l_val = train_test_split(
        paths, labels, test_size=0.25, stratify=labels, random_state=SEED)

    def make_ds(p, l, shuffle=False):
        ds = tf.data.Dataset.from_tensor_slices((p, l))
        if shuffle:
            ds = ds.shuffle(len(p), seed=SEED)
        ds = ds.map(lambda path, lab:
                    load_and_preprocess(path, lab, num_classes),
                    num_parallel_calls=tf.data.AUTOTUNE)
        return ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    train_ds = make_ds(p_train, l_train, shuffle=True)
    val_ds   = make_ds(p_val,   l_val)

    uniq = np.unique(labels)
    class_weight = dict(zip(
        uniq, compute_class_weight('balanced', classes=uniq, y=labels)))

    model = build_model(num_classes)
    model.summary()

    cbs = [
        PeriodicSaver(SAVE_EVERY_N, CKPT_DIR),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=6, verbose=1),
        keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=15, restore_best_weights=True, verbose=1),
    ]

    model.fit(train_ds,
              epochs=EPOCHS,
              validation_data=val_ds,
              class_weight=class_weight,
              callbacks=cbs)

    model.save(MODEL_PATH)
    print("✅ 训练完成，最终模型已保存:", MODEL_PATH)

if __name__ == "__main__":
    main()
