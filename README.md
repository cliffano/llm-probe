# LLM-Probe

Probe LLMs via a [prompt](prompt.txt) containing queries for the models' runtime characteristics. The models used are provided by OpenRouter.

## Setup

Create an [OpenRouter API key](https://openrouter.ai/docs/api_reference/authentication).

Install dependencies:

```shell
make deps
```

## Usage

Run the probe and generate report, with OpenRouter API key passed as environment variable:

```shell
OPENROUTER_API_KEY="..." make build
```

Each configured model is probed individually via `promptfoo eval`.
Promptfoo's raw result for each provider, including errors and token
metadata, is saved to `stage/<model>.json`; the successful response body is
exported to `data/<model>.json`.

OpenRouter changes its free catalog over time. Update the explicit `providers`
list in `config/promptfoo.yaml` accordingly .

## Colophon

* [Report](https://cliffano.github.io/llm-probe/report.html)