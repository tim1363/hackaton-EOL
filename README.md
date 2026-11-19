# EOL / RoboHack 2.0

Учим Go1 ходить и ориентироваться в симуляторе.

[ТЗ](docs/technical-specification.pdf) · [Симулятор](docs/simulator.md) · [Кабинет](https://robohack.mirea.ru/cabinet)

## Этапы

| Этап | Дедлайн (МСК) | Что готово | Статус |
| --- | --- | --- | --- |
| [T1 / Контейнер](stages/T1/) | 19.11, 12:00 | [Коммит и образ из кабинета](docs/submission.md#что-отправили) | Сдано |
| [T2 / Safety](https://github.com/tim1363/hackaton-EOL/tree/t2-t3-mishanya/stages/T2) | 21.11, 12:00 | Защита суставов, ROS-узел и локальные тесты | В работе |
| [T4 / Odom](https://github.com/tim1363/hackaton-EOL/tree/t2-t3-mishanya/stages/T4) | 24.11, 12:00 | Прототип LiDAR + IMU | Проверить в Gazebo |
| [T3 / Ходьба](stages/T3/) | 27.11, 12:00 | Есть обученные модели | Сравнить в симуляторе организаторов |
| [T5 / Nav2 + ArUco](stages/T5/) | 27.11, 12:00 | Список топиков и проверок | Нет реализации |

## Как идёт T3

Тим обучил свою модель на домашнем ПК. В нашем MuJoCo она прошла 100 из 100 заездов без падений. [Как проверяли](stages/T3/).

## Как проверить образ T1

Из корня репозитория, с Docker и Buildx:

```bash
docker buildx build --platform linux/amd64 --load -t robohack-participant:t1 stages/T1
python3 stages/T1/verify_t1.py robohack-participant:t1
```

Без Docker: [лог проверки T1 в CI](https://github.com/tim1363/hackaton-EOL/actions/runs/44300117644).
