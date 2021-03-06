Планирование бюджета для ДребеДенег
===================================

Эта программа помогает планировать бюджет в ДребеДеньгах.
Пример работы можно посмотреть тут: https://goo.gl/Dbwfpt


Особенности
-----------

* Программа исключительно отображает данные и никаких изменений не вносит
* График остатков на 18 месяцев вперёд (см `to_date=...` в `crawl_dd.py`)
* График свободных денег (те, которые можно потратить и не уйти в минус в бижайшем будущем)
* Счета в группе "Скрытых сумм" не отображаются на графиках
* Автоматическое погашение кредитной карты (автоматически "планируется" платёж по кредитной карте в конце льготного периода)
* Все суммы переводятся в одну валюту

Использование
-------------

1. Сохраняем исходный код на свой компьютер

1. Устанавливаем Python 2.7, Google App Engine Python SDK

1. Устанавливаем библиотеку `lxml` в папку `lib`

    pip install -t lib lxml

1. Указываем логин-пароль к ДД в файле `crawl_dd.py`:

    api = DdApi(email='demo@example.com', password='demo')

1. Запускаем

    dev_appserver.py --port=8123 .

1. Заходим на страницу http://localhost:8123/chart/

Настройка
---------

1. Для крупных сумм (более 10 т.р.) на графике отображается маркер с числом. Порог можно настроить в `www/js/balance.js`, `Math.abs(t.amount)>1000000`.
1. Если нужен рассчёт кредитной карты, то стоит указать её ID (правой кнопкой в ДД по счёту в блоке "остатки", `Посмотреть исхоный код`, и там можно найти что-то типа `pln12222222`. Цифры это и есть нужный id). Так же нужно указать дату выписки и льготный период.

Лицензия
--------
Apache 2.0

Список изменений
----------------

v1.0.0 - 2018-04-08
* Первая версия

Автор
-----
Vladimir Sitnikov <sitnikov.vladimir@gmail.com>
