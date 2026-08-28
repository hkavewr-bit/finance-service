import importlib
import inspect
import pkgutil

from jinrong.task.action.base import Action
from jinrong.task.action.builtin.listener import ActionListener
from jinrong.task.action.builtin.response import ActionResponse
from jinrong.task.action.register import ActionRegistry
from jinrong.task.action.runner import ActionRunner


def registry_builtin_actions(action_runner: ActionRunner):
    action_runner.registry.register(ActionResponse())
    action_runner.registry.register(ActionListener())


def registry_customer_action(action_runner: ActionRunner):
    customer_action_package = importlib.import_module("jinrong.task.action.customer")

    for _, module_name, is_pkg in pkgutil.iter_modules(customer_action_package.__path__,
                                                       prefix=customer_action_package.__name__ + "."):
        if is_pkg:
            continue
        module = importlib.import_module(module_name)

        for _,class_obj in inspect.getmembers(module,inspect.isclass):

            if not issubclass(class_obj,Action) or class_obj is Action:
                continue

            action_runner.registry.register(class_obj())

def build_action_runner()  -> ActionRunner:

    action_runner = ActionRunner(ActionRegistry())

    registry_customer_action(action_runner)
    registry_builtin_actions(action_runner)
    return action_runner

if __name__ == '__main__':
    build_action_runner()
