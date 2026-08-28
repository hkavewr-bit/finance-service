from pathlib import Path

from jinrong.chitchat.handler import ChitchatHandler
from jinrong.chitchat.responder import ChitchatResponder
from jinrong.clarify.handler import ClarifyResponder
from jinrong.engines.dialogue_engine import DialogueEngine
from jinrong.knowledge.handler import KnowledgeHandler
from jinrong.knowledge.intents import KNOWLEDGE_INTENTS
from jinrong.knowledge.provider.knowlege import (
    ApiAccountProvider,
    ApiCardProvider,
    ApiTransactionProvider,
    ApiLoanProductProvider,
    ApiWealthProductProvider,
    RagDefaultProvider,
    FaqDefaultProvider,
)
from jinrong.knowledge.provider.register import KnowledgeRegister
from jinrong.knowledge.responder import KnowledgeResponder
from jinrong.plan.planner import TurnPlanner
from jinrong.plan.validator import TurnPlanValidator
from jinrong.task.action.builder import build_action_runner
from jinrong.task.commands.processor import CommandProcessor
from jinrong.task.flows.executor import FlowExecutor
from jinrong.task.flows.handler import TaskHandler
from jinrong.task.flows.loader import FlowsLoader


PROJECT_DIR = Path(__file__).resolve().parents[2]

FLOW_CONFIG_DIR = PROJECT_DIR / "flow_config"

def build_dialogue_engine():
    flow_list = FlowsLoader().load_multi_yaml(
        [ FLOW_CONFIG_DIR / yaml  for yaml in ("system_flows.yml", "user_flows.yml") ]
    )

    return DialogueEngine(
        turn_planner=TurnPlanner(),
        turn_plan_validator=TurnPlanValidator(),
        clarify_responder=ClarifyResponder(),
        task_handler=TaskHandler(
            flow_list = flow_list,
            command_processor=CommandProcessor(),
            flow_executor=FlowExecutor(),
            action_runner = build_action_runner()
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            knowledge_register = KnowledgeRegister(
                providers = [
                    ApiAccountProvider(),
                    ApiCardProvider(),
                    ApiTransactionProvider(),
                    ApiLoanProductProvider(),
                    ApiWealthProductProvider(),
                    RagDefaultProvider(),
                    FaqDefaultProvider()
                ]
            ),
            knowledge_responder = KnowledgeResponder()
            ),
        chitchat_handler=ChitchatHandler(
            chitchat_responder=ChitchatResponder()
        ),

    )

if __name__ == '__main__':
    print(FLOW_CONFIG_DIR)