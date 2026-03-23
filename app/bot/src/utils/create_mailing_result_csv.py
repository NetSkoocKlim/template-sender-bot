import csv
import io
from itertools import zip_longest


def create_mailing_result_csv(success_list: list[str],
                              unresolved_list: list[str],
                              failed_list: list[str]) -> io.BytesIO:
    file = io.StringIO()
    writer = csv.writer(file)
    headers = ["Успешно отправлено", "Не использовали бота(или поменяли юзернейм", "Не удалось отправить"]
    writer.writerow(headers)
    for row in zip_longest(success_list, unresolved_list, failed_list, fillvalue=''):
        writer.writerow(row)
    return io.BytesIO(file.getvalue().encode('utf-8-sig'))

