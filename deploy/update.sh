#!/bin/bash
# update.sh — обновление job-bot из GitHub без переустановки
# Запускать от root: bash /opt/job-bot/deploy/update.sh

set -e

PROJECT_DIR="/opt/job-bot"

echo "==> Останавливаем бота..."
systemctl stop job-bot || true

echo "==> Получаем обновления из GitHub..."
cd "$PROJECT_DIR"
git pull

echo "==> Обновляем пакеты..."
venv/bin/pip install -r requirements.txt -q

echo "==> Запускаем бота..."
systemctl start job-bot

echo "==> Готово! Статус:"
systemctl status job-bot --no-pager
