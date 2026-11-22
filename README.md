# CFA Level I 刷题系统

> 本文件是给 AI 助手（Claude / Fable 5.2）的项目导览。读完此文件即可理解项目全貌并开始维护。

## 这是什么

一个 CFA Level I 个人备考刷题系统，包含题库练习、模拟考试、错题集、收藏夹、考试记录、三色笔记。纯前端静态站点 + Supabase 云后端，部署在 GitHub Pages。

## 快速上手（新电脑）

1. **运行本地预览**：在项目文件夹下 `python3 -m http.server 8000`，浏览器打开 `http://localhost:8000`
2. **部署到线上**：`git push origin main`，约 1 分钟后 GitHub Pages 生效
3. **线上地址**：https://blizzardchenlich.github.io/cfa-practice/
4. **GitHub 仓库**：https://github.com/blizzardchenlich/cfa-practice

## 用户数据说明（重要）

**所有用户刷题数据都存在 Supabase 云端，不在本地。** 包括：

- 错题集（`user_wrong_ids`）
- 收藏夹（`user_bookmarks`）
- 已做题记录（`user_answered_ids`）
- 考试记录（`exam_records`，含分数和分科目统计）

用户 **nadachen** 的数据已在云端。只要代码连的是同一个 Supabase 项目（配置写死在 `index.html` 第 512-513 行），nadachen 在任何设备登录后数据自动同步。**迁移项目不需要导出数据。**

## 技术栈

- 前端：纯 HTML/CSS/JS，无框架
- 后端：Supabase（Auth + PostgreSQL），通过 CDN 引入 `@supabase/supabase-js@2`
- 题库：`questions.json`（3.1 MB，Kaplan QBank 2025，OCR 提取）
- 部署：GitHub Pages

## 文件结构

| 文件 | 说明 |
|------|------|
| `index.html` | 主应用（登录、题库、考试、错题集、收藏、考试记录），1451 行 |
| `questions.json` | 题库数据，含 tips 字段 |
| `notes.html` | Book 1 三色笔记（R1–R19：Quantitative Methods + Economics） |
| `notes_b2.html` | Book 2 三色笔记（R20–R28：Portfolio Mgmt P1 + Corporate Issuers） |
| `notes_b3.html` | Book 3 三色笔记（R29–R48：FSA + Equity Investments） |
| `notes_b4.html` | Book 4 三色笔记（R49–R77：Fixed Income + Derivatives） |
| `notes_b5.html` | Book 5 三色笔记（R78–R93：Alternatives + Portfolio Mgmt P2 + Ethics） |
| `supabase_setup.sql` | 数据库建表脚本（4 张表 + RLS 策略） |
| `ARCHITECTURE.md` | 详细技术文档，修改代码前必读 |

## Supabase 配置

- **Project URL**: `https://plqhtgxacfgwthzvvqit.supabase.co`
- **Publishable Key**: `sb_publishable_7QbA8OiWeCjqfrKtKXZcrA_eBCV3UYS`
- **Email Confirmation**: 已关闭
- **Custom SMTP**: 已配置 Resend（`smtp.resend.com:465`）
- **控制台**: https://supabase.com/dashboard/project/plqhtgxacfgwthzvvqit

## Auth 机制

用户输入用户名，代码拼接 `@cfastudy.com` 作为 email 传给 Supabase：
- 登录：`sb.auth.signInWithPassword({ email: username + '@cfastudy.com', password })`
- 注册：`sb.auth.signUp({ email: username + '@cfastudy.com', password })`
- 显示时 `updateUserBar()` 去掉 `@cfastudy.com` 后缀

手动在 Supabase 控制台创建用户后需运行：
```sql
UPDATE auth.users SET email_confirmed_at = now() WHERE email LIKE '%@cfastudy.com';
```

## 常见维护任务

| 需求 | 操作 |
|------|------|
| 加新题目 | 编辑 `questions.json`，按现有 question 对象格式追加 |
| 改某题 tips | 编辑 `questions.json` 对应 question 的 `tips` 字段 |
| 更新笔记内容 | 编辑对应 `notes_b*.html` |
| 新建用户 | Supabase 控制台 Authentication → Users → Add user，email 填 `用户名@cfastudy.com`，然后运行上面的 SQL |
| 查 nadachen 数据 | Supabase 控制台 Table Editor → 选表 → filter `user_id` |
| 改 CFA 权重 | `index.html` 第 601-612 行 `CFA_WEIGHTS` 对象 |
| 改考试时长/题数 | `index.html` 中搜索 `examMode`、`secondsLeft`、`total` 相关逻辑 |

## 依赖关系

- 运行时依赖：CDN 加载 `@supabase/supabase-js@2`（需联网）
- 无构建步骤、无 npm 依赖、无编译
- 题库 `questions.json` 通过 `fetch()` 动态加载

详细架构、数据流、关键函数位置见 **[ARCHITECTURE.md](./ARCHITECTURE.md)**。
