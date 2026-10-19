# Создать базу
python -m responseflow_local.cli init-db

# Импортировать сообщения
python -m responseflow_local.cli import-messages data/messages.jsonl

# Запустить анализ
python -m responseflow_local.cli analyze \
  --workspace workspace-1 \
  --analysis-time 2026-10-17T12:00:00+03:00

# Посмотреть открытые карточки
python -m responseflow_local.cli list-findings \
  --workspace workspace-1 \
  --status open

# Принять карточку в работу
python -m responseflow_local.cli acknowledge \
  --workspace workspace-1 \
  00000000-0000-0000-0000-000000000001 \
  --author "Иван" \
  --version 1

# Сформировать сводный отчёт
python -m responseflow_local.cli report --workspace workspace-1