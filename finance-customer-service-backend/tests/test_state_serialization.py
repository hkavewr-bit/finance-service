"""DialogueState 状态机序列化/反序列化往返测试。"""
from jinrong.domain.messages import MessageType, UserMessage, FocusedObject
from jinrong.domain.state import DialogueState, Session, Turn


def test_state_round_trip_preserves_turns_and_focused_object():
    state = DialogueState(
        sender_id="CUS00000001",
        sessions=[
            Session(
                session_id="session-1",
                started_at=1.0,
                activated_at=1.0,
                turns=[
                    Turn(
                        turn_id="turn-1",
                        user_message=UserMessage(
                            sender_id="CUS00000001",
                            message_id="message-1",
                            type=MessageType.OBJECT,
                            object=FocusedObject(
                                id="ACC0000000001",
                                title="账户 ACC0000000001",
                                type="account",
                                attributes={"balance_amount": "2125.00"},
                            ),
                        ),
                        bot_messages=[],
                    )
                ],
            )
        ],
        current_session_id="session-1",
    )

    restored = DialogueState.from_dict(state.to_dict())

    assert restored.to_dict() == state.to_dict()
    assert restored.sender_id == "CUS00000001"

    restored_message = restored.sessions[0].turns[0].user_message
    assert isinstance(restored_message, UserMessage)
    assert restored_message.type is MessageType.OBJECT
    assert restored_message.object.type == "account"
    assert restored_message.object.id == "ACC0000000001"


def test_empty_state_round_trip():
    state = DialogueState(sender_id="u1")

    restored = DialogueState.from_dict(state.to_dict())

    assert restored.sender_id == "u1"
    assert restored.active_task is None
    assert restored.paused_tasks == []
    assert restored.sessions == []
    assert restored.current_session_id is None


def test_session_lifecycle_management():
    state = DialogueState(sender_id="u1")
    assert state.current_session() is None

    state.start_session()
    assert state.current_session() is not None
    assert state.current_session_id == state.current_session().session_id

    state.close_current_session()
    assert state.current_session() is None
    assert state.current_session_id is None
