# Atguigu 电商智能客服后端

这是一个基于 FastAPI 的电商智能客服后端。它接收用户文本或订单/商品卡片，通过大模型生成“本轮计划”，再把请求分流到任务流程、知识问答、闲聊或澄清链路，并将多轮会话状态持久化到 MySQL。

> 本文依据当前仓库源码整理。文中的“已实现”表示源码中已有明确调用链；“待接入/已知问题”表示当前实现仍不完整，不能仅凭目录名视为可用能力。

## 1. 项目能力概览

当前后端提供两个 HTTP 接口：

| 接口 | 作用 | 主要入口 |
| --- | --- | --- |
| `POST /api/chat` | 处理一条文本消息或订单/商品对象消息 | `atguigu/api/chat_router.py::chat_endpoint` |
| `GET /api/chat/history` | 按 `sender_id` 返回历史会话消息 | `atguigu/api/chat_router.py::get_chat_history_endpoint` |

核心业务能力包括：

- 任务型客服：订单状态查询、物流查询、退款信息收集、相似商品推荐入口、人工客服提示。
- 知识型客服：订单信息、商品信息、退款/退货/配送政策、平台规则、通用电商知识。
- 多轮对话：保存会话、轮次、焦点对象、当前任务、暂停任务、槽位和系统子任务。
- 流程编排：用 YAML 定义业务步骤，通过命令处理器、流程执行器和动作注册表运行。
- 大模型编排：由 LLM 负责回合规划、知识答案生成、闲聊回复和部分澄清/改写。
- 外部集成：通过异步 HTTP 调用电商订单、物流、商品接口，通过异步 SQLAlchemy 访问 MySQL。

## 2. 技术栈与外部依赖

| 类别 | 技术 | 在项目中的作用 |
| --- | --- | --- |
| Web | FastAPI、Uvicorn | HTTP API 与应用生命周期 |
| 大模型 | LangChain、OpenAI-compatible Chat Model | 回合规划与自然语言生成 |
| 数据库 | SQLAlchemy Async、aiomysql、MySQL | 对话状态持久化 |
| HTTP | httpx AsyncClient | 调用电商业务 API |
| 流程配置 | PyYAML | 加载任务流和系统流 |
| 模板 | Jinja2 | Prompt 和客服话术渲染 |
| 配置 | pydantic-settings | 从项目根目录 `.env` 加载配置 |
| 运行环境 | Python 3.12+ | `pyproject.toml` 声明的最低版本 |

系统边界如下：

```mermaid
flowchart LR
    Client["前端 / API 调用方"] --> API["FastAPI 接口层"]
    API --> Service["DialogueStateService"]
    Service --> Engine["DialogueEngine"]
    Service <--> DB[("MySQL dialogue_record")]
    Engine --> Planner["LLM 回合规划"]
    Engine --> Task["YAML 任务流引擎"]
    Engine --> Knowledge["知识问答链路"]
    Engine --> Chitchat["闲聊 / 澄清"]
    Task --> Commerce["电商订单 / 物流 / 商品 API"]
    Knowledge --> Commerce
    Knowledge --> LLM["LLM 服务"]
    Planner --> LLM
    Chitchat --> LLM
```

## 3. 项目目录与模块职责

```text
customer-service-backend/
├─ atguigu/
│  ├─ api/                 # FastAPI 应用、路由、请求响应模型、依赖注入
│  ├─ services/            # 用例编排：加载状态 -> 调引擎 -> 保存状态
│  ├─ engines/             # 对话总引擎及其对象装配
│  ├─ plan/                # LLM 回合规划、计划数据结构、计划校验
│  ├─ task/                # YAML 任务流、命令、执行器和动作插件
│  ├─ knowledge/           # 知识意图、Provider、知识答案生成
│  ├─ clarify/             # 无效/不完整计划的澄清回复
│  ├─ chitchat/            # 闲聊回复
│  ├─ domain/              # 消息、会话、任务上下文等领域对象
│  ├─ repository/          # 对话状态的数据访问与 ORM 映射
│  ├─ Infrastructure/      # 数据库、HTTP、大模型客户端
│  ├─ prompt/              # Jinja2 Prompt 模板及加载器
│  ├─ chat_history/        # 历史消息到 Prompt/API 数据的转换
│  ├─ config/              # 环境变量配置
│  └─ main.py              # Uvicorn 启动入口
├─ flow_config/            # 实际由引擎加载的系统流和用户业务流
├─ tests/                  # 入口、应用构建、异步 Handler、状态序列化测试
├─ pyproject.toml          # 包信息、Python 版本与依赖
└─ .env                    # 本地配置；包含敏感信息，不应提交或展示
```

