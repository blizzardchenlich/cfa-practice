# 架构详解 — CFA Level I 刷题系统

> 本文件为 AI 助手（Claude / Fable 5.2）提供修改代码所需的详细技术参考。
> `index.html` 是单文件应用（1451 行），所有 JS 逻辑内联在 `<script>` 标签内。下文行号基于打包时的快照，可能有偏移，用函数名/关键字搜索定位最可靠。

## 1. Supabase 初始化（index.html ~511-516）

```js
const SUPABASE_URL      = 'https://plqhtgxacfgwthzvvqit.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_7QbA8OiWeCjqfrKtKXZcrA_eBCV3UYS';
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false }
});
let currentUser = null;
```

- `persistSession: true` → 用 localStorage 存 session，刷新页面不丢登录
- `detectSessionInUrl: false` → 不从 URL hash 读 OAuth 回调（本项目用用户名密码，不需要）

## 2. 数据库表结构（supabase_setup.sql）

四张表，全部启用 RLS（`auth.uid() = user_id`），用户只能访问自己的数据。

| 表 | 主键 | 用途 |
|----|------|------|
| `user_wrong_ids` | `(user_id, question_id)` | 错题集 |
| `user_bookmarks` | `(user_id, question_id)` | 收藏夹 |
| `user_answered_ids` | `(user_id, question_id)` | 已做题（跨设备同步） |
| `exam_records` | `id (uuid)` | 考试记录（score/total/pct/mode/label/topic_stats jsonb） |

`user_id` 外键 `auth.users on delete cascade`，删用户时数据级联清除。

## 3. Auth 流程（index.html ~519-526, 1380-1425）

```
用户输入 username + password
  → email = username + '@cfastudy.com'
  → 登录: sb.auth.signInWithPassword({ email, password })
  → 注册: sb.auth.signUp({ email, password })
  → onAuthStateChange 监听 SIGNED_IN / TOKEN_REFRESHED / SIGNED_OUT
```

- `updateUserBar()`（~1420）：显示时 `email.replace('@cfastudy.com', '')` 还原用户名
- 登录成功后顺序：`loadUserData()` → `loadQuestions()` → `showHome()`
- 退出：`sb.auth.signOut()` + 清空 `wrongIds`/`bookmarkIds` → `showAuth()`

## 4. 用户数据加载与持久化（index.html ~540-598）

### loadUserData()（~546）
并发查询三张表，加载到内存 Set：
```js
const [w, b, a] = await Promise.all([
  sb.from('user_wrong_ids').select('question_id').eq('user_id', currentUser.id),
  sb.from('user_bookmarks').select('question_id').eq('user_id', currentUser.id),
  sb.from('user_answered_ids').select('question_id').eq('user_id', currentUser.id),
]);
wrongIds    = new Set(w.data.map(r => r.question_id));
bookmarkIds = new Set(b.data.map(r => r.question_id));
answeredIds = new Set(a.data.map(r => r.question_id));
```

降级：如果表不存在或网络失败，`loadAnsweredFromStorage()` 从 `localStorage['answered_' + currentUser.id]` 读取已做题。

### 写入云端
| 动作 | 函数 | 操作 |
|------|------|------|
| 标记已做 | `markQuestionAnswered(qid)` ~575 | `upsert` 到 `user_answered_ids`，不等待不阻塞 |
| 加入错题 | `saveWrongIds(qid)` ~583 | `upsert` 到 `user_wrong_ids` |
| 收藏/取消 | `saveBookmarkIds(qid, add)` ~589 | `upsert` 或 `delete` `user_bookmarks` |

所有写入都基于 `currentUser.id`，不传 `created_at`（数据库默认 `now()`）。

## 5. 题库加载（index.html ~615-624）

```js
const resp = await fetch('questions.json?v=' + Date.now());  // 防缓存
allQuestions = data.questions || [];
```

`questions.json` 结构：
```json
{
  "questions": [
    {
      "id": "...",
      "topic": "Quantitative Methods",
      "question": "...",
      "choices": ["A...","B...","C..."],
      "answer": "B",
      "explanation": "...",
      "tips": "..."
    }
  ]
}
```

## 6. 考试模式与记录（index.html ~1287-1295）

考试结束写入 `exam_records`：
```js
sb.from('exam_records').insert({
  user_id: currentUser.id,
  score: correct,
  total,
  pct,
  mode,        // 'exam' | 'train'
  label,       // 考试标签
  topic_stats  // jsonb: 各科目正确率
});
```

读取历史记录（~660）：`sb.from('exam_records').select('*').eq('user_id', currentUser.id)`。

## 7. CFA 权重（index.html ~601-612）

```js
const CFA_WEIGHTS = {
  'Ethics and Professional Standards': 0.15,
  'Quantitative Methods': 0.12,
  'Economics': 0.10,
  'Financial Statement Analysis': 0.20,
  'Corporate Issuers': 0.08,
  'Equity Investments': 0.10,
  'Fixed Income': 0.11,
  'Derivatives': 0.05,
  'Alternative Investments': 0.03,
  'Portfolio Management': 0.06,
};
```

用于模拟考试按权重抽题。改权重在这里。

## 8. 三色笔记

`notes.html` / `notes_b*.html` 是独立静态页面，无 Supabase 依赖，无 JS 逻辑（纯 HTML 内容）。

- Book 1 (notes.html): R1–R19
- Book 2 (notes_b2.html): R20–R28
- Book 3 (notes_b3.html): R29–R48
- Book 4 (notes_b4.html): R49–R77
- Book 5 (notes_b5.html): R78–R93

更新笔记内容直接编辑对应 HTML 的文本节点即可。

## 9. 部署

```
本地修改 → git add → git commit → git push origin main
→ GitHub Pages 自动构建（~1 分钟）→ 线上生效
```

无需 CI/CD 配置，GitHub Pages 直接服务仓库根目录静态文件。

## 10. 安全注意事项

- `SUPABASE_ANON_KEY` 是 publishable key，设计上是公开的（前端可见），安全性靠 RLS 保证
- RLS 策略 `auth.uid() = user_id` 确保用户只能读写自己的数据
- 不要在代码里放 service_role key（那是管理员密钥，仅限服务端）
- `questions.json` 是 OCR 提取的 Kaplan QBank 内容，仅限个人备考使用

## 11. 故障排查

| 症状 | 排查方向 |
|------|----------|
| 登录失败 | Supabase 控制台 → Authentication → Users，确认用户存在且 `email_confirmed_at` 非空 |
| 数据加载为空 | Table Editor 检查对应表是否有 nadachen 的行；浏览器 Console 看是否有 RLS 报错 |
| 题库加载失败 | 确认 `questions.json` 与 `index.html` 同目录；检查 fetch 路径 |
| 考试记录不显示 | 检查 `exam_records` 表 `user_id` 是否匹配 `currentUser.id` |
| 线上缓存旧版本 | `questions.json?v=Date.now()` 已防缓存；HTML 改动可能需要强刷或等 CDN 过期 |
