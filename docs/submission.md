# T1 · Что и как сдаёт капитан

**До 19.11.2026, 12:00 МСК.** В кабинете на 18.11 отображалось 4 участника из 6 и 0 из 3 публикаций. Условия доступны, но сдача для команды заблокирована. Проверьте [состав команды](https://robohack.mirea.ru/cabinet/team?event=robohack-2-0) и доведите его до 6 засчитанных участников или уточните статус у организаторов.

1. Запустите [проверку T1](../stages/T1/README.md). Для текущей заготовки уточните, принимает ли T1 образ с пустым `supported_tasks`: в ТЗ это не оговорено явно. Не указывайте этапы, которые образ не запускает.
2. Подготовьте **публичную** версию исходников команды. Не меняйте видимость рабочего репозитория без согласования. Можно создать отдельный публичный репозиторий для сдачи и перенести туда проверенные исходники, Dockerfile, конфигурации и инструкцию, не включая закрытую историю, персональные данные и секреты. Зафиксируйте исходники коммитом.
3. Из чистого checkout сдаваемого коммита соберите и проверьте образ на машине с Docker Engine и Buildx. В примере сохранена структура этого репозитория; выполняйте команды из его корня в Bash.

```bash
git status --short
git rev-parse HEAD
docker buildx build --platform linux/amd64 --load -t robohack-participant:t1 stages/T1
python3 stages/T1/verify_t1.py robohack-participant:t1
```

4. Войдите в Harbor с учётной записью организаторов и отправьте тот же проверенный образ. Пароль вводите интерактивно.

```bash
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
read -r -p 'Digest (sha256:...): ' DIGEST
IMAGE_BY_DIGEST="${IMAGE_REPO}@${DIGEST}"
docker pull --platform linux/amd64 "$IMAGE_BY_DIGEST"
python3 stages/T1/verify_t1.py "$IMAGE_BY_DIGEST"
printf 'docker pull --platform linux/amd64 %s\n' "$IMAGE_BY_DIGEST"
```

6. Когда сдача откроется, капитан вставляет в [кабинет](https://robohack.mirea.ru/cabinet) **ссылку на конкретный публичный коммит** вида `https://github.com/owner/repo/commit/<full-sha>` и **полную команду `docker pull`** из предыдущего шага. Ссылка на ветку, тег `latest` и архив вместо этих двух полей не подходят. Убедитесь, что коммит открывается без входа.

[Официальная инструкция по загрузке решения](https://github.com/Urika000/go1-simulator-public/blob/main/docs/Инструкция_по_загрузке_решения.md).
