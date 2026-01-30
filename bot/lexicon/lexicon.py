from aiogram import html
LEXICON = {
    "ADMIN":
        {
            "main": "Добро пожаловать в админ-панель. Выберите доступное действие:",
            "TEMPLATE":
                {
                    "main": "Здесь вы можете управлять своими шаблонами.\n"
                            "Доступные действия:",
                    "template_info": html.underline(html.bold("Шаблон: {}\n\n")) +
                                     html.italic("Название:\n") + "{}" +
                                     html.italic("\n\nОписание:\n") + "{}"
                },

        }
}


LEXICON_BUTTONS = {

}