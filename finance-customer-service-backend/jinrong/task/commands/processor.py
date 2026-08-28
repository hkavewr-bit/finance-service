from jinrong.domain.contexts import TaskContext, InterruptedSystemContext, StartedSystemContext, ResumedSystemContext, \
    SystemTaskResumeFailedContext, CanceledSystemContext
from jinrong.domain.state import DialogueState
from jinrong.task.commands.command import Command, StartFlowCommand, SetSlotsCommand, ResumeFlowCommand, \
    CancelFlowCommand
from jinrong.task.flows.flows import FlowList


class CommandProcessor:

    def process_command(self,
                        commands :list[Command],
                        state: DialogueState,
                        flow_list :FlowList):
        for command in commands:
            if isinstance(command,StartFlowCommand):
                self._start_flow(command,state,flow_list)
            elif isinstance(command,SetSlotsCommand):
                self._update_slots(command,state,flow_list)
            elif isinstance(command,ResumeFlowCommand):
                self._resumed_flow(command,state,flow_list)
            elif isinstance(command,CancelFlowCommand):
                self._cancel_flow(state,flow_list)
            else:
                pass

    def _start_flow(self,
                    command : StartFlowCommand,
                    state :DialogueState,
                    flow_list: FlowList):

        start_flow_id = command.flow
        start_flow_name = flow_list.get_flow_by_id(start_flow_id).name

        activated_task = state.active_task

        if activated_task is not None:
            if activated_task.flow_id == start_flow_id:
                return
            state.remove_paused_task(start_flow_id)

            interrupted_flow_id = activated_task.flow_id

            interrupted_flow_name = flow_list.get_flow_by_id(interrupted_flow_id).name

            state.interrupt_active_task()

            state.start_task( TaskContext(
                flow_id = start_flow_id,
                step_id = "start"
            ))

            state.start_system_task(InterruptedSystemContext(
                flow_id="system_task_interrupted",
                step_id="start",
                interrupted_flow_id=interrupted_flow_id,
                interrupted_flow_name=interrupted_flow_name,
                started_flow_id=start_flow_id,
                started_flow_name=start_flow_name
            ))

        else:
            state.remove_paused_task(start_flow_id)

            state.start_task( TaskContext(
                flow_id = start_flow_id,
                step_id = "start"
            ))

            state.start_system_task(StartedSystemContext(
                flow_id="system_task_started",
                step_id="start",
                started_flow_id=start_flow_id,
                started_flow_name=start_flow_name
            ))



    def _update_slots(self,
                      command: SetSlotsCommand,
                      state: DialogueState,
                      flow_list: FlowList):
        state.set_slots(command.slots)

    def _resumed_flow(self,
                      command: ResumeFlowCommand,
                      state: DialogueState,
                      flow_list: FlowList):
        resumed_flow_id = command.flow

        activated_task = state.active_task

        if activated_task is not None:

            if resumed_flow_id is None:
                return

            if resumed_flow_id==activated_task.flow_id:
                return

            interrupted_flow_id = activated_task.flow_id
            interrupted_flow_name = flow_list.get_flow_by_id(interrupted_flow_id).name

            state.interrupt_active_task()

            resumed = state.resume_task(resumed_flow_id)

            if not resumed:
                state.resume_task()

                state.start_system_task(SystemTaskResumeFailedContext(
                    flow_id="system_task_resume_failed",
                    step_id="start",
                ))
            else:
                state.start_system_task(ResumedSystemContext(
                    flow_id="system_task_resumed",
                    step_id="start",
                    resumed_flow_id=state.active_task.flow_id,
                    resumed_flow_name=flow_list.get_flow_by_id(state.active_task.flow_id).name
                ))


    def _cancel_flow(self,
                     state: DialogueState,
                     flow_list: FlowList):
        active_task = state.active_task

        state.cancel_active_task()

        state.start_system_task(CanceledSystemContext(
            flow_id="system_task_canceled",
            step_id="start",
            canceled_flow_id = active_task.flow_id,
            canceled_flow_name= flow_list.get_flow_by_id(active_task.flow_id).name
        ))

