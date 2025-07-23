#!/usr/bin/env python3
"""
Verbesserte Container-Management Funktionen für start_services.py
Kombiniert Funktionen aus alter und neuer Version.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import socket # Benötigt für wait_for_service_ready

def run_command(cmd, cwd=None, env=None, check=True, capture_output=False):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, check=check, env=env, capture_output=capture_output, text=True)
    return result

def get_env_vars(env_file=".env"):
    """Reads key-value pairs from an .env file."""
    variables = {}
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove potential quotes
                    value = value.strip().strip("'\"")
                    variables[key.strip()] = value
    except FileNotFoundError:
        print(f"Warning: .env file not found at {env_file}")
    return variables

def get_all_compose_files(profile=None, environment=None):
    """Get all relevant compose files for the current configuration."""
    compose_files = []
    
    # Main compose files
    compose_files.extend(["-f", "docker-compose.yml"])
    
    # Environment-specific overrides
    if environment == "private":
        compose_files.extend(["-f", "docker-compose.override.private.yml"])
    elif environment == "public":
        compose_files.extend(["-f", "docker-compose.override.public.yml"])
    
    # Profile-specific overrides
    if profile == "none":
        compose_files.extend(["-f", "docker-compose.override.none.yml"])
    
    # Supabase compose file
    compose_files.extend(["-f", "supabase/docker/docker-compose.yml"])
    
    # Supabase environment overrides
    if environment == "public":
        if os.path.exists("docker-compose.override.public.supabase.yml"):
            compose_files.extend(["-f", "docker-compose.override.public.supabase.yml"])
    
    return compose_files

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        run_command(["git", "pull"])
        os.chdir("..")

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env") # Annahme: .env ist im Root-Verzeichnis
    print("Copying .env in root to .env in supabase/docker...")
    if os.path.exists(env_example_path):
        shutil.copyfile(env_example_path, env_path)
    else:
        print(f"Warning: Root .env file not found at {env_example_path}. Skipping copy to Supabase.")

def stop_existing_containers(profile=None, environment=None, compose_env=None, remove_volumes=False):
    """Stop and remove existing containers with comprehensive cleanup."""
    print("Stopping and removing existing containers for the unified project 'localai'...")
    
    # Get all compose files
    compose_files = get_all_compose_files(profile, environment)
    
    # Build the docker compose command
    cmd = ["docker", "compose", "-p", "localai"]
    
    # Add profile only if explicitly specified and not 'none'
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    
    # Add all compose files
    cmd.extend(compose_files)
    
    # Add down command with options
    down_options = ["down", "--remove-orphans"]
    
    # Add volume removal if requested
    if remove_volumes:
        down_options.append("--volumes")
        print("⚠️  WARNING: Removing volumes - all data will be lost!")
    
    cmd.extend(down_options)
    
    try:
        run_command(cmd, env=compose_env)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Docker compose down failed with error: {e}")
        print("Attempting fallback cleanup...")
        fallback_cleanup(compose_env)
    
    # Wait for ports to be released
    print("Waiting for ports to be released...")
    time.sleep(5)
    
    # Verify cleanup
    verify_cleanup()

def fallback_cleanup(compose_env=None):
    """Fallback cleanup method if regular compose down fails."""
    print("Performing fallback cleanup...")
    
    try:
        # Stop all containers with the localai project name
        result = run_command([
            "docker", "ps", "-a", 
            "--filter", "label=com.docker.compose.project=localai",
            "--format", "{{.ID}}"
        ], capture_output=True, check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            container_ids = result.stdout.strip().split('\n')
            print(f"Found {len(container_ids)} containers to stop")
            
            # Stop containers
            run_command(["docker", "stop"] + container_ids, check=False)
            
            # Remove containers
            run_command(["docker", "rm"] + container_ids, check=False)
        
        # Clean up networks
        result = run_command([
            "docker", "network", "ls",
            "--filter", "label=com.docker.compose.project=localai",
            "--format", "{{.ID}}"
        ], capture_output=True, check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            network_ids = result.stdout.strip().split('\n')
            for network_id in network_ids:
                run_command(["docker", "network", "rm", network_id], check=False)
                
    except Exception as e:
        print(f"Fallback cleanup encountered error: {e}")

def verify_cleanup():
    """Verify that all containers have been properly stopped."""
    try:
        result = run_command([
            "docker", "ps", "-a",
            "--filter", "label=com.docker.compose.project=localai",
            "--format", "{{.Names}} {{.Status}}"
        ], capture_output=True, check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            print("⚠️  Warning: Some containers are still running:")
            print(result.stdout)
            return False
        else:
            print("✅ All containers successfully stopped")
            return True
            
    except Exception as e:
        print(f"Could not verify cleanup: {e}")
        return False

def wait_for_service_ready(service_name, port, host="localhost", timeout=60):
    """Wait for a service to be ready by checking its port."""
    print(f"Waiting for {service_name} to be ready on {host}:{port}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    print(f"✅ {service_name} is ready!")
                    return True
        except Exception:
            pass
        
        time.sleep(2)
    
    print(f"⚠️  {service_name} did not become ready within {timeout} seconds")
    return False

def start_supabase(environment=None, compose_env=None):
    """Start the Supabase services with proper health checks."""
    print("Starting Supabase services...")
    
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    
    if environment == "public" and os.path.exists("docker-compose.override.public.supabase.yml"):
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    
    cmd.extend(["up", "-d"])
    
    run_command(cmd, env=compose_env)
    
    # Wait for Supabase to be ready
    wait_for_service_ready("Supabase", 8000)

def start_local_ai(profile=None, environment=None, compose_env=None):
    """Start the local AI services with proper dependency handling."""
    print("Starting local AI services...")
    
    cmd = ["docker", "compose", "-p", "localai"]
    
    # Add profile only if explicitly specified and not 'none'
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    
    cmd.extend(["-f", "docker-compose.yml"])
    
    if environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    elif environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    
    # Handle 'none' profile specifically
    if profile == "none":
        cmd.extend(["-f", "docker-compose.override.none.yml"])
    
    cmd.extend(["up", "-d"])
    
    run_command(cmd, env=compose_env)

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")

    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")

    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return

    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")

    print("Generating SearXNG secret key...")

    # Detect the platform and run the appropriate command
    system = platform.system()

    try:
        if system == "Windows":
            print("Detected Windows platform, using PowerShell to generate secret key...")
            # PowerShell command to generate a random key and replace in the settings file
            ps_command = [
                "powershell", "-Command",
                "$randomBytes = New-Object byte[] 32; " +
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); " +
                "$secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ }); " +
                "(Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml"
            ]
            subprocess.run(ps_command, check=True)

        elif system == "Darwin":  # macOS
            print("Detected macOS platform, using sed command with empty string parameter...")
            # macOS sed command requires an empty string for the -i parameter
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", "", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        else:  # Linux and other Unix-like systems
            print("Detected Linux/Unix platform, using standard sed command...")
            # Standard sed command for Linux
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        print("SearXNG secret key generated successfully.")

    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key using the commands:")
        print("  - Linux: sed -i \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - macOS: sed -i '' \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - Windows (PowerShell):")
        print("    $randomBytes = New-Object byte[] 32")
        print("    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)")
        print("    $secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ })")
        print("    (Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml")

def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return

    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, 'r') as file:
            content = file.read()

        # Default to first run
        is_first_run = True

        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')

            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")

                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
                    capture_output=True, text=True, check=False
                )

                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")

        if is_first_run and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            # Temporarily comment out the cap_drop line
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

            print("Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons.")
        elif not is_first_run and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            # Uncomment the cap_drop line
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")

def generate_dashboard_config(environment='private', env_vars=None):
    """Generate a config.js file for the dashboard frontend."""
    print("Generating dashboard configuration...")
    dashboard_dir = "dashboard"
    config_path = os.path.join(dashboard_dir, "config.js")

    if not os.path.exists(dashboard_dir):
        print(f"Warning: Dashboard directory '{dashboard_dir}' not found. Skipping config generation.")
        return

    if env_vars is None:
        env_vars = {}

    auth_enabled = "true" if environment == "public" else "false"

    # Determine Supabase URL based on environment
    if environment == 'public':
        public_hostname = env_vars.get('SUPABASE_HOSTNAME', '')
        if not public_hostname:
            print("Warning: SUPABASE_HOSTNAME not set in .env for public environment. Auth might fail.")
            supabase_url = ""
        else:
            supabase_url = f"https://{public_hostname}"
    else:
        supabase_url = "http://localhost:8000"

    anon_key = env_vars.get('ANON_KEY', '')
    if not anon_key:
        print("Warning: ANON_KEY not set in .env. Dashboard authentication will not work.")

    config_content = f"""// This file is auto-generated by start_services.py. DO NOT EDIT.
