# Локальный симулятор Unitree Go1

[Инструкция организаторов](https://github.com/Urika000/go1-simulator-public#readme). Проверенная платформа: Ubuntu 22.04 amd64 с Docker Engine, Compose, Git и Python 3.10+. ROS 2 уже в образе.

Запуск T3 без окна и без кода команды:

```bash
git clone https://github.com/Urika000/go1-simulator-public.git
cd go1-simulator-public
docker login registry.cookcloud.ru
export SIM_IMAGE=registry.cookcloud.ru/go1-hackathon-remote-stage/go1-sim:v1.0
docker pull "${SIM_IMAGE}"

python3 run_local.py --task T3 --sim-only --sim-image "${SIM_IMAGE}" --headless
```

- T2 и T3 используют MuJoCo Lowlevel. T4 работает в Gazebo Classic + CHAMP, T5 в Gazebo Course. Для T5 проверьте `--course-width 2.0` и `--course-width 1.0`.
- Чтобы подключить образ команды, замените `--sim-only` на `--participant-image <тег_образа>`.
- Закрытого Judge здесь нет. Ground truth используйте только для замеров, не как вход контроллера.
