# T3 / Ходьба

Дедлайн: 27.11.2026, 12:00 МСК. [ТЗ (PDF)](spec.pdf).

В образе новая PPO-модель, обученная с нуля. Сеть корректирует рысь и выдаёт цели для 12 суставов. Она получает команду скорости из `/cmd_vel` и состояние из `/lowstate`. В `/lowcmd` пишет только защита T2, сама модель пишет в `/lowcmd_bare`. В `ping` заявлены 0,4 м/с и `self_trained_rl: true`.

Это не старые веса Тима с домашнего ПК и не [Brax v3 из командной ветки](https://github.com/tim1363/hackaton-EOL/blob/t2-t3-mishanya/stages/T3/TRAINING.md). Этот вариант обучен под PD-управление публичного симулятора.

## Подтверждение обучения

- [Веса](weights/actor.npz) и [описание входов](weights/interface.json).
- [Настройки](training/config.json), [журнал PPO](training/train.log) и [метрики эпизодов](training/training.monitor.csv).
- [Тест на 20 новых сценариях](training/holdout.json): 20/20 без падений, включая 10 усложнённых. Это локальная среда.
- [Отдельная финальная проверка](training/final-test.json): 100/100 без падений, в среднем 5,42 с на 3 метра. Из них 50 усложнённых. Это также локальная среда, не Judge.
- [Прогон в публичном MuJoCo](https://github.com/tim1363/hackaton-EOL/actions/workflows/t3-submission.yml): каждый эпизод использует новый контейнер. Истинная позиция используется только в тесте для измерения пути.

Для повторения обучения нужны Python 3.13, PyTorch CPU, Stable Baselines3 2.9.2, Gymnasium 1.4.0, NumPy 2.5.5 и MuJoCo 3.3.7. Сцена и ассеты Go1: [MuJoCo Menagerie, ревизия из ТЗ](https://github.com/google-deepmind/mujoco_menagerie/tree/0059d4335f8156206f63a35662313385f7ad6d74/unitree_go1).

```bash
python3 stages/T3/training/source/lab.py train \
  --scene /path/to/unitree_go1/scene.xml --out /path/to/new-run \
  --servo-kp 85 --gait-hz 1.8 --action-radius 0.10 --objective course \
  --steps 393216 --workers 6 --episodes 10 --scenario mixed --seed 63
```