### 3.1 API 层：`atguigu/api`

- `app.py`：创建 FastAPI 应用；启动时初始化数据库引擎和全局 HTTP 客户端，关闭时释放资源。
- `chat_router.py`：定义聊天与历史接口；负责 API Schema 与领域消息之间的转换。
- `schemas.py`：定义 `ChatRequest`、`ChatResponse`、卡片对象和历史响应模型。
- `dependencies.py`：使用 FastAPI 依赖注入装配数据库会话、Repository、DialogueEngine 和 Service。

API 层只做协议转换和依赖组装，不直接实现客服业务。

### 3.2 应用服务层：`atguigu/services`

`DialogueStateService` 是 HTTP 层与领域引擎之间的用例边界：

1. 根据 `sender_id` 从数据库加载 `DialogueState`。
2. 调用 `DialogueEngine.handle_message()`。
3. 将变更后的完整状态写回数据库。
4. 返回本轮 `ProcessedResult`。

历史查询同样从持久化状态读取，再按 `session -> turn -> user/bot message` 展开成接口响应。

### 3.3 对话引擎：`atguigu/engines`

- `builder.py`：加载 `flow_config/system_flows.yml` 和 `user_flows.yml`，并组装所有 Handler、Provider、流程组件和动作。
- `dialogue_engine.py`：整个对话的核心调度器，负责会话生命周期、轮次生命周期、文本/对象消息分流和结果提交。

`DialogueEngine` 不直接查询数据库；它只修改传入的领域状态。持久化由 Service/Repository 负责。

### 3.4 回合规划：`atguigu/plan`

- `planner.py`：把最近十轮历史、当前消息、焦点对象、活动/暂停任务、可用业务流和知识意图写入 Prompt，再调用 LLM 输出 JSON。
- `turn_plan.py`：把 LLM JSON 转换为 `TurnPlan`，支持 `task`、`knowledge`、`chitchat` 三条轨道。
- `validator.py`：保证一次只激活一条轨道，并校验任务命令、流程 ID、知识意图和所需焦点对象。

规划器负责“理解用户想做什么”，校验器负责“限制 LLM 只能调用系统允许的能力”。

### 3.5 任务流引擎：`atguigu/task`

任务模块由三层组成：

| 层 | 核心类 | 职责 |
| --- | --- | --- |
| 命令层 | `CommandProcessor` | 处理开始、填槽、取消、恢复任务，更新 `DialogueState` |
| 流程层 | `FlowsLoader`、`FlowExecutor` | 解析 YAML，按 start/collect/action/end 和条件边推进 |
| 动作层 | `ActionRunner`、`ActionRegistry` | 按动作名执行内置或业务动作，生成消息或更新槽位 |

支持的 LLM 任务命令：

- `start_flow`：开始一个业务流程；若已有不同活动任务，会先暂停旧任务。
- `set_slots`：把用户提供的信息写入当前任务槽位。
- `cancel_flow`：取消当前任务，并运行系统确认流。
- `resume_flow`：恢复之前暂停的任务。

支持的流程步骤：

- `start`：流程入口。
- `collect`：检查槽位；缺失时启动 `system_collect_information` 询问用户并停在 `action_listen`。
- `action`：执行业务动作或响应动作。
- `end`：结束系统子任务或业务任务。

业务动作不是手工逐个注册。`task/action/builder.py` 会扫描 `atguigu.task.action.customer` 包，发现所有 `Action` 子类并自动注册；新增动作时仍必须保证类的 `name` 与 YAML 中的 `action` 完全一致。

### 3.6 知识问答：`atguigu/knowledge`

