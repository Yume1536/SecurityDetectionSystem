# 多模态大模型对抗样本安全检测系统

本项目实现了一个**前后端分离**的安全检测平台，支持图像+文本输入，后端联动独立 Flask 算法服务执行基于 PIP（Probe Irrelevant Prompt）的注意力异常检测，并提供可视化、历史记录和 PDF 报告下载。

## 一、系统架构

- **前端（Html + CSS + JS + ECharts）**：登录注册、上传检测、热力图与注意力曲线可视化、历史记录、报告下载。
- **业务后端（Python Flask）**：用户鉴权、上传处理、算法服务调度、记录入库、报告生成。
- **算法服务（独立 Flask）**：加载 PyTorch 预训练模型，执行 PIP 检测逻辑并返回 `is_adversarial/confidence/heatmap/attention_data`。
- **数据库（MySQL 8.0）**：存储用户账号与检测记录。

## 二、功能模块

1. **用户管理模块**
   - 注册：用户名 + 密码（后端 MD5 存储）
   - 登录：前端凭用户名密码请求后端，后端 MD5 比对，成功后返回用户信息。
2. **图像上传检测模块**
   - 必传图像，可选文本。
   - 后端将数据转发给算法服务 `/detect`。
3. **可视化分析模块**
   - ECharts 展示图像/文本注意力曲线对比。
   - 展示扰动定位热力图。
4. **检测记录管理模块**
   - 列表查询、详情查看。
5. **安全报告生成模块**
   - 按记录生成 PDF，包含输入信息、检测结果、热力图。

## 三、目录结构

```text
SecurityDetectionSystem/
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── uploads/
│   ├── reports/
│   └── static/heatmaps/
├── algorithm_service/
│   └── app.py
├── sql/
│   └── init.sql
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 四、运行方式

### 方式A：本地直接运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动 MySQL 8.0，并创建数据库 `security_detection`，执行 `sql/init.sql`。

3. 启动算法服务：
```bash
python algorithm_service/app.py
```

4. 启动后端服务：
```bash
python backend/app.py
```

5. 打开 `frontend/index.html`（建议使用 VSCode Live Server 或 nginx 静态服务），默认请求：
- 后端：`http://127.0.0.1:5000`
- 算法服务：`http://127.0.0.1:5001`

### 方式B：Docker Compose 一键运行

```bash
docker compose up --build
```

## 五、核心流程（与你描述一致）

1. 登录认证（用户名+密码，后端 MD5 简单比对）。
2. 上传图像与文本（FormData）。
3. 后端预处理并调度算法服务。
4. 算法服务执行 PIP 检测，输出对抗判定、置信度、热力图、注意力数据。
5. 后端入库并返回前端。
6. 前端展示结果与可视化。
7. 用户查看历史记录与详情。
8. 一键生成并下载 PDF 报告。

## 六、接口简表

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/detect`
- `GET /api/records/<user_id>`
- `GET /api/records/detail/<record_id>`
- `GET /api/report/<record_id>`

## 七、安全说明

当前实现按你的要求采用了 **MD5 简单比对**。实际生产建议升级为：
- `bcrypt/argon2` 哈希 + 加盐
- 服务端 Session/JWT 与过期机制
- 上传内容安全校验（MIME/病毒扫描）
- 鉴权中间件与权限控制
