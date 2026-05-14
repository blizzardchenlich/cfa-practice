#!/usr/bin/env python3
"""
针对性修复：为选项跨页的题重新做颜色检测
1. 全局扫描 OCR，找每道题"选项在哪一页"
2. 只对无答案题的"选项页"重新转图、做颜色检测
3. 更新 correct_answers.json，再调用 reparse.py
"""
import json, re, subprocess, os
from pathlib import Path
from multiprocessing import Pool
import numpy as np
from PIL import Image

os.chdir(Path(__file__).parent)

ANSWER_PDFS = [
    "/Users/admin/Desktop/8000 for mac/未命名文件夹/CFA一级 kaplan qbank（25版）/答案1册.pdf",
    "/Users/admin/Desktop/8000 for mac/未命名文件夹/CFA一级 kaplan qbank（25版）/答案2册.pdf",
]
TMP_DIR = Path("/tmp/cfa_fix")

RE_Q_ID  = re.compile(r'Question\s+ID\s*[:\s]+(\d+)', re.I)
RE_OPT   = re.compile(r'^([ABC])\)\s*(.*)')
RE_Q_HDR = re.compile(r'Question\s+#\d+', re.I)
RE_MOD   = re.compile(r'\(Module\s+[\d.]+', re.I)


def detect_green(img_path_str, option_y_positions):
    """放宽阈值的绿色检测"""
    try:
        img = Image.open(img_path_str)
        arr = np.array(img)
        h, w = arr.shape[:2]
        g = arr[:,:,1].astype(int)
        r = arr[:,:,0].astype(int)
        b = arr[:,:,2].astype(int)

        # 放宽：原阈值 g>155, g>r*1.15, b<70
        green_mask = (g > 140) & (g > r * 1.08) & (b < 90)
        green_mask[:, :int(w * 0.45)] = False  # 右侧55%（原55%→45%放宽）

        ys, _ = np.where(green_mask)
        if len(ys) == 0:
            return None

        clusters = []
        current = [ys[0]]
        for y in ys[1:]:
            if y - current[-1] < 100:  # 原80→100
                current.append(y)
            else:
                if len(current) > 3:   # 原5→3
                    clusters.append(1.0 - float(np.mean(current)) / h)
                current = [y]
        if len(current) > 3:
            clusters.append(1.0 - float(np.mean(current)) / h)

        if not clusters:
            return None

        best, best_dist = None, 0.12  # 原0.08→0.12
        for letter, opt_y in option_y_positions.items():
            for gc_y in clusters:
                dist = abs(opt_y - gc_y)
                if dist < best_dist:
                    best_dist = dist
                    best = letter
        return best
    except Exception:
        return None


def process_one_page(args):
    """转换一页并检测颜色，返回 {qid: answer}"""
    global_page, opt_map = args  # opt_map: {qid: {letter: y}}
    pdf_idx = 0 if global_page < 10000 else 1
    actual_page = global_page % 10000
    pdf_path = ANSWER_PDFS[pdf_idx]

    TMP_DIR.mkdir(exist_ok=True)
    img_path = TMP_DIR / f"page_{global_page:06d}.png"
    ppm_prefix = str(TMP_DIR / f"p_{global_page:06d}")

    try:
        subprocess.run([
            "pdftoppm", "-r", "200", "-png",
            "-f", str(actual_page), "-l", str(actual_page),
            pdf_path, ppm_prefix
        ], capture_output=True, timeout=30)

        candidates = list(TMP_DIR.glob(f"p_{global_page:06d}-*.png"))
        if candidates:
            candidates[0].rename(img_path)
        if not img_path.exists():
            return {}

        results = {}
        for qid, opt_y in opt_map.items():
            ans = detect_green(str(img_path), opt_y)
            if ans:
                results[qid] = ans

        img_path.unlink(missing_ok=True)
        return results

    except Exception:
        img_path.unlink(missing_ok=True)
        return {}


def main():
    print("加载数据...")
    with open("ocr_cache.json") as f:
        cached = json.load(f)
    with open("correct_answers.json") as f:
        known_answers = json.load(f)

    print(f"已知答案: {len(known_answers)} 条")

    # 全局扫描：每道题的选项在哪一页
    print("全局扫描选项位置...")
    option_pages = {}   # qid → {letter: y, '_page': global_page_num}
    current_qid = None

    for item in sorted(cached, key=lambda x: x[0]):
        page_num, ocr_lines = item[0], item[1]
        for ymin, ymax, xmin, text in sorted(ocr_lines, key=lambda x: x[1], reverse=True):
            text = text.strip()
            if RE_Q_HDR.search(text): current_qid = None; continue
            m = RE_Q_ID.search(text)
            if m: current_qid = m.group(1); continue
            if RE_MOD.search(text): current_qid = None; continue
            m = RE_OPT.match(text)
            if m and xmin < 0.35 and current_qid:
                letter = m.group(1)
                if current_qid not in option_pages:
                    option_pages[current_qid] = {}
                option_pages[current_qid][letter] = (ymin + ymax) / 2.0
                option_pages[current_qid]['_page'] = page_num

    # 找无答案题的选项页
    missing_tasks = {}  # global_page → {qid: {letter: y}}
    for qid, info in option_pages.items():
        if qid in known_answers:
            continue
        opt_y = {k: v for k, v in info.items() if k != '_page'}
        if len(opt_y) < 2:
            continue
        pg = info['_page']
        if pg not in missing_tasks:
            missing_tasks[pg] = {}
        missing_tasks[pg][qid] = opt_y

    print(f"需要处理的页数: {len(missing_tasks)} (共 {sum(len(v) for v in missing_tasks.values())} 道题)")

    # 并行颜色检测
    TMP_DIR.mkdir(exist_ok=True)
    tasks = list(missing_tasks.items())
    new_answers = {}

    with Pool(6) as pool:
        for i, result in enumerate(pool.imap(process_one_page, tasks, chunksize=4)):
            new_answers.update(result)
            if (i+1) % 100 == 0:
                print(f"  {i+1}/{len(tasks)} 页, 已找到 {len(new_answers)} 个新答案")

    print(f"\n颜色检测完成: 新找到 {len(new_answers)} 个答案")

    # 合并更新 correct_answers.json
    known_answers.update(new_answers)
    with open("correct_answers.json", 'w') as f:
        json.dump(known_answers, f)
    print(f"correct_answers.json 更新: 共 {len(known_answers)} 条")

    # 重新解析
    print("\n重新解析题目...")
    import reparse
    reparse.main()


if __name__ == '__main__':
    main()
