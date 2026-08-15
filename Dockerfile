# Network-isolated sandbox for running the PURE core library + evals.
#
#   docker build -t slackmd-sandbox .
#   docker run --rm --network none slackmd-sandbox
#
# --network none proves the core performs zero network I/O. The macOS clipboard
# extra and the Slack extra are deliberately NOT installed here, so nothing in this
# image can read your pasteboard or post to Slack. This is where code runs "freely".
FROM python:3.13-slim

RUN pip install --no-cache-dir uv
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY evals ./evals

# Install ONLY the pure core (no macos/slack extras) plus the test runner.
RUN uv pip install --system -e . pytest

# Non-root for good measure.
RUN useradd -m runner
USER runner

CMD ["python", "-m", "pytest", "-p", "no:cacheprovider"]
