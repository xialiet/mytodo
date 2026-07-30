# MyTodo · 自主掌控的个人数据中枢

> 一个**自托管**的轻量级个人效率系统：待办管理 + 每日打卡 + 时间流。
> 数据 100% 归你，无云端锁定，无第三方依赖。
> **开放的 REST API 让任何 AI Agent 都能读取你的数据、分析规律、发送提醒，甚至代你创建任务。**

---

## 🎯 设计理念

MyTodo 不是一个普通的待办 App，它的核心定位是 **"你的 AI Agent 的个人数据中心"**：

### 1. 全自主管理（You own everything）

- **自托管** —— 跑在你自己的机器/服务器上，数据存在本地 SQLite，不经手任何第三方
- **完全可控** —— 没有订阅费、没有账号体系、没有数据上传、没有"服务停止"风险
- **数据归你** —— 一个 `.db` 文件就是全部，随时可备份、可迁移、可离线
- **PWA** —— 可装到手机主屏幕，全屏运行，离线可用

### 2. 联动 AI Agent（Agent-ready by design）

- **开放 REST API** —— 所有数据（待办、打卡、分类、日志）都能通过 HTTP 读写
- **双向交互** —— Agent 既能**读取**（查待办、分析打卡规律）也能**写入**（创建任务、帮你打卡）
- **零锁定** —— 标准 JSON 接口，任何能发 HTTP 请求的 Agent / 脚本 / 自动化工具都能接入

> 这意味着你的 AI 助手可以做到：**读取你的待办 → 分析你的行为规律 → 主动提醒 → 甚至帮你规划下一步**。
> MyTodo 提供数据和能力，Agent 提供智能，两者组合 = 你的个人数字分身。

---

## ✨ 功能

### 📝 待办管理
- 创建 / 编辑 / 完成待办，支持**子任务**（可拖拽排序）
- **分类**管理（自定义名称 + 颜色）
- **优先级**（高 / 中 / 低）、**截止日期**、**开始日期**
- **循环任务**：每日 / 每周 / 每两周 / 每月 / 自定义间隔（漏做可补卡，自动顺延）
- 全文**搜索**、**时间流**视图

### ✅ 每日打卡
- 自定义打卡项（图标、颜色、每日目标次数）
- 打卡日志，支持备注
- 打卡数据**统计**（连续天数、热力图）

### 📱 PWA
- 可安装到手机主屏幕，独立全屏运行
- Service Worker 离线缓存

---

## 🤖 AI Agent 集成

MyTodo 的全部能力都通过 REST API 暴露。下面是几个典型场景，展示 AI Agent 如何接入。

### 场景一：读取 + 分析 —— "我最近状态如何？"

Agent 读取近 30 天打卡数据和待办完成情况，分析规律：

```bash
# 1. 取近 30 天每日打卡次数（分析坚持度、连续天数）
curl "http://your-host:3090/api/checkin/logs/batch?days=30"

# 2. 取所有待办（含完成状态）
curl "http://your-host:3090/api/todos"

# 3. 取所有打卡项定义
curl "http://your-host:3090/api/checkin/items"
```

Agent 拿到这些 JSON 后，就能总结出："你这周打卡完成率 85%，比上周高；有 3 个高优先级待办逾期了，建议优先处理 X。"

### 场景二：主动提醒 —— "今天还有什么没做？"

利用专门的**逾期查询**端点，Agent 可以做精准提醒：

```bash
# 查所有逾期未完成的待办（提醒功能的核心）
curl "http://your-host:3090/api/todos?overdue=true"

# 查今天某项打卡做了几次
curl "http://your-host:3090/api/checkin/items?date_str=2026-07-30"
```

Agent 据此推送通知：「你有 2 个待办今天截止，还有「运动」打卡今天还没做。」

### 场景三：代写 —— Agent 帮你创建任务 / 打卡

API 支持写入，Agent 可以反向操作：

```bash
# Agent 帮你新建一个待办
curl -X POST "http://your-host:3090/api/todos" \
  -H "Content-Type: application/json" \
  -d '{"title":"给项目写周报","priority":"high","due_date":"2026-08-01"}'

# Agent 帮你打卡
curl -X POST "http://your-host:3090/api/checkin/items/3/log" \
  -H "Content-Type: application/json" \
  -d '{"note":"晨跑 5km"}'
```

### 完整 API 一览

所有接口以 `/api` 开头，启动后访问 `/docs` 可查看**交互式 API 文档**（FastAPI 自动生成）。

| 资源 | 方法 | 说明 |
|------|------|------|
| `/api/todos` | GET | 列出待办（支持 `status`/`category_id`/`q`/`overdue`/`limit` 筛选） |
| `/api/todos` | POST | 创建待办 |
| `/api/todos/{id}` | GET / PATCH / DELETE | 查 / 改 / 删单个待办 |
| `/api/todos/{id}/complete` | POST | 标记完成（循环任务自动生成下一期） |
| `/api/todos/{id}/reopen` | POST | 重开 |
| `/api/todos/{id}/subtasks` | GET / POST | 子任务列表 / 新增 |
| `/api/subtasks/{id}` | PATCH / DELETE | 改 / 删子任务 |
| `/api/categories` | GET / POST / PATCH / DELETE | 分类 CRUD |
| `/api/checkin/items` | GET / POST | 打卡项列表 / 新增 |
| `/api/checkin/items/{id}` | PATCH / DELETE | 改 / 删打卡项 |
| `/api/checkin/items/{id}/log` | POST | 记一次打卡 |
| `/api/checkin/items/{id}/logs?days=N` | GET | 近 N 天每日打卡次数（热力图/连续天数） |
| `/api/checkin/logs/batch?days=N` | GET | 所有打卡项近 N 天数据（批量分析） |

---

## 🛠 技术栈

- **后端**：[FastAPI](https://fastapi.tiangolo.com/) 0.115 + Uvicorn
- **数据库**：SQLite（[SQLAlchemy 2.0](https://www.sqlalchemy.org/) async + aiosqlite）
- **前端**：Jinja2 模板 + Tailwind CSS（CDN）+ 原生 JS
- **部署**：Docker / Docker Compose

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/xialiet/mytodo.git
cd mytodo
docker compose up -d
```

打开 `http://localhost:3090` 即可使用。数据持久化在 `./data/` 目录。

### 方式二：本地运行

```bash
git clone https://github.com/xialiet/mytodo.git
cd mytodo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 3090
```

---

## 📂 项目结构

```
mytodo/
├── app/
│   ├── main.py              # 应用入口、路由注册
│   ├── database.py          # 数据库连接
│   ├── models.py            # 数据模型（Todo / SubTask / Category / CheckinItem / CheckinLog）
│   ├── schemas.py           # Pydantic 模型
│   ├── seed.py              # 首次启动的示例数据
│   ├── routers/
│   │   ├── api.py           # REST API（Agent 集成入口）
│   │   └── pages.py         # 页面路由
│   ├── templates/           # Jinja2 HTML 模板
│   └── static/              # 静态资源（图标、字体、PWA 配置）
├── data/                    # SQLite 数据库（运行时生成，已 gitignore）
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 📄 License

MIT
