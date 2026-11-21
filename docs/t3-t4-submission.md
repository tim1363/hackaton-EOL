# Сдача T3 и T4

Оба образа уже в Harbor. В [кабинете RoboHack](https://robohack.mirea.ru/cabinet?event=robohack-2-0) откройте нужный этап, вставьте его два поля и нажмите «Опубликовать решение». Не перепутайте команды: для T3 и T4 разные образы.

## T4

Дедлайн: **24 ноября, 12:00 МСК**.

**Коммит**

```text
https://github.com/tim1363/hackaton-EOL/commit/3e4f86934a161373fa09bc45488643753a38744b
```

**Команда загрузки**

```bash
docker pull --platform linux/amd64 registry.cookcloud.ru/end-of-line/end-of-line@sha256:8b5d73c8caf9cbe93d394f3c219349c6cda0847f5b68a3642687a72785772e1e
```

[Проверка T4 в публичном Gazebo](https://github.com/tim1363/hackaton-EOL/actions/runs/44891122646): плоская RPE 0,89%, `/odom` и TF около 50 Гц, дрейф за 10 с около 4 мм и 0,005°.

## T3

Дедлайн: **27 ноября, 12:00 МСК**.

**Коммит**

```text
https://github.com/tim1363/hackaton-EOL/commit/0c7b1731a894941c440a57f576b7728e8f7a2157
```

**Команда загрузки**

```bash
docker pull --platform linux/amd64 registry.cookcloud.ru/end-of-line/end-of-line@sha256:c79df74cec484ea461f93345380c2c24ad77d2be0eaf44214b9c93d0f3a1fd3d
```

[Проверка T3 в публичном MuJoCo](https://github.com/tim1363/hackaton-EOL/actions/runs/44891350196): 10 из 10 заездов через T2, каждый в новых контейнерах. Три метра без падения за 5,03–5,18 с после прогрева. Это новая PPO, обученная с нуля. В `ping` стоят `self_trained_rl: true` и скорость 0,4 м/с.

Для подтверждения обучения: [веса, конфиг, логи и результаты в ZIP](t3-training.zip). Те же файлы есть в сдаваемом коммите. Если организаторы запросят материалы отдельным файлом, используйте этот ZIP.

Оба прогона сделаны в публичных симуляторах. Это не результаты закрытого Judge.
