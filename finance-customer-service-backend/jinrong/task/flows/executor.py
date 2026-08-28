from dataclasses import asdict

from jinrong.domain.contexts import SystemCollectionInformationContext
from jinrong.domain.messages import BotMessage, OBJECT_TYPE_TO_SLOT
from jinrong.domain.state import DialogueState
from jinrong.task.action.runner import ActionRunner, ActionCall
from jinrong.task.flows.flows import FlowList
from jinrong.task.flows.links import FlowStepStaticLink, FlowStepConditionLink, FlowStepFallbackLink
from jinrong.task.flows.steps import StartFlowStep, FlowStep, EndFlowStep, ActionFlowStep, CollectFlowStep


class FlowExecutor:
    async def execute_flow(self,
                           state: DialogueState,
                           action_runner: ActionRunner,
                           flow_list: FlowList) -> list[BotMessage]:
        final_response_messages = []
        while True:

            action_call = self._advance_flow_util_action(state, flow_list)

            if action_call.action_name == 'action_listen':
                break

            action_result = await action_runner.run(action_call,state)

            final_response_messages.extend(action_result.messages)
            state.set_slots(action_result.updated_slots)

        return final_response_messages

    def _advance_flow_util_action(self, state:DialogueState, flow_list:FlowList) -> ActionCall | None:
        while True:
            current_task = state.current_task()
            if current_task is None:
                return ActionCall(action_name='action_listen')

            flow = flow_list.get_flow_by_id(current_task.flow_id)

            step = flow.get_step_by_id(current_task.step_id)

            action_call = self._run_task(step, state)

            if action_call is not None:
                return action_call

    def _run_task(self, step, state) -> ActionCall | None:
        if isinstance(step, StartFlowStep):
            return self._run_start_step(step, state)
        elif isinstance(step, EndFlowStep):
            return self._run_end_step(step, state)
        elif isinstance(step, ActionFlowStep):
            return self._run_action_step(step, state)
        elif isinstance(step, CollectFlowStep):
            return self._run_collection_step(step, state)
        else:
            return None

    def _run_start_step(self, step, state) -> ActionCall | None:
        self._advance_next_step(step, state)
        return None

    def _advance_next_step(self,
                           step: FlowStep,
                           state: DialogueState):
        next_step_id = self._find_next_step_id(step, state)

        state.current_task().step_id = next_step_id

    def _find_next_step_id(self, step, state):
        for link in step.next:
            if isinstance(link, FlowStepStaticLink):
                return link.target
            elif isinstance(link, FlowStepConditionLink):

                if self._eval_condition(state, link.condition):
                    return link.target
            elif isinstance(link, FlowStepFallbackLink):
                return link.target

        return ""

    def _eval_condition(self, state: DialogueState, condition_str: str):
        data = {
            "context": asdict(state.active_system_task) if state.active_system_task else None,
            "slots": state.active_task.slots if state.active_task else None,
        }
        return eval(condition_str, {}, data)

    def _run_end_step(self, step, state) -> ActionCall | None:
        if state.active_system_task:
            state.end_system_task()
        elif state.active_task:
            state.end_active_task()
        return None

    def _run_action_step(self, step, state) -> ActionCall | None:
        self._advance_next_step(step, state)

        action_kwargs = step.args

        if isinstance(action_kwargs, str):
            action_kwargs = asdict(state.active_system_task)["response"]

        return ActionCall(action_name=step.action, action_kwargs=action_kwargs)

    def _run_collection_step(self,
                             step: CollectFlowStep,
                             state: DialogueState) -> ActionCall | None:
        self._try_fill_slots_from_object(step, state)

        if state.active_task.slots.get(step.slot_name):
            if step.validated:
                if self._eval_condition(state, step.validated.condition):
                    self._advance_next_step(step, state)
                    return None
                else:
                    state.remove_slot(step.slot_name)

                    if step.validated.failure_response:
                        return ActionCall(action_name='action_response',
                                          action_kwargs=asdict(step.validated.failure_response))
                    else:
                        return ActionCall(action_name='action_response',
                                          action_kwargs={
                                              "text" : "你填写的槽位信息有误不合法，请重新填写"
                                          })
            else:
                self._advance_next_step(step, state)
                return None
        else:
            state.start_system_task(SystemCollectionInformationContext(
                flow_id="system_collect_information",
                step_id="start",
                response=asdict(step.response),
                slot_name=step.slot_name

            ))

            return None



    def _try_fill_slots_from_object(self,
                                    step:CollectFlowStep,
                                    state:DialogueState):

        # 1. 判断当前是否存在正在执行的业务流程以及卡片信息
        if  state.active_task is None or state.focused_object is None:
            return

        # 2. 卡片类型和槽位的映射
        object_type_slots_mapping = OBJECT_TYPE_TO_SLOT

        # 3. 获取期望的槽位
        expected_slot_name = object_type_slots_mapping.get(state.focused_object.type)

        # 4. 判读当前这一步缺少的槽位是否等于期望的槽位 且当前业务流程上下文中槽位还没有，才利用前面点击过的卡片
        if step.slot_name== expected_slot_name and not state.active_task.slots.get(step.slot_name) :
            state.set_slots({step.slot_name:state.focused_object.id})