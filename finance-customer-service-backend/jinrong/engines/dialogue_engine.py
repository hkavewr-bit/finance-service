import time

from jinrong.chitchat.handler import ChitchatHandler
from jinrong.clarify.handler import ClarifyResponder
from jinrong.domain.messages import ProcessedResult, BotMessage, UserMessage, MessageType, FocusedObject, OBJECT_TYPE_TO_SLOT
from jinrong.domain.state import DialogueState
from jinrong.knowledge.handler import KnowledgeHandler
from jinrong.plan.planner import TurnPlanner
from jinrong.plan.turn_plan import ClarifyReason
from jinrong.plan.validator import TurnPlanValidator
from jinrong.task.commands.command import SetSlotsCommand
from jinrong.task.flows.flows import FlowList
from jinrong.task.flows.handler import TaskHandler
from jinrong.task.flows.steps import CollectFlowStep


class DialogueEngine:

    def __init__(self,
                 turn_planner: TurnPlanner,
                 task_handler: TaskHandler,
                 knowledge_handler: KnowledgeHandler,
                 chitchat_handler: ChitchatHandler,
                 clarify_responder: ClarifyResponder,
                 turn_plan_validator: TurnPlanValidator
                 ):
        self.turn_planner = turn_planner
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder
        self.turn_plan_validator = turn_plan_validator

    async def handle_message(self, user_message: UserMessage,
                             dialogue_state: DialogueState) -> ProcessedResult:
        self._prepare_session(dialogue_state)

        self._start_turn(user_message, dialogue_state)

        if user_message.type is MessageType.TEXT:
            bot_messages: list[BotMessage] = await self._handle_text_message(dialogue_state)
        else:
            dialogue_state.focused_object=user_message.object
            bot_messages: list[BotMessage] = await self._handle_object_message(user_message.object, dialogue_state,
                                                                               self.task_handler.flow_list)

        dialogue_state.pending_turn.bot_messages = bot_messages
        dialogue_state.commit_pending_turn()

        return ProcessedResult(message_id=user_message.message_id,
                               messages=bot_messages)

    def _prepare_session(self, state: DialogueState):
        current_session = state.current_session()

        if current_session is None:
            state.start_session()
        else:
            now = time.time()

            if now - current_session.activated_at > 60 * 60:
                state.close_current_session()
                state.reset_runtime_state_for_new_session()

                state.start_session()
            else:
                current_session.activated_at = now

    def _start_turn(self, user_message: UserMessage, state: DialogueState):
        state.begin_turn(user_message)

    async def _handle_text_message(self, dialogue_state) -> list[BotMessage]:
        turn_plan = await self.turn_planner.predict(dialogue_state,
                                                    flow_list=self.task_handler.flow_list,
                                                    knowledge_intents=self.knowledge_handler.knowledge_intents)

        validated = self.turn_plan_validator.valid(
            turn_plan,
            dialogue_state,
            flow_list=self.task_handler.flow_list,
            knowledge_intents=self.knowledge_handler.knowledge_intents
        )

        if not validated.valid:
            return await self.clarify_responder.respond(validated.reason, dialogue_state)

        if turn_plan.task is not None:
            return await self.task_handler.handle(turn_plan.task.commands, dialogue_state)
        elif turn_plan.knowledge is not None:
            return await self.knowledge_handler.handle(turn_plan.knowledge.intents, dialogue_state)
        else:
            return await self.chitchat_handler.handle(turn_plan.chitchat.chat, dialogue_state)

    async def _handle_object_message(self,
                                     obj: FocusedObject,
                                     dialogue_state: DialogueState,
                                     flow_list: FlowList):
        command = self._try_build_set_slots_command(obj, dialogue_state, flow_list)

        if command:
            return await self.task_handler.handle(commands=[command], dialogue_state=dialogue_state)

        if dialogue_state.active_task is not None:
            return await self.task_handler.handle(commands=[], dialogue_state=dialogue_state)

        return await self.clarify_responder.respond(reason=ClarifyReason.OBJECT_REQUIRES_INTENT,
                                                    dialogue_state=dialogue_state)

    def _try_build_set_slots_command(self,
                                     obj: FocusedObject,
                                     dialogue_state: DialogueState,
                                     flow_list: FlowList):
        slot_name = OBJECT_TYPE_TO_SLOT.get(obj.type)
        if slot_name is None:
            return None

        if self._is_can_set_slots_command(slot_name=slot_name,
                                          state=dialogue_state,
                                          flow_list=flow_list):
            return SetSlotsCommand(command="set_slots", slots={slot_name: obj.id})
        return None

    def _is_can_set_slots_command(self,
                                  slot_name :str,
                                  state: DialogueState,
                                  flow_list : FlowList):
        task_context = state.active_task

        if task_context is None:
            return False

        flow = flow_list.get_flow_by_id(task_context.flow_id)
        if flow is None:
            return False

        step_id = task_context.step_id
        step = flow.get_step_by_id(step_id)

        if step is None:
            return False

        if not isinstance(step, CollectFlowStep):
            return False

        return step.slot_name == slot_name


