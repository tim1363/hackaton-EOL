# T1 / Контейнер

**Дедлайн: 19.11.2026, 12:00 МСК.** [ТЗ v4 (PDF)](spec.pdf) | [Чек-лист сдачи](../../docs/submission.md)

**CI PASS, не сдано.** [GitHub Actions](https://github.com/tim1363/hackaton-EOL/actions/runs/44300117644) собрал `linux/amd64` и проверил запуск без сети и root.

- [Dockerfile](Dockerfile): Ubuntu 22.04, ROS 2 Humble, CycloneDDS и непривилегированный UID.
- [entrypoint.sh](entrypoint.sh): `ping` выводит один JSON, не поднимая ROS.
- [verify_t1.py](verify_t1.py): проверяет платформу, окружение, UID, код выхода и ответ `ping` за 10 секунд.

> [!NOTE]
> Образ пока только для T1: `supported_tasks: []`, `self_trained_rl: false`, `preferred_speed_mps: null`. Уточняем у организаторов, принимают ли пустой список. Незаконченные задачи не заявляем.

## Сборка и проверка

Из корня репозитория на машине с Docker Engine и Buildx:

```bash
docker buildx build --platform linux/amd64 --load -t robohack-participant:t1 stages/T1

# Без сети и автоскачивания. Проверяем то, что только что собрали.
python3 stages/T1/verify_t1.py robohack-participant:t1
```

В Windows можно заменить `python3` на `python`. Интернет нужен при сборке для загрузки базового образа и пакетов.