- `intents.py`：定义知识意图、说明、Provider 列表和可选的焦点对象要求。
- `handler.py`：把一个或多个知识意图映射到 Provider，聚合 `KnowledgeChunk`。
- `provider/provider.py`：定义统一的 Provider 抽象与知识块结构。
- `provider/register.py`：按 `provider_id` 保存并查找 Provider。
- `provider/knowlege.py`：实现订单、商品、RAG、FAQ Provider。
- `responder.py`：把检索结果、当前问题和最近十轮历史交给 LLM，生成最终回答。

#### `knowlege.py` 的具体作用

该文件位于知识检索链路，不是任务流动作：

| Provider | `provider_id` | 数据来源 | 当前状态 |
| --- | --- | --- | --- |
| `ApiOrderProvider` | `api.order` | 并发请求订单详情和物流详情 API | 已实现 |
| `ApiProductProvider` | `api.product` | 请求商品详情 API | 类已实现，但当前未正确注册 |
| `RagDefaultProvider` | `rag.default` | 预期连接向量知识库 | 占位实现 |
| `FaqDefaultProvider` | `faq.default` | 预期连接 FAQ 语义检索 | 占位实现 |

订单 Provider 使用 `asyncio.gather()` 并发获取：

```text
GET {commerce_api_base_url}/orders/{order_number}
GET {commerce_api_base_url}/orders/{order_number}/logistics
```

商品 Provider 调用：

```text
GET {commerce_api_base_url}/products/{product_id}
```

Provider 返回的结构化数据先序列化为 `KnowledgeChunk.content`，随后才由 `KnowledgeResponder` 交给 LLM 组织自然语言答案。

### 3.7 领域状态：`atguigu/domain`

`DialogueState` 是贯穿整个请求的核心对象：

```text
DialogueState
├─ sender_id                 # 用户标识，也是数据库主键
├─ active_task               # 当前业务任务及其 step/slots
├─ paused_tasks[]            # 被新任务打断的任务栈
├─ active_system_task        # 开始、打断、收集、取消等系统子流程
├─ sessions[]                # 历史会话
│  └─ turns[]                # 每个会话的轮次
│     ├─ user_message
│     └─ bot_messages[]
├─ current_session_id
├─ focused_object            # 当前订单或商品卡片
└─ pending_turn              # 正在处理、尚未提交的本轮
```

如果当前会话超过一小时未激活，引擎会关闭旧会话、清空运行时任务状态并新建会话；历史 `sessions` 仍会保留。

### 3.8 Repository 与基础设施

- `DialogueRepository`：用 `sender_id` 读取 `dialogue_record`；不存在时创建空状态；保存时使用 MySQL `ON DUPLICATE KEY UPDATE` 完成 upsert。
- `DialogueRecord`：数据库表映射，仅含 `sender_id` 主键与 `state_json` 文本字段。
- `db_client.py`：创建异步 SQLAlchemy Engine 和 Session Factory。
- `http_client.py`：维护应用级 `httpx.AsyncClient`。
- `llm_client.py`：根据 `.env` 创建 OpenAI-compatible LangChain Chat Model。

数据库存的是完整领域状态 JSON，而不是把 session、turn、slot 分成多张关系表。

## 4. 启动与依赖装配链路

```mermaid
flowchart TD
    Main["python -m atguigu.main"] --> Uvicorn["uvicorn.run"]
    Uvicorn --> App["atguigu.api.app:app"]
    App --> Lifespan["FastAPI lifespan"]
    Lifespan --> DB["init_db_engine"]
    Lifespan --> HTTP["init_http_client"]
    Request["请求到达路由"] --> Depends["FastAPI Depends"]
    Depends --> Session["AsyncSession"]
    Depends --> Repo["DialogueRepository"]
    Depends --> Builder["build_dialogue_engine"]
    Builder --> YAML["加载两份 flow_config YAML"]
    Builder --> Actions["扫描并注册 Actions"]
    Depends --> Service["DialogueStateService"]
```

每次请求依赖解析时会重新调用 `build_dialogue_engine()`，因此也会重新读取 YAML 并组装引擎；数据库 Engine 和 HTTP Client 则由应用生命周期统一初始化和释放。

## 5. 一条聊天请求的完整业务链路

