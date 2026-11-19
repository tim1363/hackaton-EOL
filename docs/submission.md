# Как сдать T1

Дедлайн: 19.11.2026, 12:00 МСК. Капитан вставляет ссылку на коммит и команду загрузки образа в [личном кабинете](https://robohack.mirea.ru/cabinet). ZIP не нужен. Если форма недоступна, проверьте [состав команды](https://robohack.mirea.ru/cabinet/team?event=robohack-2-0).

## Текущий образ T1

Коммит: [150f82738ebe9d8ed2a9e63530fcedbc62b5da59](https://github.com/tim1363/hackaton-EOL-submission/commit/150f82738ebe9d8ed2a9e63530fcedbc62b5da59).

```bash
docker pull --platform linux/amd64 registry.cookcloud.ru/end-of-line/end-of-line@sha256:91313c63bf47ede5e9d170eb4ce3954e9251552dce8bfb03b4bf545e059a34eb
```

Этот образ только для T1: `supported_tasks: []`, `self_trained_rl: false`. Для T3 нужны отдельный образ, его коммит и digest, веса, конфиг обучения, журналы W&B и результаты проверки.

## Если нужно пересобрать T1 без Linux

1. Если исходники изменились, опубликуйте коммит и обновите `SOURCE_SHA` в `.github/workflows/t1-submission.yml`.
2. В [настройках Actions](https://github.com/tim1363/hackaton-EOL/settings/secrets/actions) задайте секреты `HARBOR_USERNAME` и `HARBOR_PASSWORD`, а также переменную `HARBOR_IMAGE_REPO` со значением `registry.cookcloud.ru/end-of-line/end-of-line`. Пароль не кладите в Git.
3. В [T1 / Build and publish](https://github.com/tim1363/hackaton-EOL/actions/workflows/t1-submission.yml) выберите **Run workflow**, ветку `main` и **Push the verified image to Harbor**. Без галочки публикации не будет.
4. Из **Summary** скопируйте **GitHub commit** и **Docker pull** в кабинет. CI проверяет образ, но не сдаёт его за команду.

## Если собираете вручную на Linux

1. Проверьте, что сдаваемый коммит открывается без входа в GitHub.
2. Соберите и проверьте образ из чистого checkout этого коммита. Команды ниже рассчитаны на структуру рабочего репозитория. В отдельном репозитории для сдачи Dockerfile и скрипт проверки лежат в корне.

```bash
git status --short
git rev-parse HEAD

docker buildx build --platform linux/amd64 --load -t robohack-participant:t1 stages/T1
python3 stages/T1/verify_t1.py robohack-participant:t1
```

3. Войдите в Harbor и отправьте проверенный образ.

```bash
docker login registry.cookcloud.ru
IMAGE_REPO="registry.cookcloud.ru/end-of-line/end-of-line"
IMAGE="${IMAGE_REPO}:$(git rev-parse --short=12 HEAD)"
docker tag robohack-participant:t1 "$IMAGE"
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

4. Скопируйте полный digest из вывода и проверьте загрузку.

```bash
read -r -p 'Digest (sha256:...): ' DIGEST
IMAGE_BY_DIGEST="${IMAGE_REPO}@${DIGEST}"
docker pull --platform linux/amd64 "$IMAGE_BY_DIGEST"
python3 stages/T1/verify_t1.py "$IMAGE_BY_DIGEST"
printf 'docker pull --platform linux/amd64 %s\n' "$IMAGE_BY_DIGEST"
```

5. Вставьте в кабинет ссылку на коммит и выведенную команду `docker pull`. Не подставляйте ссылку на ветку или тег `latest`.

[Официальная инструкция по загрузке решения](https://github.com/Urika000/go1-simulator-public/blob/main/docs/Инструкция_по_загрузке_решения.md).
