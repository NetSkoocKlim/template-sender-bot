from enum import StrEnum, auto, Enum


class AdminPanelOptions(StrEnum):
    user_list = "Управление списком пользователей"
    template = "Управление шаблонами"
    statistic = "Просмотр статистики"
    mailing = "Управление рассылкой"
    back = "Вернуться к админ-панели"

class AdminPanelTemplateOptions(StrEnum):
    add_template = "Создать новый шаблон"
    edit_template = "Посмотреть созданные шаблоны"
    back = AdminPanelOptions.back

class TemplateEditAction(str, Enum):
    view_tmplt = auto()
    choose_tmplt = auto()
    name_tmplt = auto()
    desc_tmplt = auto()
    delete_tmplt = auto()
    back_tmplt = auto()

    @property
    def label(self) -> str:
        labels = {
            TemplateEditAction.choose_tmplt: "Выбрать для рассылки",
            TemplateEditAction.name_tmplt: "Изменить название",
            TemplateEditAction.desc_tmplt: "Изменить описание",
            TemplateEditAction.delete_tmplt: "Удалить шаблон",
            TemplateEditAction.back_tmplt: AdminPanelOptions.back
        }
        return labels.get(self, self.value)


class AdminPanelReceiverOptions(StrEnum):
    view_rcvr = "Посмотреть список пользователей"
    expand_rcvr = "Добавить пользователей"
    delete_rcvr = "Удалить пользователей"
    clear_rcvr = "Очистить список пользователей"
    back = AdminPanelOptions.back


class AdminPanelMailingOptions(StrEnum):
    view_chosen_template = "Посмотреть выбранный шаблон"
    begin_mailing = "Начать рассылку"
    back = AdminPanelOptions.back

class AdminPanelChosenTemplateOptions(StrEnum):
    choose_another = "Выбрать другой шаблон"
    back2mlng = "Назад к рассылке"

class AdminPanelStatisticOptions(StrEnum):
    download_mlngRes = "Скачать результат последней рассылки"
    view_mlngs = "Посмотреть все рассылки"
    back = AdminPanelOptions.back

class MailingInfoOptions(StrEnum):
    download_lst_mlngRes = "Скачать результат рассылки"
    check_template = "Посмотреть используемый шаблон"
    back2st_mlngs = "Назад к рассылкам"


