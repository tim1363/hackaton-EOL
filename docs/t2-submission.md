# Сдача T2

Дедлайн: **21 ноября, 12:00 МСК**. Образ уже в Harbor. Лидеру ничего собирать не нужно.

Откройте T2 в [кабинете RoboHack](https://robohack.mirea.ru/cabinet?event=robohack-2-0), вставьте два поля и нажмите «Опубликовать решение».

**Ссылка на коммит GitHub**

```text
https://github.com/tim1363/hackaton-EOL/commit/9aea37286f5993f2ef8c017390031ce3d00e8966
```

**Команда загрузки образа**

```bash
docker pull --platform linux/amd64 registry.cookcloud.ru/end-of-line/end-of-line@sha256:28054e380fd4071215a3d9b0c61b25f18ea6886b9e66727d96424cbc83d8b4d9
```

## Что проверили

[Сборка и тесты в CI](https://github.com/tim1363/hackaton-EOL/actions/runs/44802298027). Образ `linux/amd64`, `ping` и узел ROS работают без сети и без root. В тесте со своими часами ROS получили 100 Гц за 5 с, паузу до 10 мс и переход в удержание через 0,45 с. Узел отклонил 30 команд с NaN/Inf и переход с самоколлизией. Это тест команды, не результат Judge.

Образ объявляет только T2. В нём нет модели T3, поэтому `self_trained_rl` здесь `false`. Сданный образ T1 не меняли.
