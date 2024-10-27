#!/usr/bin/env python
# coding: utf-8

import os
import psutil
import requests
import json
import subprocess
import threading
import inquirer
from typing import Optional, List, Tuple, Type
from datetime import datetime

# Terminal colors
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
CYAN = "\033[96m"

# Base directory for servers
BASE_DIR = os.path.abspath("Minecraft-servers")
os.makedirs(BASE_DIR, exist_ok=True)

def log_message(message: str, color: str = RESET, end: str = '\n') -> None:
    """Print a formatted log message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{RESET}", end=end)

class TunnelService:
    def __init__(self, local_port: int = 25565):
        self.local_port = local_port

    def start_tunnel(self):
        raise NotImplementedError("Each service must implement its own tunnel method")

class NgrokTunnel(TunnelService):
    def __init__(self, local_port: int = 25565, auth_token: str = "2ntG1Do0RPAj8ozh2Bmdt5oc3tw_3L4tzn1UZfXFnFr8Kau2n"):
        super().__init__(local_port)
        self.auth_token = auth_token or os.getenv("NGROK_AUTH_TOKEN")

    def start_tunnel(self):
        if not self.auth_token:
            log_message("⚠️  No Ngrok authentication token provided.", RED)
            return None

        subprocess.run(["ngrok", "config", "add-authtoken", self.auth_token], 
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        
        log_message("🚀 Starting Ngrok tunnel service...", CYAN)

        tunnel_process = subprocess.Popen(
            ["ngrok", "tcp", str(self.local_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        def get_public_url():
            import time
            while True:
                try:
                    response = requests.get("http://localhost:4040/api/tunnels")
                    data = response.json()
                    public_url = data['tunnels'][0]['public_url'].replace('tcp://', '')
                    log_message(f"✨ Server accessible at: {public_url}", GREEN)
                    break
                except Exception:
                    time.sleep(1)

        url_thread = threading.Thread(target=get_public_url)
        url_thread.daemon = True
        url_thread.start()
        return tunnel_process

class PlayitGGTunnel(TunnelService):
    def start_tunnel(self):
        log_message("🚀 Starting Playit.gg tunnel service...", CYAN)
        tunnel_process = subprocess.Popen(
            ["playit", "run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        def read_output():
            for line in tunnel_process.stdout:
                if "agent connected" in line.lower():
                    log_message("✅ Playit.gg agent connected successfully!", GREEN)
                elif "tunnel ready" in line.lower():
                    address = line.strip().split()[-1]
                    log_message(f"✨ Server accessible at: {address}", GREEN)

        tunnel_thread = threading.Thread(target=read_output)
        tunnel_thread.daemon = True
        tunnel_thread.start()
        return tunnel_process

def release_port(port: int = 25565) -> None:
    """Release the specified port if in use."""
    try:
        subprocess.run(f"fuser -k {port}/tcp", 
                      shell=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        log_message(f"🔓 Port {port} released successfully", GREEN, end='\n\n')
    except Exception as e:
        log_message(f"⚠️  Could not release port {port}: {str(e)}", YELLOW)

def get_available_tunnel_services() -> List[Tuple[str, Type[TunnelService]]]:
    """Check which tunnel services are available on the system."""
    available_services = []
    
    if subprocess.run(["which", "ngrok"], stdout=subprocess.PIPE).returncode == 0:
        available_services.append(("Ngrok", NgrokTunnel))
    
    if subprocess.run(["which", "playit"], stdout=subprocess.PIPE).returncode == 0:
        available_services.append(("Playit.gg", PlayitGGTunnel))
    
    return available_services

def select_tunnel_service() -> Optional[TunnelService]:
    """Allow user to select an available tunnel service."""
    available_services = get_available_tunnel_services()
    
    if not available_services:
        log_message("⚠️  No tunnel services found. Please install one of the following:", YELLOW)
        log_message("📦 Ngrok (https://ngrok.com/download)", BLUE)
        log_message("📦 Playit.gg (https://playit.gg)", BLUE)
        return None

    questions = [
        inquirer.List('tunnel_service',
                     message="Select tunnel service",
                     choices=[name for name, _ in available_services])
    ]
    
    answer = inquirer.prompt(questions)
    selected_service = next((service for name, service in available_services 
                           if name == answer['tunnel_service']), None)
    
    return selected_service(25565) if selected_service else None

def get_minecraft_versions() -> List[str]:
    """Obtiene todas las versiones de lanzamiento de Minecraft desde el manifiesto de Mojang y asegura que '1.18.2' esté incluida."""
    try:
        # Endpoint oficial de Mojang para el manifiesto de versiones
        response = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
        if response.status_code == 200:
            versions = response.json().get('versions', [])
            # Filtra solo las versiones de tipo "release" para incluir solo versiones completas
            release_versions = [v["id"] for v in versions if v["type"] == "release"]
            
            # Asegura que '1.18.2' esté en la lista
            if "1.18.2" not in release_versions:
                release_versions.append("1.18.2")
                
            return release_versions
    except Exception as e:
        log_message(f"Error fetching versions: {e}", RED)
    
    # Lista de versiones por defecto si falla la API
    return ["1.20.4", "1.20.3", "1.20.2", "1.19.4", "1.18.2", "1.18.1", "1.18", "1.17.1", "1.17", "1.16.5"]

def download_server(url: str, output_path: str) -> bool:
    """Download server jar with progress indicator."""
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        current_size = 0

        with open(output_path, 'wb') as f:
            for data in response.iter_content(block_size):
                current_size += len(data)
                f.write(data)
                
                if total_size:
                    percentage = int((current_size / total_size) * 100)
                    print(f"\rDownloading: {percentage}%", end='')
            
        print("\n")
        return True
    except Exception as e:
        log_message(f"⚠️  Download failed: {str(e)}", RED)
        return False

def get_paper_download_url(version: str) -> Optional[str]:
    """URL de descarga para PaperMC."""
    response = requests.get(f"https://papermc.io/api/v2/projects/paper/versions/{version}")
    if response.status_code != 200:
        log_message(f"Error al obtener versión PaperMC {version}.", RED)
        return None
    builds = response.json().get('builds', [])
    latest_build = builds[-1] if builds else None
    if not latest_build:
        log_message(f"No se encontraron builds para PaperMC {version}.", RED)
        return None
    return f"https://papermc.io/api/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
    
def get_vanilla_download_url(version: str) -> Optional[str]:
    """URL de descarga para Vanilla."""
    manifest_response = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
    if manifest_response.status_code != 200:
        log_message("Error al obtener el manifiesto de versiones.", RED)
        return None
    version_manifest_url = next((v["url"] for v in manifest_response.json()["versions"] if v["id"] == version), None)
    version_manifest = requests.get(version_manifest_url).json() if version_manifest_url else {}
    return version_manifest.get("downloads", {}).get("server", {}).get("url")

def get_fabric_version(api_url: str) -> Optional[str]:
    """Obtiene la última versión estable de Fabric desde la API."""
    response = requests.get(api_url)
    if response.status_code == 200:
        return next((v["version"] for v in response.json() if v.get("stable")), None)
    log_message(f"Error accediendo a la API: {api_url}.", RED)
    return None

def get_fabric_download_url(version: str) -> Optional[str]:
    """URL de descarga para Fabric."""
    loader_version = get_fabric_version("https://meta.fabricmc.net/v2/versions/loader")
    installer_version = get_fabric_version("https://meta.fabricmc.net/v2/versions/installer")
    return f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_version}/{installer_version}/server/jar" if loader_version and installer_version else None

def get_server_download_url(server_type: str, version: str) -> Optional[str]:
    """Obtiene la URL de descarga según el tipo y versión de servidor."""
    if server_type == 'paper':
        return get_paper_download_url(version)
    elif server_type == 'vanilla':
        return get_vanilla_download_url(version)
    elif server_type == 'fabric':
        return get_fabric_download_url(version)
    return None

def create_server_properties(server_dir: str, server_name: str):
    """Create default server.properties file."""
    properties = {
        "server-name": server_name,
        "gamemode": "survival",
        "difficulty": "normal",
        "max-players": "20",
        "view-distance": "10",
        "spawn-protection": "16",
        "enable-command-block": "false",
        "motd": f"§6Welcome to {server_name}!",
        "online-mode": "false"
    }
    
    with open(os.path.join(server_dir, 'server.properties'), 'w') as f:
        for key, value in properties.items():
            f.write(f"{key}={value}\n")

def create_new_server() -> Optional[str]:
    """Create a new Minecraft server."""
    log_message("🆕 Creating new Minecraft server...", BLUE)
    
    # Solicitar el nombre del servidor
    name = input("Enter server name: ").strip()
    if not name:
        log_message("⚠️  Server name cannot be empty!", RED)
        return None

    # Obtener la lista de versiones y solicitar la selección
    versions = get_minecraft_versions()
    version = inquirer.prompt([
        inquirer.List("version", 
                      message="Select Minecraft version", 
                      choices=versions)
    ])["version"]

    # Solicitar el tipo de servidor
    server_type = inquirer.prompt([
        inquirer.List("type", 
                      message="Select server type", 
                      choices=["paper", "vanilla", "fabric"])
    ])["type"]

    log_message(f"📥 Setting up {server_type} server version {version}...", CYAN)

    # Obtener la URL de descarga según el tipo de servidor y la versión seleccionada
    url = get_server_download_url(server_type, version)
    
    if not url:
        log_message("⚠️  Could not determine server download URL!", RED)
        return None

    # Crear el directorio del servidor ahora que se han obtenido todos los datos
    server_dir = os.path.join(BASE_DIR, name)
    os.makedirs(server_dir, exist_ok=True)

    # Ruta donde se descargará el archivo jar del servidor
    jar_path = os.path.join(server_dir, "server.jar")
    if not download_server(url, jar_path):
        return None

    # Crear archivos de configuración para el servidor
    config = {
        "server_type": server_type,
        "version": version,
        "created_at": datetime.now().isoformat(),
        "last_started": None
    }

    # Guardar el archivo de configuración en formato JSON
    with open(os.path.join(server_dir, "server_config.json"), 'w') as f:
        json.dump(config, f, indent=2)

    # Crear el archivo eula.txt
    with open(os.path.join(server_dir, 'eula.txt'), 'w') as f:
        f.write('eula=true\n')

    # Crear el archivo server.properties
    create_server_properties(server_dir, name)

    log_message(f"✅ Server '{name}' created successfully!", GREEN)
    return name


def run_server(server_name: str) -> None:
    """Run the Minecraft server."""
    server_dir = os.path.join(BASE_DIR, server_name)
    if not os.path.exists(server_dir):
        log_message(f"⚠️  Server directory '{server_name}' not found!", RED)
        return

    os.chdir(server_dir)
    release_port()

    try:
        with open("server_config.json") as f:
            config = json.load(f)
    except Exception as e:
        log_message(f"⚠️  Error reading server configuration: {str(e)}", RED)
        return    
    # Start tunnel service
    tunnel_service = select_tunnel_service()
    tunnel_process = tunnel_service.start_tunnel() if tunnel_service else None
    
    # Detectar memoria del sistema y asignar el 80% de la memoria total
    total_memory = psutil.virtual_memory().total // (1024 ** 3)  # Convertir a GB
    allocated_memory = int(total_memory * 0.8)  # Asignar el 80% de la memoria total
    
    # Start server with optimized Java flags
    java_flags = [
        "-Xms1G", f"-Xmx{allocated_memory}G",  # Memory allocation
        "-XX:+UseG1GC",      # Use G1 Garbage Collector
        "-XX:+ParallelRefProcEnabled",
        "-XX:MaxGCPauseMillis=200",
        "-XX:+UnlockExperimentalVMOptions",
        "-XX:+DisableExplicitGC",
        "-XX:+AlwaysPreTouch",
        "-XX:G1NewSizePercent=30",
        "-XX:G1MaxNewSizePercent=40",
        "-XX:G1HeapRegionSize=8M",
        "-XX:G1ReservePercent=20",
        "-XX:G1HeapWastePercent=5",
        "-XX:G1MixedGCCountTarget=4",
        "-XX:InitiatingHeapOccupancyPercent=15",
        "-XX:G1MixedGCLiveThresholdPercent=90",
        "-XX:G1RSetUpdatingPauseTimePercent=5",
        "-XX:SurvivorRatio=32",
        "-XX:+PerfDisableSharedMem",
        "-XX:MaxTenuringThreshold=1"
    ]

    java_command = ["java"] + java_flags + ["-jar", "server.jar", "nogui"]
    
    log_message("⚙️  Starting Minecraft server with optimized settings...", CYAN)
    server_process = subprocess.Popen(
        java_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    def monitor_server():
        for line in server_process.stdout:
            print(line.strip())
            if "Done (" in line:
                log_message(f"✨ Server '{server_name}' is ready!", GREEN)

    server_thread = threading.Thread(target=monitor_server)
    server_thread.daemon = True
    server_thread.start()

    try:
        server_process.wait()
    except KeyboardInterrupt:
        log_message("\n🛑 Stopping server...", YELLOW)
    finally:
        if tunnel_process:
            tunnel_process.terminate()
            log_message("🔌 Tunnel service stopped", YELLOW)

def main():
    """Main program function."""
    log_message("🎮 Minecraft Server Manager v2.0", CYAN)
    log_message("=" * 50, BLUE)
    
    servers = [d for d in os.listdir(BASE_DIR) 
              if os.path.isdir(os.path.join(BASE_DIR, d))]
    
    if servers:
        choices = servers + ["📦 Create new server"]
        selected = inquirer.prompt([
            inquirer.List("server", 
                         message="Select an option", 
                         choices=choices)
        ])["server"]
        
        if selected == "📦 Create new server":
            selected_server = create_new_server()
        else:
            selected_server = selected
    else:
        log_message("No existing servers found. Creating new server...", YELLOW)
        selected_server = create_new_server()

    if selected_server:
        run_server(selected_server)
    else:
        log_message("⚠️  Failed to start server", RED)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("\n👋 Thanks for using Minecraft Server Manager!", CYAN)
