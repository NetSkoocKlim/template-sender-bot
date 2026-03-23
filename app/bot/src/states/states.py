from aiogram.fsm.state import StatesGroup, State

class TemplateAddStates(StatesGroup):
    template_name = State()
    template_description = State()

class TemplateEditStates(StatesGroup):
    template_name = State()
    template_description = State()

class ReceiverMenuStates(StatesGroup):
    add_receivers = State()
    delete_receivers = State()


