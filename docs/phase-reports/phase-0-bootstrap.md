# 阶段复盘 · M0 · 项目初始化

> 通过日期：2026-04-27
> 分支：`feat/m0-bootstrap`
> 提交范围：`f0fe4d3..HEAD`（4 个 commit）

---

## 1. 做了什么

| 任务 | 文件 / 模块 | 一句话说明 |
|---|---|---|
| T1 | `backend/{__init__.py,agents,prompts,api,schemas,mock_data,runtime_data,cache,scripts,tests}` | 完整目录骨架 + .gitkeep |
| T1 | `backend/pyproject.toml` | fastapi/pydantic v2/openai/structlog/pytest 等 dev 依赖 |
| T1 | `backend/main.py` | `create_app()` + CORS + `/api/health` |
| T1 | `backend/config.py` | `load_settings(require_keys)` + `ConfigError` 严格模式，sandbox 安全的 dotenv 加载 |
| T1 | `backend/scripts/check_env.py` | 不回显密钥原文的可达性自检脚本 |
| T1 | `backend/tests/test_health.py` + `test_config.py` | 4 个 pytest 用例 |
| T1 | `docs/phase-reports/{TEMPLATE,README}.md` | 11 阶段复盘的模板与索引 |
| T2 | `frontend/` | Vite 5 + React 19 + TS scaffold |
| T2 | `frontend/{tailwind,postcss}.config.js` + `src/index.css` | Tailwind 3 + design tokens 占位（M2 阶段填全） |
| T2 | `frontend/{package.json,package-lock.json}` | Radix 4 件 + Lucide + Zustand + clsx + tailwind-merge + cva |
| T2 | `frontend/vite.config.ts` | server.proxy['/api'] -> :8000 |
| T2 | `frontend/src/App.tsx` | M0 临时启动页（fetch /api/health 显示状态） |
| T3 | 主仓库 `.venv` (Python 3.11) | 安装 `backend[dev]` 全部依赖 |
| T4 | `README.md` | 项目简介 + 目录结构 + 本地开发 + 复现步骤 + 任务推进 + 红线 |
| T5 | `backend/Dockerfile` | python:3.11-slim + healthcheck + uvicorn |
| T5 | `frontend/Dockerfile` | node:20-alpine + vite dev |
| T5 | `docker-compose.yml` | backend + frontend 双服务 + env_file: .env |
| T5 | `.dockerignore` | 剥掉 .git/.venv/.taskmaster/node_modules/.env |

---

## 2. 如何测试

### 前置

- [x] Python 3.11 已安装（`/opt/homebrew/bin/python3.11` 或 Library Frameworks）
- [x] Node 20+ 已安装（`/opt/homebrew/bin/npm` 11.9.0）
- [x] `.env.example` 已存在（M0 不需要真实密钥即可启动 / 测试，require_keys=False）

### 用例清单

| # | 用例 | 操作 | 预期结果 |
|---|---|---|---|
| 1 | venv 创建 | `python3.11 -m venv .venv && .venv/bin/python --version` | `Python 3.11.x` |
| 2 | 后端依赖安装 | `.venv/bin/pip install -e "./backend[dev]"` | 无 error |
| 3 | 后端 pytest | `.venv/bin/python -m pytest backend/tests/` | 4 passed |
| 4 | 前端依赖安装 | `cd frontend && npm ci` | 0 vulnerabilities |
| 5 | 前端 typecheck | `npx tsc --noEmit` | 0 errors |
| 6 | 前端 build | `npm run build` | 输出 dist/ |
| 7 | 后端启动 | `uvicorn backend.main:app --port 8000` | "Application startup complete" |
| 8 | /api/health | `curl localhost:8000/api/health` | `{"ok":true,"service":"beacon-backend","version":"0.1.0"}` |
| 9 | 配置自检 | `python backend/scripts/check_env.py` | 不回显原文，按状态打印各 key 是否设置 |

---

## 3. 测试结果

### 实测

