# Автодеплой на ВМ (GitHub Actions)

После каждого push в ветку `main` GitHub Actions подключается по SSH к серверу и запускает `scripts/deploy.sh`.

## 1. Подготовка сервера (один раз)

```bash
# Каталог деплоя (можно другой путь)
sudo mkdir -p /opt/quazar
sudo chown "$USER:$USER" /opt/quazar
cd /opt/quazar

git clone https://github.com/Balastov/Quazar_Assistent.git
cd Quazar_Assistent

cp .env.example .env
nano .env   # OPENAI_API_KEY, JWT_SECRET, SECRETS_ENCRYPTION_KEY, PUBLIC_API_URL

# Первый ручной запуск
chmod +x scripts/deploy.sh
./scripts/deploy.sh
docker compose -f infra/docker-compose.yml exec api python seed.py
```

Убедитесь, что пользователь в группе `docker`:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

## 2. SSH-ключ для GitHub Actions

На **своём компьютере** (не на сервере):

```bash
ssh-keygen -t ed25519 -C "github-actions-quazar" -f ~/.ssh/quazar_deploy -N ""
```

Публичный ключ — на **сервер**:

```bash
cat ~/.ssh/quazar_deploy.pub | ssh USER@SERVER 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

Проверка:

```bash
ssh -i ~/.ssh/quazar_deploy USER@SERVER 'echo OK'
```

Приватный ключ — в секреты GitHub (весь файл, включая `BEGIN` / `END`):

```bash
cat ~/.ssh/quazar_deploy
```

## 3. Секреты в GitHub

Репозиторий → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Пример | Описание |
|--------|--------|----------|
| `SSH_HOST` | `203.0.113.10` | IP или домен ВМ |
| `SSH_USER` | `ubuntu` | SSH-пользователь |
| `SSH_PRIVATE_KEY` | содержимое `quazar_deploy` | Приватный ключ |
| `DEPLOY_PATH` | `/opt/quazar/Quazar_Assistent` | Путь к клону репозитория |
| `SSH_PORT` | `22` | Опционально, если не стандартный порт |

## 4. Как это работает

1. Push в `main`
2. Workflow `.github/workflows/deploy.yml`
3. SSH на сервер → `scripts/deploy.sh`:
   - `git fetch` + `git reset --hard origin/main`
   - `docker compose build`
   - `docker compose up -d`
   - `alembic upgrade head`

Ручной запуск: **Actions** → **Deploy to VM** → **Run workflow**.

## 5. Проверка после деплоя

```bash
cd /opt/quazar/Quazar_Assistent
docker compose -f infra/docker-compose.yml ps
docker compose -f infra/docker-compose.yml logs api --tail=50
```

В `.env` на сервере:

```env
PUBLIC_API_URL=http://ВАШ_IP:8000
CORS_ORIGINS=http://ВАШ_IP:3000
```

После изменения `PUBLIC_API_URL` пересоберите web:

```bash
docker compose -f infra/docker-compose.yml up -d --build web
```

## 6. Частые ошибки

| Симптом | Решение |
|---------|---------|
| `Permission denied (publickey)` | Проверьте `SSH_PRIVATE_KEY` и `authorized_keys` на сервере |
| `DEPLOY_PATH`: no such file | Укажите полный путь в секрете `DEPLOY_PATH` |
| `.env not found` | Создайте `.env` на сервере (не в git) |
| `docker: permission denied` | `usermod -aG docker` для SSH-пользователя |

Файл `.env` **никогда не коммитьте** — он остаётся только на сервере.
