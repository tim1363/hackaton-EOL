# T1 · Подготовка сдачи решения

**Сдать до 19.11.2026, 12:00 МСК.** [Техническое задание (PDF)](spec.pdf) · [Инструкция капитану](../../docs/submission.md)

**Сделано:** образ на Ubuntu 22.04 / ROS 2 Humble с CycloneDDS описан в [Dockerfile](Dockerfile), запуск настроен от непривилегированного пользователя. [entrypoint.sh](entrypoint.sh) при `ping` возвращает один JSON, не требует ROS-инициализации и не обращается к сети. Локально скрипт вернул код 0 и корректный JSON; это не проверка Docker-образа.

Образ пока рассчитан только на T1. `supported_tasks` пуст, `self_trained_rl` — `false`, `preferred_speed_mps` — `null`. Приём пустого списка нужно подтвердить у организаторов; незавершённые T2–T5 не заявляем.

## Сборка и проверка

Из корня репозитория на машине с Docker Engine и Buildx:

```bash
docker buildx build --platform linux/amd64 --load -t robohack-participant:t1 stages/T1
python3 stages/T1/verify_t1.py robohack-participant:t1
```

В Windows можно заменить `python3` на `python`. Проверка запускает контейнер без сети и без скачивания образа; проверяет Linux/amd64, Ubuntu, ROS, CycloneDDS, UID и JSON в пределах 10 секунд. Интернет нужен на этапе сборки для загрузки базового образа и зависимостей. Результат сборки и проверки в CI — на вкладке [Actions](https://github.com/tim1363/hackaton-EOL/actions).
