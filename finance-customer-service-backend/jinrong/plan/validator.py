from jinrong.domain.state import DialogueState
from jinrong.knowledge.intents import KnowledgeIntent
from jinrong.plan.turn_plan import TurnPlan, ClarifyReason, TurnPlanValidatedResult, TaskTurnPlan, KnowledgeTurnPlan
from jinrong.task.commands.command import StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand
from jinrong.task.flows.flows import FlowList


class TurnPlanValidator:

    def valid(self,
              turn_plan: TurnPlan,
              dialogue_state: DialogueState,
              *,
              flow_list: FlowList,
              knowledge_intents: dict[str, KnowledgeIntent]
              ):
        activated_tracks = turn_plan.activated_tracks()

        if not activated_tracks:
            return self._reject(ClarifyReason.MISSING_TRACK)

        if len(activated_tracks) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS)

        selected_track = activated_tracks[0]

        if selected_track == "task":
            return self._validate_task_track(turn_plan.task, flow_list)

        if selected_track == "knowledge":
            return self._validate_knowledge_track(dialogue_state, turn_plan.knowledge, knowledge_intents)

        return TurnPlanValidatedResult(valid=True)

    def _reject(self, reason: ClarifyReason) -> TurnPlanValidatedResult:
        return TurnPlanValidatedResult(valid=False, reason=reason)

    def _validate_task_track(self, task: TaskTurnPlan, flow_list: FlowList):
        # 校验1：task轨道是否有对应的命令（commands）
        if not task.commands:
            return self._reject(ClarifyReason.MISSING_TASK_COMMANDS)
        # 校验2：命令(command)是否合法
        if not all(isinstance(command, (StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand)) for
                   command in task.commands):
            return self._reject(ClarifyReason.INVALID_TASK_COMMANDS)

        # 校验3: 是否有多个开启command
        start_command = [command for command in task.commands if isinstance(command, StartFlowCommand)]

        if len(start_command) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TASK_FLOWS)
        # 校验4：是否有流程
        if start_command:
            flow_id = start_command[0].flow
            flow = flow_list.get_flow_by_id(flow_id)

            if flow is None:
                return self._reject(ClarifyReason.UNKNOWN_TASK_FLOW)

        return TurnPlanValidatedResult(valid=True)

    def _validate_knowledge_track(self, dialogue_state: DialogueState, knowledge: KnowledgeTurnPlan,
                                  knowledge_intents: dict[str, KnowledgeIntent]):

        if not knowledge.intents:
            return self._reject(ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        for llm_intent in knowledge.intents:
            knowledge_object = knowledge_intents[llm_intent]
            require_type = knowledge_object.requires_object_type

            focus_object = dialogue_state.focused_object

            if require_type is not None:
                if focus_object is None or focus_object.type != require_type:
                    return self._reject(ClarifyReason.MISSING_FOCUSED_OBJECT)

        return TurnPlanValidatedResult(valid=True)
