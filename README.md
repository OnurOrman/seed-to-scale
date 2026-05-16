# seed-to-scale
The public repository for the CS 414/514 (Network Science) course project at Sabancı University.

## How to run the project?
```bash
uv run main.py <vc-name> <vc-linkedin-url> [--overwrite] [--collect]
```

- For 212: ```212 https://www.linkedin.com/company/212vc```

## How to run different modules of the project independently?

```bash
uv run -m collect.vc_212 [--overwrite]
```

```bash
uv run -m collect.linkedin <vc-name> <vc-linkedin-url> [--overwrite]
```

## How to set up the project workflow?
```bash
uv venv

uv sync

uv run playwright install
```