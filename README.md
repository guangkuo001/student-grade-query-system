# 学生成绩查询系统

一个基于 Flask 的学生成绩查询系统，支持 SQLite（本地）和 PostgreSQL（生产）。

## 功能

- 按学号查询学生信息和成绩
- 展示语文/数学/英语成绩
- 自动计算平均分
- 首次运行自动初始化示例数据
- 支持管理员接口进行增删改（学生/成绩）

## 快速启动

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动服务

```bash
python app.py
```

3. 打开浏览器访问

```text
http://127.0.0.1:5000
```

## 一键自动部署（推荐）

首次部署：

```bash
chmod +x deploy.sh stop.sh status.sh
./deploy.sh
```

常用命令：

```bash
./status.sh   # 查看服务状态
./stop.sh     # 停止服务
./deploy.sh   # 重新部署/启动
```

部署后服务会在后台运行，日志在：

```text
logs/app.log
```

说明：

- 脚本默认从 `5000` 开始，若端口被占用会自动切换到下一个可用端口
- 也可手动指定端口，例如：`APP_PORT=8000 ./deploy.sh`

## 部署到 Vercel

1. 安装并登录 Vercel CLI

```bash
npm i -g vercel
vercel login
```

2. 在项目目录执行部署

```bash
vercel
```

首次会提示选择项目配置，保持默认即可。

3. 生产环境发布

```bash
vercel --prod
```

### 说明

- 已提供 `vercel.json` 和 `api/index.py`，可直接作为 Flask Serverless 部署
- 当前项目使用 SQLite 仅做成绩查询演示；在 Vercel 上建议后续改成云数据库（如 Supabase / Neon / PlanetScale）

## 更自动化部署（推荐 Render）

本项目已提供 `render.yaml`，可直接用 GitHub 自动部署。

### 一次性配置

1. 打开 [Render Dashboard](https://dashboard.render.com/)
2. 选择 `New +` -> `Blueprint`
3. 连接你的 GitHub 仓库：`guangkuo001/student-grade-query-system`
4. 保持默认配置，点击部署

### 自动化效果

- 每次 push 到 `main`，Render 会自动重新部署
- 不需要本地再手动运行 `deploy.sh`
- Blueprint 会自动创建 PostgreSQL，并注入 `DATABASE_URL`

### 备注

- 本地默认使用 SQLite（`grades.db`）
- Render 线上默认使用 PostgreSQL 持久化

## 管理接口（增删改）

如果设置了环境变量 `ADMIN_TOKEN`，请求头需要带：

```text
X-Admin-Token: 你的Token
```

### 新增学生

`POST /api/admin/student`

```json
{
  "student_id": "2026999",
  "name": "赵六"
}
```

### 删除学生

`DELETE /api/admin/student/2026999`

### 新增成绩

`POST /api/admin/score`

```json
{
  "student_id": "2026001",
  "subject": "物理",
  "score": 89
}
```

### 修改成绩

`PUT /api/admin/score`

```json
{
  "student_id": "2026001",
  "subject": "数学",
  "score": 93
}
```

### 删除成绩

`DELETE /api/admin/score?student_id=2026001&subject=数学`

## 示例学号

- 2026001
- 2026002
- 2026003

## 接口说明

- `GET /api/query?student_id=学号`

成功返回示例：

```json
{
  "student_id": "2026001",
  "name": "张三",
  "scores": [
    { "subject": "数学", "score": 88 },
    { "subject": "英语", "score": 95 },
    { "subject": "语文", "score": 92 }
  ],
  "average": 91.67
}
```