```mermaid
sequenceDiagram
    participant C as 前端
    participant R as chat_endpoint
    participant S as DialogueStateService
    participant D as DialogueRepository
    participant E as DialogueEngine
    participant P as TurnPlanner / LLM
    participant H as 业务 Handler
    participant X as 外部服务

    C->>R: POST /api/chat
    R->>R: ChatRequest -> UserMessage
    R->>S: process_message(user_message)
    S->>D: load_state(sender_id)
    D-->>S: DialogueState
    S->>E: handle_message(message, state)
    E->>E: 准备 session + begin_turn
    alt 文本消息
        E->>P: 根据状态预测 TurnPlan
        P-->>E: task / knowledge / chitchat
        E->>E: TurnPlanValidator 校验
        E->>H: 执行选中的 Handler
        opt 任务动作或知识 Provider
            H->>X: 电商 API / LLM
            X-->>H: 数据或回答
        end
    else 订单/商品对象消息
        E->>E: 更新 focused_object
        E->>H: 尝试填充当前 collect 槽位，否则澄清
    end
    H-->>E: BotMessage[]
    E->>E: 写入 pending_turn 并 commit
    E-->>S: ProcessedResult
    S->>D: save_state(sender_id, state)
    D->>D: JSON 序列化并 upsert
    S-->>R: ProcessedResult
    R-->>C: ChatResponse
```

### 5.1 文本消息分流

文本请求一定先经过 LLM Planner。Planner 的输出通过 Validator 后，只能进入一条轨道：

```mermaid
flowchart TD
    Text["文本消息"] --> Plan["LLM 生成 TurnPlan"]
    Plan --> Validate{"计划是否合法?"}
    Validate -- 否 --> Clarify["ClarifyResponder 澄清"]
    Validate -- 是 --> Track{"激活轨道"}
    Track -- task --> Task["TaskHandler"]
    Track -- knowledge --> Knowledge["KnowledgeHandler"]
    Track -- chitchat --> Chat["ChitchatHandler"]
    Task --> Result["BotMessage[]"]
    Knowledge --> Result
    Chat --> Result
    Clarify --> Result
```

### 5.2 对象消息分流

前端可以发送 `object.type=order` 或 `product` 的卡片消息：

1. 引擎把对象保存为 `focused_object`。
2. 如果活动任务正停在匹配的 `collect` 步骤，订单 ID 会写入 `order_number`，商品 ID 会写入 `product_id`。
3. 若存在活动任务但当前步骤不匹配，任务流继续运行/等待。
4. 若没有活动任务，引擎不会猜测用户意图，而是询问用户想对该订单或商品做什么。

## 6. 三条核心业务链路

### 6.1 任务型客服链路

以“查询物流”为例：

```text
用户说“查物流”
-> Planner 输出 start_flow(logistics_tracking)
-> Validator 确认流程存在
-> CommandProcessor 建立 TaskContext
-> 系统流回复“先处理物流查询”
-> 业务流进入 collect(order_number)
-> 缺少槽位时询问订单号并监听
-> 下一轮 Planner 输出 set_slots(order_number)
-> FlowExecutor 调用 action_lookup_logistics
-> 电商 API 返回物流数据并写入槽位
-> action_response 用 Jinja2 渲染结果
-> end 清除 active_task
-> 保存完整 DialogueState
```

当前 `user_flows.yml` 中定义：

| Flow ID | 业务作用 | 外部副作用/完整度 |
| --- | --- | --- |
| `onboarding` | 欢迎并介绍能力 | 仅回复文本 |
| `order_status_query` | 收集订单号并查询订单状态 | 调用订单 API |
| `logistics_tracking` | 收集订单号并查询物流 | 调用物流 API |
| `refund_request` | 收集订单号和退款原因 | 当前只回复“已提交”，没有真实退款 API/数据库写入 |
| `similar_product_recommendation` | 收集商品并进入推荐动作 | 当前明确提示推荐系统尚未接入 |
| `human_handoff` | 回复转人工提示 | 没有真实工单、队列或客服系统集成 |

### 6.2 知识型客服链路

以“这个订单现在到哪里了”为例：

```text
用户文本 + 已有 order focused_object
-> Planner 输出 knowledge.intents=[order_info]
-> Validator 检查必须存在 order 对象
-> KnowledgeHandler 映射到 api.order
-> ApiOrderProvider 并发查询订单与物流
-> 返回 KnowledgeChunk
-> KnowledgeResponder 组合知识、问题和历史
-> LLM 生成自然语言答案
```

