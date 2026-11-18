# Локальный симулятор Unitree Go1

[Полная инструкция организаторов](https://github.com/Urika000/go1-simulator-public/blob/main/docs/SIMULATOR_LAUNCH_GUIDE_RU.md). Практически проверенный организаторами хост: Linux Ubuntu 22.04 amd64, Docker Engine, Docker Compose, Git и Python 3.10+. ROS 2 на хосте не нужен. На проверенном Windows-ПК Docker не найден; для первых интеграционных прогонов возьмите Linux-машину с Docker.

```bash
git clone https://github.com/Urika000/go1-simulator-public.git
cd go1-simulator-public
docker login registry.cookcloud.ru
export SIM_IMAGE=registry.cookcloud.ru/go1-hackathon-remote-stage/go1-sim:v1.0
docker pull "${SIM_IMAGE}"

# Поднимаем только симулятор, без узлов команды.
python3 run_local.py --task T2 --sim-only --sim-image "${SIM_IMAGE}" --headless
```

- T2/T3: MuJoCo Lowlevel. T4: Gazebo Classic + CHAMP. T5: Gazebo Course. Вместо T2 можно указать нужный этап. Для T5 проверьте оба варианта: `--course-width 2.0` и `--course-width 1.0`.
- Запуск с `--sim-only` не подключает решение команды. Когда этап реализован, замените этот флаг на `--participant-image <локальный_образ>`.
- Локальная симуляция не содержит закрытого Judge. Публичный ground truth годится для сравнительных замеров, но его нельзя использовать на вход одометрии, RL или навигации.