window.APP_CONFIG = {{
    authEnabled: {auth_enabled.lower()},
    supabaseUrl: "{supabase_url}",
    supabaseAnonKey: "{anon_key}"
}};
"""

    try:
        with open(config_path, "w") as f:
            f.write(config_content.strip())
        print(f"Dashboard config generated at '{config_path}' with authEnabled: {auth_enabled}")
    except Exception as e:
        print(f"Error generating dashboard config: {e}")

def main():
    """Enhanced main function with volume management options."""
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile to use for Docker Compose (default: cpu)') # Geändert von None auf 'cpu'
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    parser.add_argument('--remove-volumes', action='store_true',
                      help='Remove all volumes (WARNING: This will delete all data!)')
    parser.add_argument('--no-cleanup', action='store_true',
                      help='Skip the cleanup phase (for debugging)')
    
    args = parser.parse_args()

    # Safety check for volume removal
    if args.remove_volumes:
        print("⚠️  WARNING: You have requested to remove all volumes!")
        print("⚠️  This will permanently delete all data including databases, configurations, etc.")
        response = input("Are you absolutely sure? Type 'DELETE_ALL_DATA' to confirm: ")
        if response != 'DELETE_ALL_DATA':
            print("Volume removal cancelled. Proceeding without removing volumes.")
            args.remove_volumes = False

    env_vars = get_env_vars()
    
    # Prepare environment for docker compose commands
    compose_env = os.environ.copy()
    compose_env['DOMAIN'] = env_vars.get('DOMAIN', 'localhost')
    compose_env['IS_PUBLIC_PROFILE'] = 'true' if args.environment == 'public' else 'false'

    # Pre-startup preparations
    clone_supabase_repo()
    prepare_supabase_env()
    generate_dashboard_config(args.environment, env_vars)
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    # Cleanup existing containers if not skipped
    if not args.no_cleanup:
        stop_existing_containers(
            args.profile, 
            args.environment, # Übergabe des environments an stop_existing_containers
            compose_env=compose_env,
            remove_volumes=args.remove_volumes
        )

    # Start services
    start_supabase(args.environment, compose_env=compose_env)
    
    # Wartezeit wurde in start_supabase durch wait_for_service_ready ersetzt, 
    # kann aber bei Bedarf auch hier noch eingefügt werden, falls weitere Services 
    # von Supabase abhängen und etwas mehr Zeit benötigen.
    # print("Waiting for Supabase to initialize...")
    # time.sleep(10) # Kann beibehalten oder entfernt werden, je nach Bedarf

    start_local_ai(args.profile, args.environment, compose_env=compose_env)
    
    print("🎉 All services started successfully!")

if __name__ == "__main__":
    main()