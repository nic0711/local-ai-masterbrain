# 1. Installation

Before you begin, ensure you have the following software installed:

- [Python](https://www.python.org/downloads/)
- [Git or GitHub Desktop](https://desktop.github.com/)
- [Docker / Docker Desktop](https://www.docker.com/products/docker-desktop)

Then:

```bash
git clone -b stable https://github.com/nic0711/local-ai-masterbrain
cd local-ai-masterbrain
cp .env.example .env
```

Adjust your `.env` file as described in [02_configuration.md](02_configuration.md), then start:

```bash
python start_services.py --profile cpu
```

