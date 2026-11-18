# T1 / Чек-лист сдачи

**До 19.11.2026, 12:00 МСК.** Перед отправкой проверьте допуск и число оставшихся попыток в кабинете. Если кабинет блокирует сдачу из-за состава, проверьте [раздел «Команда»](https://robohack.mirea.ru/cabinet/team?event=robohack-2-0). ZIP для T1 не обязателен: нужны коммит и команда загрузки образа.

## Без Linux на своём ПК

1. Исходники T1 уже лежат в [публичном коммите](https://github.com/tim1363/hackaton-EOL-submission/commit/150f82738ebe9d8ed2a9e63530fcedbc62b5da59). Рабочее репо остаётся приватным. Уточните у организаторов, принимают ли образ с `supported_tasks: []`.
2. Нужна выданная организаторами учётка с правом записи в Harbor. В [Secrets and variables → Actions](https://github.com/tim1363/hackaton-EOL/settings/secrets/actions) добавьте секреты `HARBOR_USERNAME` и `HARBOR_PASSWORD`. Во вкладке **Variables** добавьте `HARBOR_IMAGE_REPO`: выданный путь вида `registry.cookcloud.ru/go1-hackathon-remote-stage-<team>/<team>` без тега или digest. Пароль не отправляйте в чате и не добавляйте в Git. Используйте отдельную учётку для проекта, если её выдали.
3. В [T1 / Build and publish](https://github.com/tim1363/hackaton-EOL/actions/workflows/t1-submission.yml) нажмите **Run workflow**, выберите `main` и отметьте **Push the verified image to Harbor**. Без галочки CI только собирает и проверяет образ.
4. После зелёного прогона с публикацией откройте **Summary**. Скопируйте **GitHub commit** и **Docker pull** в два поля кабинета. Команда уже содержит SHA-256 digest образа, который CI скачал из Harbor и повторно проверил. CI ничего не отправляет в кабинет.

## Если собираете вручную на Linux

1. Запустите [проверку T1](../stages/T1/README.md). Для текущей заготовки уточните, принимает ли T1 образ с пустым `supported_tasks`: в ТЗ это не оговорено явно. Не указывайте этапы, которые образ не запускает.
2. Подготовьте **публичную** версию исходников команды. Не меняйте видимость рабочего репозитория без согласования. Можно создать отдельный публичный репозиторий для сдачи и перенести туда проверенные исходники, Dockerfile, конфигурации и инструкцию, не включая закрытую историю, персональные данные и секреты. Зафиксируйте исходники коммитом.
3. Из чистого checkout сдаваемого коммита соберите и проверьте образ на машине с Docker Engine и Buildx. В примере сохранена структура этого репозитория; выполняйте команды из его корня в Bash.

```bash
git status --short
git rev-parse HEAD

# Собираем тот же SHA, который укажем судьям.
docker buildx build --platform linux/amd64 --load -t robohack-participant:t1 stages/T1
python3 stages/T1/verify_t1.py robohack-participant:t1
```

4. Войдите в Harbor с учётной записью организаторов и отправьте тот же проверенный образ. Пароль вводите интерактивно.

```bash
# Пароль вводим в prompt, не пишем в команду.
docker login registry.cookcloud.ru
read -r -p 'Имя команды в Harbor: ' TEAM_NAME
IMAGE_REPO="registry.cookcloud.ru/go1-hackathon-remote-stage-${TEAM_NAME}/${TEAM_NAME}"
IMAGE="${IMAGE_REPO}:$(git rev-parse --short=12 HEAD)"
docker tag robohack-participant:t1 "$IMAGE"
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

5. Возьмите полный `Digest: sha256:…` из вывода и выполните проверку загрузки.

```bash
# Тег меняется. Digest фиксирует конкретный образ.
read -r -p 'Digest (sha256:...): ' DIGEST
IMAGE_BY_DIGEST="${IMAGE_REPO}@${DIGEST}"
docker pull --platform linux/amd64 "$IMAGE_BY_DIGEST"
python3 stages/T1/verify_t1.py "$IMAGE_BY_DIGEST"
printf 'docker pull --platform linux/amd64 %s\n' "$IMAGE_BY_DIGEST"
```

6. Когда сдача откроется, капитан вставляет в [кабинет](https://robohack.mirea.ru/cabinet) **ссылку на конкретный публичный коммит** вида `https://github.com/owner/repo/commit/<full-sha>` и **полную команду `docker pull`** из предыдущего шага. Ссылка на ветку, тег `latest` и архив вместо этих двух полей не подходят. Убедитесь, что коммит открывается без входа.

[Официальная инструкция по загрузке решения](https://github.com/Urika000/go1-simulator-public/blob/main/docs/Инструкция_по_загрузке_решения.md).
