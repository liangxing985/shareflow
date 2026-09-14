# ShareFlow 个人收款分账系统

> 个人微信/支付宝收款 + 智能分账 + 批量结算管理系统

## 项目简介

ShareFlow 是一套面向个人和小团队的收款分账管理系统。通过**记账式分账**模式，系统不触碰资金池，只管理分账规则和结算记录，规避"二清"合规风险。

### 核心特性

- **多渠道收款管理**：支持微信、支付宝、银行卡收款账户管理
- **智能分账引擎**：支持固定比例分账、平台抽成、多级分账（一级/二级）
- **批量结算**：一键生成转账清单，手动转账后登记，支持批量导出Excel
- **订单管理**：支持手动录入、API接入（业务系统对接）
- **分账方管理**：分账方信息、收款方式、余额追踪
- **对账管理**：微信/支付宝对账单上传与差异核对
- **数据看板**：收款趋势、分账统计、平台抽成分析
- **多用户权限**：管理员/运营主管/财务/运营/只读五种角色

## 技术栈

### 后端
- Python 3.11 + FastAPI 0.115
- SQLAlchemy 2.0 (异步) + MySQL 8.0
- Redis 7 + Celery 5.4
- JWT认证 + bcrypt密码哈希
- cryptography Fernet 敏感数据加密

### 前端
- Vue 3.4 + TypeScript + Vite 5
- Element Plus 2.5 + ECharts 5.5
- Pinia 状态管理 + Vue Router 4

### 部署
- Docker + Docker Compose 一键部署
- Nginx 反向代理

## 快速开始

### 方式一：Docker Compose 部署（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd shareflow

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，修改 SECRET_KEY 和 ENCRYPTION_KEY（必须32位以上随机字符串）

# 3. 启动服务
docker compose up -d

# 4. 访问
# 前端: http://localhost
# 后端API: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 方式二：本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
# 配置环境变量
export DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/shareflow?charset=utf8mb4"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="your-secret-key-at-least-32-chars"
export ENCRYPTION_KEY="your-encryption-key-at-least-32-chars"
uvicorn app.main:app --reload --port 8000

# 前端（新开终端）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

## 首次使用

1. 访问系统后，第一个注册的用户自动成为**管理员**
2. 在「收款账户」页面添加你的微信/支付宝收款账户
3. 在「分账方管理」页面添加分账方（合伙人、供应商等）
4. 在「分账规则」页面配置分账规则（平台抽成比例 + 各分账方比例）
5. 在「订单管理」页面录入订单或通过API接入业务系统
6. 订单创建后自动分账，在「结算管理」页面生成转账清单
7. 手动微信/支付宝转账后，在系统登记转账并确认结算

## 分账规则说明

### 分账流程

```
订单金额 100元
    ↓
平台抽成 10% = 10元（留在你的账户）
    ↓
可分账金额 90元
    ↓
一级分账：
  - 分账方A 60% = 54元
  - 分账方B 40% = 36元
    ↓
（可选）二级分账：基于分账方A的54元再分
  - 分账方C 20% = 10.8元
```

### 规则匹配优先级

1. 订单指定的分账规则
2. 按业务分类匹配的规则
3. 全局默认规则

## API 接入

业务系统可通过API创建订单，系统自动分账：

```bash
curl -X POST http://localhost:8000/api/v1/orders/api/create \
  -H "Content-Type: application/json" \
  -d '{
    "out_order_no": "BUSINESS20240101001",
    "total_amount": 100.00,
    "product_name": "商品名称",
    "category": "分类",
    "payer_name": "付款人",
    "auto_share": true
  }'
```

## 角色权限

| 角色 | 权限说明 |
|---|---|
| admin | 全部权限，包括用户管理 |
| manager | 运营管理，订单/分账方/规则管理 |
| finance | 财务，结算管理/对账/导出 |
| operator | 运营，订单录入/查看 |
| viewer | 只读，仅查看数据 |

## 合规说明

> ⚠️ **重要提示**

本系统采用**记账式分账**模式，系统本身不触碰资金、不形成资金池：
- 收款直接进入你的个人微信/支付宝账户
- 系统只记录各分账方应得金额
- 结算时由你手动转账给分账方，系统做登记

这种模式下，你仍需注意：
1. 个人收款码用于经营收款存在监管要求，建议注册个体工商户
2. 大额资金往来建议通过对公账户
3. 依法纳税是每个公民的义务

如需全自动合规分账，建议注册企业后接入微信/支付宝官方分账API。

## 项目结构

```
shareflow/
├── backend/                 # 后端
│   ├── app/
│   │   ├── main.py         # FastAPI主应用
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库连接
│   │   ├── dependencies.py # 依赖注入（认证/权限）
│   │   ├── core/           # 核心工具（安全/加密）
│   │   ├── models/         # 数据模型（11个表）
│   │   ├── schemas/        # Pydantic Schema
│   │   ├── api/            # API路由（10个模块）
│   │   ├── services/       # 业务服务（分账引擎）
│   │   └── tasks/          # 异步任务
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # 前端
│   ├── src/
│   │   ├── views/          # 页面（12个）
│   │   ├── api/            # API模块
│   │   ├── store/          # Pinia状态
│   │   ├── router/         # 路由
│   │   ├── layouts/        # 布局
│   │   └── types/          # TypeScript类型
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml       # Docker编排
├── .env.example            # 环境变量模板
└── README.md
```

## License

MIT
