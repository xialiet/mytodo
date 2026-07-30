# MyTodo · 个人待办 · 打卡 · 时间流

一个自托管的轻量级个人效率工具，把**待办管理**和**每日打卡**合二为一。
基于 FastAPI + SQLite，支持 PWA（可添加到手机主屏幕，离线可用），Docker 一键部署。

## ✨ 功能

### 📝 待办管理
- 创建 / 编辑 / 完成待办，支持**子任务**（可拖拽排序）
- **分类**管理（自定义名称 + 颜色）
- **优先级**（高 / 中 / 低）、**截止日期**、**开始日期**
- **循环任务**：每日 / 每周 / 每两周 / 每月 / 自定义间隔
- 全文**搜索**、**时间流**视图

### ✅ 每日打卡
- 自定义打卡项（图标、颜色、每日目标次数）
- 打卡日志，支持备注
- 打卡数据**统计**页

### 📱 PWA
- 可安装到手机主屏幕，独立全屏运行
- Service Worker 离线缓存

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
│   │   ├── api.py           # REST API
│   │   └── pages.py         # 页面路由
│   ├── templates/           # Jinja2 HTML 模板
│   └── static/              # 静态资源（图标、字体、PWA 配置）
├── data/                    # SQLite 数据库（运行时生成，已 gitignore）
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 📡 API

所有接口以 `/api` 开头，主要资源：

| 资源 | 方法 |
|------|------|
| `/api/todos` | GET / POST |
| `/api/todos/{id}` | GET / PATCH / DELETE |
| `/api/todos/{id}/complete` | POST |
| `/api/todos/{id}/subtasks` | GET / POST |
| `/api/categories` | GET / POST |
| `/api/checkin/items` | GET / POST |
| `/api/checkin/items/{id}/log` | POST |

启动后访问 `/docs` 可查看完整的交互式 API 文档（FastAPI 自动生成）。

## 📄 License

MIT
