import pandas as pd
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier


def word_WBooks(words_input):
    # 拆分字符串word
    words = [word_one for word_one in words_input]
    WBooks_path = r"图片\女书_new"
    Word_path = r"表格\testtabl.xls"
    chinese_xls = pd.read_excel(Word_path, usecols=['ID', 'WordRaw'])
    images_word = []
    for word in words:
        words_ID = chinese_xls[chinese_xls['WordRaw'] == word]['ID']
        if words_ID.empty:
            image_word = Image.open(r"Image\empty.png")
            image_word = image_word.resize((50, 120))
            images_word.append(image_word)
        else:
            for word_ID in words_ID:
                image_word = Image.open(r"图片\女书_new\{}.jpg".format(word_ID))
                image_word = image_word.resize((50, 120))
                images_word.append(image_word)

    return images_word

def WBooks_word(file_path: str) -> str:
    """
    整页女书图片 → CNN 识别 → 汉字串
    ------------------------------------------------------------
    - 先用 Image_process.split_image 切字
    - CNN 输出 **连续 idx** → 通过 id_mapping.json 还原到旧 ID
    - 再用 Excel 表把旧 ID 映射到汉字
    """
    import json, cv2, keras, Image_process as impro

    # ---------- 1. 模型 & 对照表 ----------
    global _CNN_MODEL, _ID2CHAR, _IDX2ID
    if '_CNN_MODEL' not in globals():
        _CNN_MODEL = keras.models.load_model("model_CNN.h5", compile=False)
        print("✅ CNN 模型已载入")

    if '_ID2CHAR' not in globals():
        df = pd.read_excel(r"表格/testtabl.xls", usecols=["ID", "WordRaw"])
        df = df.drop_duplicates(subset="ID", keep="first")
        _ID2CHAR = dict(zip(df["ID"].astype(int), df["WordRaw"].astype(str)))

    if '_IDX2ID' not in globals():
        with open("id_mapping.json", encoding="utf-8") as f:
            _IDX2ID = {
                int(k): int(v) for k, v in json.load(f)["idx2id"].items()
            }

    model   = _CNN_MODEL
    id2char = _ID2CHAR
    idx2id  = _IDX2ID

    # ---------- 2. 切图 ----------
    crops = impro.split_image(file_path)          # ndarray or list
    if crops is None or len(crops) == 0:          # ← 安全判断
        return ""

    # ---------- 3. 预处理 ----------
    X = []
    for g in crops:
        img = cv2.resize(g, (480, 220))
        X.append(np.expand_dims(img.astype("float32") / 255.0, -1))
    X = np.stack(X, 0)

    # ---------- 4. 预测 ----------
    preds    = model.predict(X, verbose=0)
    idx_pred = preds.argmax(axis=1)               # 连续 idx

    for idx, old in zip(idx_pred, [idx2id[i] for i in idx_pred]):
        print(f"idx={idx:<4}  id={old:<5}  char={id2char.get(old,'□')}")
    # ---------- 5. idx → oldID → 汉字 ----------
    chars = []
    for idx in idx_pred:
        old_id = idx2id.get(int(idx), -1)         # 不存在给 -1
        chars.append(id2char.get(old_id, "□"))
    return "".join(chars)




if __name__ == '__main__':
    file_path = r"图片\测试图片\屏幕截图 2024-03-29 105236.png"
    print(WBooks_word(file_path))