# 7. Troubleshooting

This guide provides solutions to common issues. The first and most important step for any problem is to **check the container logs**. You can do this by running:

```sh
docker-compose logs <service_name>

# Example for checking n8n logs
docker-compose logs n8n

# Follow logs in real-time
docker-compose logs -f n8n
```

---

### General Docker & Networking Issues

**Issue: `Permission Denied` on a mounted directory (e.g., for SearXNG, Neo4j).**

- **Cause:** The Docker container runs with an internal user that doesn't have the necessary read/write permissions for the local directory you've mounted.
- **Solution:** Adjust the permissions on your local machine. For example, for SearXNG:
  ```sh
  chmod -R 755 ./searxng
  ```
  For Neo4j, ensure the user running Docker has ownership or write access to the `./neo4j/data`, `./neo4j/logs`, etc. directories.

**Issue: `Port is already allocated` or `address already in use`.**

- **Cause:** Another service on your host machine is using a port that a container needs.
- **Solution:** 
  1. Identify the conflicting service using `sudo lsof -i -P -n | grep LISTEN` or `netstat -tulpn`.
  2. Stop the conflicting service or change the port mapping in the `docker-compose.override.private.yml` file. For example, to change the n8n port from `5678` to `5679`:
     ```yaml
     # docker-compose.override.private.yml
     services:
       n8n:
         ports:
           - "127.0.0.1:5679:5678"
     ```

**Issue: Containers fail to start after a system reboot.**

- **Cause:** Docker daemon might not have started, or network services are not ready.
- **Solution:** Ensure the Docker service is enabled to start on boot (`sudo systemctl enable docker`). Manually restart the stack with `docker-compose down && docker-compose up -d`.

---

### Ollama & AI Models

**Issue: Ollama container exits or models fail to pull.**

- **Cause:** Insufficient disk space, network issues, or problems with the base Ollama image.
- **Solution:**
  1.  **Check Disk Space:** Run `df -h` to ensure you have enough space for the models.
  2.  **Check Logs:** Run `docker-compose logs ollama-cpu` (or `-gpu`) for specific error messages.
  3.  **Manual Pull:** Try pulling a model manually to isolate the issue:
      ```sh
      docker-compose exec ollama-cpu ollama pull llama3
      ```

**Issue: Poor performance or high CPU usage.**

- **Cause:** The model is too large for your hardware, or the container is not configured with enough resources.
- **Solution:**
  1.  **Use a Smaller Model:** Quantized models (e.g., `q4_0`) are smaller and faster. Check the Ollama library for available tags.
  2.  **Adjust `OLLAMA_` environment variables** in `docker-compose.yml` to optimize performance for your hardware.

---

### Supabase

**Issue: Supabase containers fail to start, especially after changing the Postgres password.**

- **Cause:** Inconsistent state or corrupted data in the database volume.
- **Solution:** This is a destructive action. **Ensure you have a backup first.**
  1.  Stop the stack: `docker-compose down`.
  2.  Remove the database volume directory: `sudo rm -rf ./supabase/docker/volumes/db/data`.
  3.  Restart the stack: `docker-compose up -d`. Supabase will re-initialize the database.

**Issue: `supabase-pooler` is in a restart loop.**

- **Cause:** This is a known issue in some versions of Supabase.
- **Solution:** Refer to the fix described in the [official Supabase GitHub issue](https://github.com/supabase/supabase/issues/30210#issuecomment-2456955578).

**Issue: Services like n8n can't connect to the Supabase database.**

- **Cause:** An invalid character in your `POSTGRES_PASSWORD`. The `@` symbol is a known problematic character.
- **Solution:** Change your `POSTGRES_PASSWORD` in the `.env` file to a password that does not contain special characters like `@`.

---

### n8n

**Issue: Workflows are not saving or credentials are not working.**

- **Cause:** Problems with the `n8n_storage` volume or incorrect `N8N_ENCRYPTION_KEY`.
- **Solution:**
  1.  **Check Logs:** `docker-compose logs n8n` will often show errors related to the database or encryption key.
  2.  **Verify Encryption Key:** Ensure the `N8N_ENCRYPTION_KEY` in your `.env` file is set and has not been changed since your workflows/credentials were first saved.
  3.  **Check Volume Permissions:** Run `docker volume inspect <project_name>-n8n_storage` and check the mount point for any permission issues.

---

### GPU Support

**Issue: Ollama fails to start with the `gpu` profile.**

- **Cause:** NVIDIA drivers are not installed correctly on the host, or the NVIDIA Container Toolkit is missing or misconfigured.
- **Solution:**
  1.  **Verify Host Drivers:** Ensure `nvidia-smi` runs successfully on your host machine.
  2.  **Install NVIDIA Container Toolkit:** Follow the official installation guide for your Linux distribution.
  3.  **Docker Desktop (Windows/macOS):** GPU passthrough on macOS is not supported. On Windows, ensure you are using the WSL 2 backend and that GPU support is enabled in Docker Desktop settings.