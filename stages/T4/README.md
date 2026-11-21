# T4 / Одометрия

[ТЗ (PDF)](spec.pdf) · [Коммит и образ для отправки](../../docs/t4-submission.md)

Узел оценивает путь по `/scan` и `/imu/data`. IMU даёт ориентацию, а сопоставление лазерных сканов с поверхностями даёт смещение. Узел публикует `/odom` и TF `odom → trunk` с общими метками времени. Он не читает `/cmd_vel` и не управляет роботом.

В публичном Gazebo с lockstep: RPE 0,89%, частота около 50 Гц, дрейф за 10 с около 4 мм и 0,005°. Истинная поза поступала только в скрипт проверки. [Лог CI](https://github.com/tim1363/hackaton-EOL/actions/runs/44891122646).

## Запуск проверки

Из корня репозитория. `SIM_IMAGE` указывает на публичный образ организаторов, скачанный из Harbor.

```bash
docker buildx build --platform linux/amd64 --load \
  -f stages/T4/Dockerfile -t eol-t4:local .
bash stages/T4/test_image.sh eol-t4:local "$SIM_IMAGE"
```
