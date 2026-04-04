-- 在 Supabase SQL Editor 中运行此脚本

-- 错题集
create table if not exists user_wrong_ids (
  user_id uuid references auth.users on delete cascade,
  question_id text not null,
  created_at timestamptz default now(),
  primary key (user_id, question_id)
);
alter table user_wrong_ids enable row level security;
create policy "own data" on user_wrong_ids for all using (auth.uid() = user_id);

-- 标记题目
create table if not exists user_bookmarks (
  user_id uuid references auth.users on delete cascade,
  question_id text not null,
  created_at timestamptz default now(),
  primary key (user_id, question_id)
);
alter table user_bookmarks enable row level security;
create policy "own data" on user_bookmarks for all using (auth.uid() = user_id);

-- 考试记录
create table if not exists exam_records (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users on delete cascade,
  score int not null,
  total int not null,
  pct int not null,
  mode text not null,
  label text not null,
  topic_stats jsonb,
  created_at timestamptz default now()
);
alter table exam_records enable row level security;
create policy "own data" on exam_records for all using (auth.uid() = user_id);
