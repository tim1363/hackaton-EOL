# Сдача T4

Дедлайн: 24 ноября, 12:00 МСК. В [кабинете](https://robohack.mirea.ru/cabinet?event=robohack-2-0) откройте T4, вставьте два поля и нажмите «Опубликовать решение». Собрать образ заново не нужно.

**Коммит**

```text
https://github.com/tim1363/hackaton-EOL/commit/3e4f86934a161373fa09bc45488643753a38744b
```

**Команда загрузки**

```bash
docker pull --platform linux/amd64 registry.cookcloud.ru/end-of-line/end-of-line@sha256:8b5d73c8caf9cbe93d394f3c219349c6cda0847f5b68a3642687a72785772e1e
```

[Проверка в публичном Gazebo](https://github.com/tim1363/hackaton-EOL/actions/runs/44891122646): RPE 0,89%, одометрия и TF около 50 Гц, дрейф за 10 с около 4 мм и 0,005°. Это наш прогон, не оценка Judge.