| # | 用例 | 实测 | 状态 |
|---|---|---|---|
| 1 | venv | Python 3.11.10 ✅ | ✅ |
| 2 | pip install | 含 [notice] 提示 pip 升级；其余无 error | ✅ |
| 3 | pytest | `4 passed in 0.17s` | ✅ |
| 4 | npm ci | `added 153 packages, ... 0 vulnerabilities` | ✅ |
| 5 | tsc | exit 0 | ✅ |
| 6 | vite build | `dist/index.html 0.45kB / index-CPasYJ_Z.js 191.81kB gzip:60.76kB / built in 755ms` | ✅ |
| 7 | uvicorn | "Application startup complete" 正常 | ✅ |
| 8 | /api/health | `{"ok":true,"service":"beacon-backend","version":"0.1.0"}` | ✅ |
| 9 | check_env | 输出 5 项必填❌（`.env` 为空预期）+ 不暴露原文 | ✅ |

### 失败 / 降级项

无失败。已知降级：

- `.env` 文件留作占位符（用户尚未填 DEEPSEEK_API_KEY），M0 不依赖真实密钥即可走通；M4 阶段需要用户填入。
- 未跑 `docker compose up`：本机 docker daemon 不在测试环境内，仅校验 yaml/Dockerfile 结构合法。

### 性能数据

| 指标 | 目标 | 实测 |
|---|---|---|
| pytest 时长 | < 5s | 0.17s |
| Vite build 时长 | < 5s | 0.755s |
| Vite build 产物 | 评委加载 < 2s | 191.81kB（gzip 60.76kB） |
| uvicorn 冷启动 | < 5s | < 2s |
| /api/health p50 | < 100ms | 个位数 ms |

---

## 4. 如何复现

### 从零步骤

```bash
# 1) clone 与切到 M0 commit（主仓库 main）
git clone <repo-url> beacon
cd beacon
git checkout 9314373        # M0 完成提交

# 2) 配置占位 .env（M0 不需要真实 key）
cp .env.example .env
# 不需要编辑

# 3) 后端
python3.11 -m venv .venv
.venv/bin/pip install -e "./backend[dev]"
.venv/bin/python -m pytest backend/tests/         # 期望 4 passed

# 4) 前端
cd frontend
npm ci
npx tsc --noEmit                                  # 期望 exit 0
npm run build                                     # 期望产出 dist/
cd ..

# 5) 后端启动 + 联通验证
.venv/bin/uvicorn backend.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/health          # 期望 {"ok":true,...}
kill %1

# 6) 配置自检
.venv/bin/python backend/scripts/check_env.py     # 期望 5 项必填❌（占位 .env）
```

### 耗时

| 步骤 | 时长（参考） |
|---|---|
| pip install backend | ~ 30 s（首次 · 含下载） |
| npm ci frontend | ~ 25 s（首次） |
| pytest | < 1 s |
| tsc + vite build | ~ 1 s |
| 全套从零 | ~ 1 min |

### 已知坑

1. **macOS 系统默认 `python3` 是 3.9**：必须用 `python3.11` 显式创建 venv，否则 fastapi 等依赖会因为 `pyproject.toml` 限制 `>=3.11` 拒绝安装。
2. **sandbox 禁止跨 worktree 读 `.env`**：`backend.config._load_dotenv_from_project_root` 已加 `try/except PermissionError`，遇到无权限的目录会跳过继续向上找。在主仓库正常运行时，会找到根目录 `.env`。
3. **React 19 + TS 严格模式**：函数组件返回类型不要写 `JSX.Element`（会触发 `Cannot find namespace 'JSX'`），让 TS 自行推断或用 `React.ReactElement`。
4. **Vite proxy 仅在 dev 生效**：生产部署需要在网关层配置 `/api` 路由（M9 处理）。
5. **远端尚未配置**：本仓库还没有 git remote，commit 已在 `feat/m0-bootstrap` 分支，但尚未 push。设置 GitHub remote 之后即可 `git push -u origin feat/m0-bootstrap`。
