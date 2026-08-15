.PHONY: setup test eval lint sandbox sandbox-build clean

setup:            ## Create the isolated venv and install deps incl. macOS clipboard extra
	uv sync --python 3.13 --extra macos

test:             ## Run unit tests in the local venv
	uv run pytest tests

eval:             ## Run the eval corpus (fidelity gate)
	uv run pytest evals

lint:             ## Lint
	uv run ruff check src tests

sandbox-build:    ## Build the network-isolated Docker sandbox image
	docker build -t slackmd-sandbox .

sandbox: sandbox-build  ## Run tests inside the sandbox with NO network or cloud access
	docker run --rm --network none slackmd-sandbox

clean:
	rm -rf .venv .pytest_cache .ruff_cache dist build *.egg-info