知识链路与任务链路的区别：任务链路通过步骤和槽位完成一个可持续的业务过程；知识链路检索数据后直接生成本轮答案。

### 6.3 闲聊与澄清链路

- `chitchat`：Planner 判定为闲聊后，`ChitchatResponder` 根据闲聊内容和最近十轮历史调用 LLM。
- `clarify`：计划缺轨道、多轨道、缺命令、缺知识意图、缺焦点对象或对象缺少意图时，`ClarifyResponder` 先构造针对性提示，再让 LLM 生成自然回复。

## 7. 对话状态的数据流

```mermaid
flowchart LR
    Row["dialogue_record.state_json"] --> Decode["json.loads"]
    Decode --> Restore["DialogueState.from_dict"]
    Restore --> Runtime["引擎修改领域对象"]
    Runtime --> Serialize["DialogueState.to_dict"]
    Serialize --> Encode["json.dumps"]
    Encode --> Upsert["MySQL upsert"]
```

反序列化必须逐层恢复领域对象：`DialogueState -> Session -> Turn -> UserMessage/BotMessage`。如果某一层保留为普通字典，后续代码按属性访问时会失败。

## 8. 配置、运行与验证

### 8.1 必需配置

项目从根目录 `.env` 读取以下字段：

```dotenv
LLM_MODEL=your-model
LLM_API_KEY=your-secret
LLM_BASE_URL=https://your-openai-compatible-endpoint
COMMERCE_API_BASE_URL=http://your-commerce-api
DATABASE_URL=mysql+aiomysql://user:password@host:port/database
APP_HOST=127.0.0.1
APP_PORT=18082
```

不要把真实 API Key、数据库密码或完整 `.env` 放入 README、日志或版本库。

数据库需预先存在 `dialogue_record` 表；ORM 模型不会在应用启动时自动执行 `create_all()`：

```sql
CREATE TABLE dialogue_record (
    sender_id VARCHAR(255) PRIMARY KEY,
    state_json TEXT NOT NULL
);
```

字段长度应结合实际 `sender_id` 规则调整；`state_json` 会随历史增长，生产环境可评估 `MEDIUMTEXT`/归档策略。

### 8.2 安装与启动

在 PowerShell 中进入项目根目录后执行：

```powershell
Set-Location -LiteralPath 'F:\0331大模型课程文件\项目一智能客服\day01_项目介绍初始化\3_code\sz260331\customer-service-backend'
& '.\.venv\Scripts\python.exe' -m pip install -e .
& '.\.venv\Scripts\python.exe' -m atguigu.main
```

不要直接运行 `atguigu/main.py`；包内使用了 `from atguigu...` 绝对导入，从项目根目录用 `-m atguigu.main` 最稳定。

启动后可访问：

```text
http://127.0.0.1:18082/docs
```

实际主机和端口以 `.env` 的 `APP_HOST`、`APP_PORT` 为准。

### 8.3 请求示例

文本消息：

```json
{
  "sender_id": "user-001",
  "text": "帮我查一下订单状态"
}
```

订单卡片消息：

```json
{
  "sender_id": "user-001",
  "object": {
    "id": "A20260408002",
    "type": "order",
    "title": "订单 A20260408002",
    "attributes": {}
  }
}
```

历史查询：

```text
GET /api/chat/history?sender_id=user-001
```

### 8.4 测试

```powershell
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_*.py' -v
```

测试目前主要覆盖：

- 包模块入口是否把正确的 app/host/port 交给 Uvicorn。
- FastAPI 应用与依赖是否可以构建。
- 知识/闲聊异步 Handler 是否真正等待 responder。
- 对话状态能否完成“序列化 -> 恢复 -> 再序列化”。

这些测试不等价于真实 LLM、电商 API 和 MySQL 的端到端验证。

## 9. 常见扩展点

### 新增一个任务流程

1. 在 `flow_config/user_flows.yml` 定义所需 slot 和 flow。
2. 能复用 `action_response`、`action_listen` 时无需新建 Action。
3. 需要外部业务操作时，在 `atguigu/task/action/customer/` 新建 `Action` 子类。
4. 保证类的 `name` 与 YAML 的 `action` 值一致；扫描器会自动注册。
5. 确保 Planner Prompt 能看到并正确选择新 flow。
6. 为命令、槽位推进和结束状态增加测试。

