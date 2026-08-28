# 金融小二 · 金融客服系统

一套面向银行/金融场景的智能客服前后端项目，打通「前端 → 客服后端 → 数据中台 → MySQL」全链路。

- **数据中台** `finance-data`：FastAPI 业务 API 层，端口 `8000`，库 `finance`。
- **客服后端** `finance-customer-service-backend`：Python 包 `jinrong`，复刻电商客服引擎骨架（意图规划 + 知识检索 + 任务流 + 闲聊 + 澄清 + 状态持久化），端口 `18082`。
- **前端** `finance-customer-service-frontend`：Vue3 + Vite 聊天调试页，端口 `5174`。

---

## 一、架构

```
浏览器 (Vue3 + Vite, :5174)
  │  /api/*       (Vite proxy → 18082)
  │  /finance/*   (Vite proxy → 8000/api/v1)
  ▼
金融客服后端 (FastAPI, :18082)   Python 包 `jinrong`
  api → service → DialogueEngine
    ├─ TurnPlanner (LLM → TurnPlan JSON)
    ├─ KnowledgeHandler (Provider → LLM 应答)
    ├─ TaskHandler (CommandProcessor + FlowExecutor + ActionRunner)
    ├─ ChitchatHandler / ClarifyResponder
  domain(DialogueState 状态机) / repository(MySQL 持久化)
  │  HTTP (Bearer + X-Channel-Code + X-Operator-No + X-Request-Id)
  ▼
数据中台 finance-data (FastAPI, :8000) → MySQL `finance`
```

### 后端分层

```
jinrong/
├── main.py                  # 入口 (uvicorn)
├── api/                     # app / chat_router / schemas / dependencies
├── services/                # DialogueStateService（消息处理 + 会话管理）
├── engines/                 # DialogueEngine + builder
├── plan/                    # TurnPlanner / TurnPlanValidator（LLM 意图规划）
├── knowledge/               # intents / handler / responder / provider
├── task/                    # commands / flows（YAML 流程引擎）/ action（金融 Action）
├── chitchat/  clarify/  chat_history/  prompt/
├── domain/                  # state / messages / contexts（状态机）
├── Infrastructure/          # db_client / http_client / llm_client / finance_client
├── repository/              # dialogue_record 持久化
└── config/settings.py       # .env 配置
```

---

## 二、重新设计的业务线

### 任务流程（`flow_config/user_flows.yml`）

| flow_id | 名称 | 关键槽位 | 数据中台接口 |
|---|---|---|---|
| `account_balance_query` | 账户余额查询 | `account_no` | `GET /accounts/{account_no}` |
| `transaction_query` | 交易流水查询 | `account_no` | `GET /accounts/{account_no}/transactions` |
| `loan_application` | 贷款申请 | `loan_product` `apply_amount` `apply_term_months` `loan_purpose` | `GET /loan/products` → `GET /customers/{no}/credit-limits` → `POST /loan/applications` |
| `card_loss_report` | 银行卡挂失 | `card_no` `loss_reason` | `POST /support/tickets`（`ticket_type=card_loss`） |
| `complaint_ticket` | 投诉工单 | `ticket_title` `ticket_content` | `POST /support/tickets` |

### 知识意图（`knowledge/intents.py`）

| intent | provider | 数据来源 |
|---|---|---|
| `account_info` | `api.account` | 账户列表 |
| `card_info` | `api.card` | 银行卡列表 |
| `transaction_info` | `api.transaction` | 交易流水 |
| `loan_product_info` | `api.loan_product` | 贷款产品 |
| `wealth_product_info` | `api.wealth_product` | 理财产品 |
| `policy_faq` | `faq.default` | 内置静态 FAQ（利率/手续费/挂失/销卡等） |
| `open_knowledge` | `rag.default` | 占位（可接向量库） |

### 前端业务对象卡片

账户 / 银行卡 / 贷款产品 / 理财产品，点击「发送」作为 `object` 消息发给后端，复用电商的 `object → focused_object → set_slots` 机制自动填槽。

---

## 三、启动步骤

### 0. 环境要求

- Python 3.12+ 与 `uv`
- Node.js 18+ 与 npm
- 已运行的 MySQL（默认 `192.168.100.100:3306`）

### 1. 数据中台 `finance-data`

```bash
cd finance-data
python init_db.py                       # 重建 finance 库（一次性）
python -m generate.main --profile full  # 生成 9 层数据
python -m uvicorn app.main:app --port 8000
```

### 2. 客服后端

```bash
cd finance-customer-service-backend
cp .env.example .env   # 或编辑 .env 填入 LLM / DB / 中台地址
uv run python -m jinrong.main
# 端口 18082，/health 返回 {"status":"ok"}
```

后端 `.env` 关键项：

```
LLM_MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.openai-proxy.org/v1
LLM_API_KEY=sk-...
FINANCE_API_BASE_URL=http://127.0.0.1:8000
DATABASE_URL=mysql+aiomysql://root:xxx@192.168.100.100:3306/jinrong?charset=utf8mb4
APP_HOST=0.0.0.0
APP_PORT=18082
CHANNEL_CODE=MOBILE_BANK
OPERATOR_NO=EMP000006
DEMO_CUSTOMER_NO=CUS00000001
```

### 3. 前端

```bash
cd finance-customer-service-frontend
npm install
npm run dev
# 打开 http://127.0.0.1:5174
```

---

## 四、接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 非流式对话，body `{sender_id, text?|object?}` |
| POST | `/api/chat/stream` | SSE 流式对话（逐字 `bot_text`，结尾 `turn_end`） |
| GET | `/api/chat/history?sender_id=` | 拉取历史消息 |
| POST | `/api/session` | 新建会话 |
| GET | `/api/session/state?sender_id=` | 查询当前状态 |
| DELETE | `/api/session?sender_id=` | 清空会话 |

**SSE 事件**：`data: {"type":"bot_text","delta":"..."}`、`data: {"type":"bot_object","object":{...}}`、`data: {"type":"turn_end","message_id":"..."}`。

---

## 五、测试

```bash
cd finance-customer-service-backend
uv run --with pytest python -m pytest tests/ -v
```

- 单元测试：状态机序列化、对象→槽位映射、Action 注册、`{code,message,data}` 解包、流程加载、路由注册。
- 集成测试（需中台 + 后端在运行）：闲聊、知识检索、会话接口、余额查询对象点击、SSE 流式。

---

## 六、演示流程建议

1. 「你好」→ 闲聊兜底。
2. 「你们有哪些贷款产品」→ 知识检索（真实产品）。
3. 「查一下我的账户余额」→ 追问账户号 → 点侧栏「账户」卡片 → 返回真实余额。
4. 「查一下我的交易流水」→ 点账户卡片 → 返回最近流水。
5. 「我想申请贷款」→ 选产品/金额/期限/用途 → 返回申请单号。
6. 「我要挂失银行卡」→ 卡号/原因/身份 → 落挂失工单返回工单号。
7. 「我要投诉」→ 标题/内容 → 返回投诉工单号。
