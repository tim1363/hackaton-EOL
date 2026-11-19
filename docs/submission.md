# Сдача T1

Отправили 18.11.2026 в 23:13 МСК. Редакция решения 1, версия задания 4.

## Что отправили

Коммит из кабинета: [`6848a22` в общем репозитории](https://github.com/tim1363/hackaton-EOL/commit/6848a22b1cebd5a1b289c9c13962f3a792d6e369).

Команда из кабинета:

```bash
docker pull --platform linux/amd64 registry.cookcloud.ru/end-of-line/end-of-line@sha256:91313c63bf47ede5e9d170eb4ce3954e9251552dce8bfb03b4bf545e059a34eb
```

Для загрузки нужна учётка Harbor с доступом к образу.

## Из чего собрали образ

В CI использовали [`150f827` из репозитория для сдачи](https://github.com/tim1363/hackaton-EOL-submission/commit/150f82738ebe9d8ed2a9e63530fcedbc62b5da59). Dockerfile, скрипт запуска и скрипт проверки совпадают с файлами из `stages/T1/` коммита, указанного в кабинете.

В этом образе нет модели: он только отвечает на `ping`. Образ и материалы обучения для T3 сдаём отдельно.

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