### 新增一个知识意图

1. 在 `knowledge/intents.py` 增加 `KnowledgeIntent`。
2. 在 `knowledge/provider/` 实现稳定且唯一的 `provider_id`。
3. 在 `engines/builder.py` 的 `KnowledgeRegister` 中注册实例。
4. 若依赖订单/商品对象，设置 `requires_object_type`。
5. 测试“意图 -> Provider -> KnowledgeChunk -> 回答”的完整链路。

### 新增配置或外部客户端

1. 在 `config/settings.py` 增加字段。
2. 更新 `.env` 示例，但不要写入真实凭据。
3. 在 FastAPI lifespan 中初始化和释放应用级资源。
4. 不要在业务模块里重复创建数据库 Engine 或 HTTP Client。

## 10. 当前已知问题与风险

以下结论来自当前源码静态检查：

1. **商品知识 Provider 未注册。** `engines/builder.py` 的 Provider 列表写了两次 `ApiOrderProvider()`，却没有 `ApiProductProvider()`；`product_info -> api.product` 会在注册表查找时触发 `KeyError`。
2. **RAG 和 FAQ 仍是占位实现。** 两者只返回“未检索到”类固定文本，尚未接入向量库或 FAQ 数据源。
3. **退款与转人工没有真实落地。** YAML 只生成确认话术，没有退款 API、工单、消息队列或人工客服系统调用。
4. **相似商品推荐尚未接入。** 动作会读取商品信息，但只返回能力未接入的提示。
5. **外部 API 错误策略不一致。** 任务动作的共享请求函数捕获所有异常并返回 `None`；知识 Provider 则直接索引响应 JSON，网络错误、非 2xx 或字段缺失会向上抛出。
6. **Validator 对未知知识意图缺少保护。** `_validate_knowledge_track()` 直接用字典下标访问意图，LLM 输出未知 ID 时可能触发 `KeyError`。
7. **流程条件使用 `eval()`。** 条件来自本地 YAML，但仍应把配置文件视为受信代码；生产系统宜替换为受限表达式解释器。
8. **引擎按请求重复装配。** 当前依赖函数每次请求都加载 YAML、扫描动作包并构建引擎，功能正确但存在不必要的 I/O 和反射开销。
9. **状态 JSON 会持续增长。** 所有历史会话都存入单行 `TEXT`；缺少历史归档、大小限制和并发更新冲突控制。
10. **接口身份边界较弱。** 客户端直接传入 `sender_id`，源码未体现认证授权，调用者理论上可查询其他 ID 的历史。
11. **源码/配置中存在乱码文本。** 多处中文呈现为错误编码字符，会影响 Prompt、客服回复、流程名称和可维护性；修复时需先确认原始编码并统一为 UTF-8。
12. **部分状态边界需补测试。** 例如无活动任务时取消流程、并发处理同一 `sender_id`、外部 API 失败和 LLM 非法 JSON 等路径目前未见完整覆盖。

## 11. 推荐阅读顺序

第一次学习项目时，建议按真实调用链阅读：

1. `atguigu/main.py`、`atguigu/api/app.py`：理解应用如何启动和管理资源。
2. `atguigu/api/chat_router.py`、`services/dialogue_service.py`：理解一次 HTTP 请求的外层链路。
3. `domain/state.py`、`domain/messages.py`：掌握贯穿全项目的数据对象。
4. `engines/dialogue_engine.py`：掌握文本、对象和 session/turn 的总调度。
5. `plan/planner.py`、`plan/validator.py`：理解 LLM 如何被约束为可执行计划。
6. `flow_config/*.yml`、`task/commands/processor.py`、`task/flows/executor.py`：理解多轮任务如何推进。
7. `task/action/`：理解流程最终如何产生回复或调用外部业务。
8. `knowledge/handler.py`、`knowledge/provider/knowlege.py`、`knowledge/responder.py`：理解检索增强问答链路。
9. `repository/dialogue_repository.py`：理解状态如何落库和恢复。

读完这条路线后，再选择一个具体场景（推荐“物流查询”）从请求 JSON 一直跟到数据库 `state_json`，会比逐文件浏览更容易建立整体认知。

