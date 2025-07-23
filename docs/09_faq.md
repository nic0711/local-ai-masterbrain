# 9. FAQ

### Q: How do I add a new AI model to Ollama?

**A:** You can pull new models directly from the command line while the stack is running.

1.  First, find the model you want in the [Ollama Library](https://ollama.com/library).
2.  Execute the `pull` command inside the running Ollama container. The container name depends on the profile you used to start the services.

    ```sh
    # If you started with the cpu or gpu profile
    docker-compose exec ollama-cpu ollama pull <model_name>:<tag>

    # Example
    docker-compose exec ollama-cpu ollama pull llama3:8b-instruct-q4_K_M
    ```
    The model will be downloaded to the `ollama_storage` volume and will be available in Open WebUI and other connected services immediately.

---

### Q: What are the minimum system requirements?

**A:** This depends heavily on the models you intend to run.
-   **CPU-only:** A modern multi-core CPU (e.g., 4+ cores), 16GB+ RAM, and a fast SSD are recommended. At least 8GB of RAM is required for basic 7B models.
-   **GPU:** For good performance with 7B models, a dedicated NVIDIA GPU with at least 8GB of VRAM is recommended (e.g., RTX 3060 or better). For larger models, more VRAM is necessary.
-   **Disk Space:** At least 50GB of free space is recommended to accommodate the OS, Docker, and several AI models.

---

### Q: How do I expose the services to my local network (not just `localhost`)?

**A:** By default, services are mapped to `127.0.0.1` for security. To expose them, you need to edit `docker-compose.override.private.yml`.

-   **Change this:**
    ```yaml
    # Example for n8n
    ports:
      - "127.0.0.1:5678:5678"
    ```
-   **To this (to allow access from any IP on your network):**
    ```yaml
    ports:
      - "0.0.0.0:5678:5678"
    # Or just this, which defaults to 0.0.0.0
    # ports:
    #   - "5678:5678"
    ```
    You will need to do this for each service you want to expose. Restart the stack for changes to take effect by running the `start_services.py` script again with your chosen profile.

---

### Q: Can I use this stack with other AI providers like OpenAI or Anthropic?

**A:** Yes. The services are not exclusively tied to Ollama.
-   **n8n:** The n8n "LLM" nodes support various providers. You can configure them directly in the workflow editor by adding your API keys as credentials.
-   **Flowise:** Flowise also has built-in nodes for OpenAI, Anthropic, and many other model providers.
-   **Open WebUI:** While it's a great client for Ollama, it can also be configured to connect to any OpenAI-compatible API endpoint.

---

### Q: How do I update the stack to the latest version?

**A:** Updating involves pulling the latest changes from the Git repository and restarting the stack with the `start_services.py` script.

```sh
# 1. Stop all running services
docker-compose down

# 2. Pull the latest changes from the main branch
git pull origin main

# 3. Run the start script again with your profile.
# The script handles pulling the latest Docker images and starting the services.
python start_services.py --profile <your_profile>

# Example for CPU profile
python start_services.py --profile cpu
```

---

### Q: Is it possible to disable services I don't need?

**A:** Yes. The easiest way is to comment out the service definition in the main `docker-compose.yml` file.

For example, if you don't need Neo4j, you can open `docker-compose.yml` and comment out the service block:

```yaml
# docker-compose.yml
services:
  # ... other services

  # neo4j:
  #   image: neo4j:latest
  #   volumes:
  #       - ./neo4j/logs:/logs
  # ... etc.
```
After saving the file, run `python start_services.py --profile <your_profile>`. The script will apply the changes, and the disabled service will not be started.

---

### Q: Can I run Ollama outside of Docker?

**A:** Yes. This is the recommended approach for macOS users who want GPU support.

1.  Install Ollama directly on your host machine by following the official instructions.
2.  Run a model to ensure it's working, e.g., `ollama run llama3`.
3.  Start the stack using the `none` profile. This special profile tells the stack *not* to start its own Ollama container and to look for it on the host machine instead.
    ```sh
    python start_services.py --profile none
    ```
4.  The `docker-compose.override.none.yml` file automatically configures n8n and other services to connect to Ollama on your host at the special address `host.docker.internal:11434`.

---

### Q: Does this work on Apple Silicon (M1/M2/M3)?

**A:** Yes, the stack runs well on Apple Silicon. However, Docker on macOS does not support GPU passthrough, so you cannot use the `gpu-nvidia` profile.

For the best performance, you should run Ollama natively on your Mac to get GPU acceleration, and then start the stack using the `none` profile as described in the previous question.