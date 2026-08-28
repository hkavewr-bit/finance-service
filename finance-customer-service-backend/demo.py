"""金融客服端到端演示脚本。

在数据中台(:8000)与客服后端(:18082)均已启动后运行：

    cd finance-customer-service-backend
    uv run python demo.py

按验收清单依次走通：闲聊、知识检索、余额查询、流水查询、贷款申请、挂失、投诉。
"""
import json

import httpx

BASE_URL = "http://127.0.0.1:18082"
SENDER_ID = "CUS00000001"

ACCOUNT_OBJECT = {
    "type": "account",
    "id": "ACC0000000001",
    "title": "账户 ACC0000000001",
    "attributes": {"account_no": "ACC0000000001", "balance_amount": "2125.00", "currency_code": "CNY"},
}

SECTION_SEP = "\n" + "=" * 70


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, timeout=90)

    # 重置会话
    client.delete("/api/session", params={"sender_id": SENDER_ID})

    def chat(payload: dict) -> str:
        r = client.post("/api/chat", json={"sender_id": SENDER_ID, **payload})
        r.raise_for_status()
        return "\n".join(m["text"] for m in r.json()["messages"] if m["text"])

    def turn(user_text: str) -> None:
        print(f"\n[用户] {user_text}")
        print(f"[客服] {chat({'text': user_text})}")

    def reset() -> None:
        client.delete("/api/session", params={"sender_id": SENDER_ID})

    # 1. 闲聊兜底
    print(SECTION_SEP)
    print("1. 闲聊兜底")
    turn("你好")

    # 2. 知识检索（贷款产品）
    print(SECTION_SEP)
    print("2. 知识检索（贷款产品）")
    turn("你们有哪些贷款产品")

    # 3. 账户余额查询（文本 + 对象点击自动填槽）
    print(SECTION_SEP)
    print("3. 账户余额查询（点击账户卡片自动填槽）")
    reset()
    print(f"\n[用户] 查一下我的账户余额")
    print(f"[客服] {chat({'text': '查一下我的账户余额'})}")
    print(f"\n[用户] (点击账户卡片 {ACCOUNT_OBJECT['id']})")
    print(f"[客服] {chat({'object': ACCOUNT_OBJECT})}")

    # 4. 交易流水查询（对象点击）
    print(SECTION_SEP)
    print("4. 交易流水查询（点击账户卡片自动填槽）")
    reset()
    print(f"\n[用户] 查一下我的交易流水")
    print(f"[客服] {chat({'text': '查一下我的交易流水'})}")
    print(f"\n[用户] (点击账户卡片 {ACCOUNT_OBJECT['id']})")
    print(f"[客服] {chat({'object': ACCOUNT_OBJECT})}")

    # 5. 贷款申请（多轮槽位收集 → 提交 → 申请单号）
    print(SECTION_SEP)
    print("5. 贷款申请（多轮槽位收集）")
    reset()
    turn("我想申请一笔贷款")
    turn("LOAN_CONSUMER_STD")
    turn("30000")
    turn("12")
    turn("个人消费")

    # 6. 银行卡挂失（多轮 → 落挂失工单 → 工单号）
    print(SECTION_SEP)
    print("6. 银行卡挂失（工单兜底）")
    reset()
    turn("我要挂失银行卡")
    turn("6222000000000000001")
    turn("丢失")
    turn("1234")

    # 7. 投诉工单
    print(SECTION_SEP)
    print("7. 投诉工单")
    reset()
    turn("我要投诉")
    turn("网点服务态度差")
    turn("今天下午在网点办理业务时柜员态度恶劣，且排队等待时间过长。")

    # 8. SSE 流式响应演示
    print(SECTION_SEP)
    print("8. SSE 流式响应（逐字推送）")
    print(f"\n[用户] 你好")
    print("[客服]", end=" ")
    with client.stream("POST", "/api/chat/stream", json={"sender_id": SENDER_ID, "text": "你好"}) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if data.get("type") == "bot_text":
                    print(data["delta"], end="", flush=True)
    print()

    print(SECTION_SEP)
    print("演示完成 ✅")


if __name__ == "__main__":
    main()
