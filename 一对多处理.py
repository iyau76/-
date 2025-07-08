#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rebuild_dataset.py
━━━━━━━━━━━━━━━━━━
 1️⃣ 读取  testtabl.xls  → 找到 URL 重复的 ID
 2️⃣ 扫描  图片/女书图片   → 计算 md5 ，找到文件内容重复的 ID
 3️⃣ 合并两种冲突集合 → 生成  id_merge_map.csv   (old_id,new_id)
 4️⃣ 在  图片/女书_merge  下为每张图建立『软链接』；若系统不支持软链接则自动复制文件
     链接(或文件) 命名格式：  newID_oldID.jpg   （便于追溯）

依赖：
    pip install pandas pillow tqdm
    （可选）OpenCV： pip install opencv-python   —若不装也能跑，代码只用到 Pillow
"""

import csv, hashlib, os, shutil, sys
from pathlib import Path
from collections import defaultdict
import pandas as pd
from PIL import Image
from tqdm import tqdm

# ————————>>> ❶ 路径自行修改  <<<————————
XLS_PATH   = Path(r"D:\清华\实践资料\湖南永州\Women_Books-main1\Women_Books-main\表格\testtabl.xls")
IMG_DIR_IN = Path(r"D:\清华\实践资料\湖南永州\Women_Books-main1\Women_Books-main\图片\女书_new")
IMG_DIR_OUT= Path(r"D:\清华\实践资料\湖南永州\Women_Books-main1\Women_Books-main\图片\女书_merge")
# ————————————————————————————————————————

CSV_PATH   = Path("id_merge_map.csv")

# ============ 1. 通过 URL 找重复 =============
print("① 正在扫描 xls…")
df = pd.read_excel(XLS_PATH, usecols=["ID", "WordWB"])
url2ids = defaultdict(list)
for row in df.itertuples(index=False):
    url2ids[row.WordWB].append(int(row.ID))

sets_from_url = [ids for ids in url2ids.values() if len(ids) > 1]

# ============ 2. 通过文件内容找重复 ============
def md5_of(fp: Path) -> str:
    with fp.open("rb") as f:
        return hashlib.md5(f.read()).hexdigest()

print("② 正在计算图片 MD5…")
hash2ids = defaultdict(list)
for img_path in tqdm(list(IMG_DIR_IN.glob("*.jp*"))):
    try:
        h = md5_of(img_path)
        hash2ids[h].append(int(img_path.stem))
    except Exception as e:
        print("⚠️ 读图失败:", img_path, e)

sets_from_md5 = [ids for ids in hash2ids.values() if len(ids) > 1]

# ============ 3. 合并所有冲突集合 ============
# 把若干集合做并查集合并
from itertools import combinations

def merge_sets(list_of_lists):
    merged = []
    for ids in list_of_lists:
        ids = set(ids)
        placed = False
        for s in merged:
            if not s.isdisjoint(ids):
                s |= ids
                placed = True
                break
        if not placed:
            merged.append(ids)
    # 可能需要二次合并
    changed = True
    while changed:
        changed = False
        for a, b in combinations(merged, 2):
            if not a.isdisjoint(b):
                a |= b
                merged.remove(b)
                changed = True
                break
    return merged

groups = merge_sets(sets_from_url + sets_from_md5)
print(f"③ 发现需归并的冲突组 {len(groups)} 组")

# ============ 4. 生成映射表 ============
old2new = {}
for g in groups:
    new_id = min(g)            # 规则：取该组最小 ID 作为主类
    for old_id in g:
        old2new[old_id] = new_id

# 保证单元素（无重复）的 id 也留在映射中（old_id==new_id）
all_ids = {int(p.stem) for p in IMG_DIR_IN.glob("*.jp*")}
for iid in all_ids:
    old2new.setdefault(iid, iid)

print("④ 写出 id_merge_map.csv")
with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["old_id", "new_id", "reason"])
    for oid, nid in sorted(old2new.items()):
        reason = "dup" if oid != nid else ""
        writer.writerow([oid, nid, reason])

# ============ 5. 建软链接 / 复制 ============
print("⑤ 重构数据集…")
IMG_DIR_OUT.mkdir(parents=True, exist_ok=True)

def link_or_copy(src: Path, dst: Path):
    try:
        # Windows 创建软链接需要管理员或开发者模式；用 os.symlink
        os.symlink(src, dst)
    except (OSError, NotImplementedError):
        shutil.copy2(src, dst)

for img_path in tqdm(list(IMG_DIR_IN.glob("*.jp*"))):
    old_id = int(img_path.stem)
    new_id = old2new[old_id]
    dst_name = f"{new_id}_{old_id}{img_path.suffix.lower()}"
    dst_path = IMG_DIR_OUT / dst_name
    if not dst_path.exists():
        link_or_copy(img_path, dst_path)

print("✅ 数据集重构完成  →", IMG_DIR_OUT.resolve())
print("   映射表生成     →", CSV_PATH.resolve())
