#!/bin/bash
# deploy.sh — первоначальная установка job-bot на VPS (Ubuntu 24)
# Запускать от root: bash deploy.sh

set -e

PROJECT_DIR="/opt/job-bot"
REPO="https://github.com/amapemom-rgb/job-bot.git"
SERVICE="job-bot"

echo "==> [1/6] Обновляем систему и ставим зависимости..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

echo "==> [2/6] Клонируем репозиторий в $PROJECT_DIR..."
if [ -d "$PROJECT_DIR" ]; then
    echo "    Директория уже существует — выполняю git pull"
    cd "$PROJECT_DIR" && git pull
else
    git clone "$REPO" "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

echo "==> [3/6] Создаём виртуальное окружение и ставим пакеты..."
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

echo "==> [4/6] Настраиваем .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "  !! Заполни /opt/job-bot/.env перед запуском !!"
    echo "     nano /opt/job-bot/.env"
    echo ""
else
    echo "    .env уже существует, пропускаю"
fi

echo "==> [5/6] Устанавливаем systemd сервис..."
cp deploy/job-bot.service /etc/systemd/system/job-bot.service
systemctl daemon-reload
systemctl enable "$SERVICE"

echo "==> [6/6] Готово!"
echo ""
echo "  Следующие шаги:"
echo "  1. Заполни .env:      nano /opt/job-bot/.env"
echo "  2. Запусти бота:      systemctl start job-bot"
echo "  3. Статус:            systemctl status job-bot"
echo "  4. Логи:              journalctl -u job-bot -f"
echo ""
