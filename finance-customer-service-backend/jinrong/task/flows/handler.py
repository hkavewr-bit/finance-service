from jinrong.domain.messages import BotMessage
from jinrong.domain.state import DialogueState
from jinrong.task.action.runner import ActionRunner
from jinrong.task.commands.command import Command
from jinrong.task.commands.processor import CommandProcessor
from jinrong.task.flows.executor import FlowExecutor
from jinrong.task.flows.flows import FlowList


class TaskHandler:

    def __init__(self,
                 flow_list :FlowList ,
                 command_processor: CommandProcessor,
                 flow_executor: FlowExecutor,
                 action_runner: ActionRunner):
        self.flow_list = flow_list
        self.command_processor = command_processor
        self.flow_executor = flow_executor
        self.action_runner = action_runner

    async def handle(self,
                     commands:list[Command],
                     dialogue_state : DialogueState):
        self.command_processor.process_command(commands, dialogue_state,self.flow_list)

        bot_messages = await self.flow_executor.execute_flow(
            dialogue_state,
            action_runner = self.action_runner,
            flow_list=self.flow_list
        )
        return bot_messages
