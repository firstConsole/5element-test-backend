.PHONY: help clean-cache up build down

GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

help:
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# ====================== PROJECT ======================

clean-cache: ## Удалить все __pycache__ директории
	find . -type d -name "__pycache__" -exec rm -rf {} +

# ====================== DATABASE ======================

migrate: ## Применить миграции до последней (alembic upgrade head)
	poetry run alembic upgrade head

downgrade: ## Откатить последнюю миграцию (alembic downgrade -1)
	poetry run alembic downgrade -1

revision: ## Сгенерировать миграцию из моделей: make revision m="описание"
	poetry run alembic revision --autogenerate -m "$(m)"
