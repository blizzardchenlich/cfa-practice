#!/usr/bin/env python3
"""
用 DeepSeek 为每道题生成解题思路，写入 questions.json 的 tips 字段
用法: DEEPSEEK_API_KEY=sk-xxx python3 generate_tips.py
"""
import os, json, time, sys
from pathlib import Path
from openai import OpenAI

API_KEY  = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL    = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"

SYSTEM_PROMPT = """你是一位专业的 CFA Level 1 辅导老师。
用户会给你一道选择题（题目、三个选项、正确答案、Kaplan原版解析），
请用中文写出简洁的「解题思路」，格式严格如下（不要输出多余内容）：

**考查要点**：[1-2句，说明本题考的是哪个知识点/公式]
**解题步骤**：
1. [第一步]
2. [第二步]
3. [第三步（如适用）]
**易错提示**：[1句，常见错误或陷阱]"""

def make_prompt(q: dict) -> str:
    opts = "\n".join(f"{k}) {v}" for k, v in q["options"].items() if v)
    return (
        f"题目：{q['question']}\n\n"
        f"选项：\n{opts}\n\n"
        f"正确答案：{q['correct']}\n\n"
        f"Kaplan解析：{q.get('explanation','（无）')}"
    )

def generate_tip(client: OpenAI, q: dict) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": make_prompt(q)},
        ],
        max_tokens=400,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()

def main():
    if not API_KEY:
        print("错误：请设置环境变量 DEEPSEEK_API_KEY")
        print("  export DEEPSEEK_API_KEY=sk-xxx")
        sys.exit(1)

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    qfile = Path("questions.json")
    with open(qfile, encoding="utf-8") as f:
        data = json.load(f)

    questions = data["questions"]
    need = [q for q in questions if not q.get("tips")]
    total = len(need)
    print(f"共 {len(questions)} 题，需要生成解题思路：{total} 题")
    if total == 0:
        print("全部已生成，无需重跑。")
        return

    # 估算费用（deepseek-chat 约 $0.14/MTok in, $0.28/MTok out）
    est = total * 300 / 1e6 * 0.14 + total * 300 / 1e6 * 0.28
    print(f"预计费用：~${est:.2f}  (deepseek-chat)")
    print("按 Enter 继续，Ctrl+C 取消...")
    input()

    done = 0
    errors = 0
    save_every = 50  # 每50题保存一次

    for q in need:
        try:
            tip = generate_tip(client, q)
            q["tips"] = tip
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{total} ({done/total*100:.1f}%)", flush=True)
            if done % save_every == 0:
                with open(qfile, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  [已保存进度]")
            time.sleep(0.1)   # 避免触发频率限制
        except Exception as e:
            errors += 1
            print(f"  ! 跳过 {q['id']}: {e}")
            if errors > 20:
                print("错误太多，中止。检查 API Key 是否正确。")
                break
            time.sleep(2)

    # 最终保存
    with open(qfile, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n完成！生成 {done} 题，失败 {errors} 题")
    print("已更新 questions.json，运行以下命令推送到线上：")
    print("  cd ~/Desktop/CFA练习系统 && git add questions.json && git commit -m '添加AI解题思路' && git push")

if __name__ == "__main__":
    main()
