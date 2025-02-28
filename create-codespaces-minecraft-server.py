#!/usr/bin/env python
# coding: utf-8

# Paquetes necesarios del sistema
import subprocess
import sys
import os
import psutil
import requests
import json
import threading
from typing import Optional, List, Tuple, Type
from datetime import datetime
import pty
import time

# Variables globales
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
CYAN = "\033[96m"
GRAY = "\033[90m"

BASE_DIR = os.path.abspath("Minecraft-servers")
os.makedirs(BASE_DIR, exist_ok=True)

# Actualiza el sistema y Python
subprocess.run(["sudo", "apt", "update", "-y"], check=True)
subprocess.run(["sudo", "apt", "upgrade", "-y"], check=True)

import threading
import time
import subprocess

def clean_ram_periodically():
    first_run = True
    
    while True:
        try:
            subprocess.run(["sudo", "sync"], capture_output=True)
            subprocess.run(["sudo", "sysctl", "-w", "vm.drop_caches=3"], capture_output=True)

            if not first_run:
                print("🧹 Memoria caché limpiada correctamente.")

            first_run = False
        except Exception as e:
            print(f"⚠️ Error al limpiar caché: {e}")
        
        time.sleep(60)

# Funciones globales
def get_lima_time(location: str = "America/Lima"):
    lima_timezone = pytz.timezone(location)
    lima_time = datetime.now(lima_timezone)
    return lima_time.strftime("%H:%M:%S")

def log_message(message: str, color: str = RESET, end: str = '\n') -> None:
    current_time = get_lima_time()
    print(f"{color}[{current_time}] {message}{RESET}", end=end)

def log_input(message: str, color: str = RESET) -> str:
    current_time = get_lima_time()
    return input(f"{color}[{current_time}] {message}{RESET}")

# Instalar paquetes necesarios de python
required_packages = ["python-dotenv", "pytz", "inquirer", "pyngrok"]
print()
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"🔄 Paquete '{package}' instalado con éxito.")

# Importar paquetes necesarios instalados
import inquirer
import pytz
from pyngrok import ngrok, conf
from dotenv import load_dotenv

# Cargar variables de entorno del archivo '.env'
load_dotenv()

# application.properties
def create_server_properties(server_dir: str, server_name: str):
    properties = {
        "server-name": server_name,
        "gamemode": "survival",
        "difficulty": "hard",
        "max-players": "20",
        "view-distance": "12",
        "spawn-protection": "0",
        "enable-command-block": "true",
        "motd": f"Bienvenido a {server_name}!",
        "online-mode": "false"
    }
    
    with open(os.path.join(server_dir, 'server.properties'), 'w') as f:
        for key, value in properties.items():
            f.write(f"{key}={value}\n")

def release_port(port: int = 25565) -> None:
    try:
        subprocess.run(f"fuser -k {port}/tcp", 
                      shell=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        log_message(f"🔓 Puerto {port} liberado exitosamente", GRAY, end='\n')
    except Exception as e:
        log_message(f"⚠️  No se pudo liberar el puerto {port}: {str(e)}", YELLOW)

class NgrokTunnel():
    def __init__(self, port: int = 25565):
        self.port = port

    def start_tunnel(self):
        auth_token = os.getenv("NGROK_AUTH_TOKEN")
        region = os.getenv("NGROK_REGION")

        if not auth_token or not region:
            log_message("⚠️  No se encontró un token de autenticación o una región.", RED)
            return None
    
        log_message("🚀 Iniciando tunel con Ngrok...", CYAN)

        ngrok.set_auth_token(auth_token)
        conf.get_default().region = region

        url = ngrok.connect(self.port, "tcp")
        
        print()
        log_message("✅ Agente Ngrok conectado exitosamente!", GRAY)
        
        # Procesa la URL en pasos separados
        url_str = str(url)
        formatted_url = url_str.split('"')[1::2][0].replace('tcp://', '')
        log_message(f"✨ IP del servidor: {formatted_url}", GREEN)

class PlayitGGTunnel():
    def __init__(self, port: int = 25565):
        self.port = port

    def start_tunnel(self):
        # Libera el puerto antes de usarlo
        release_port(self.port)

        log_message("🚀 Iniciando tunel con Playit.gg...", CYAN)
        tunnel_process = subprocess.Popen(
            ["playit", "run"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        print()
        log_message("✅ Agente Playit.gg conectado exitosamente!", GRAY)
        log_message(f"✨ Inicia un tunel manualmente escribiendo en la terminal 'playit' CUANDO TERMINE DE ABRIR EL SERVIDOR", GREEN)

        def read_output():
            for line in tunnel_process.stdout:
                if "agent connected" in line.lower():
                    log_message("✅ Agente Playit.gg conectado exitosamente!", GREEN)
                elif "tunnel ready" in line.lower():
                    address = line.strip().split()[-1]
                    log_message(f"✨ IP del servidor: {address}", GREEN)

        tunnel_thread = threading.Thread(target=read_output)
        tunnel_thread.daemon = True
        tunnel_thread.start()
        return tunnel_process

def install_playit():
    subprocess.run(["curl", "-SsL", "https://playit-cloud.github.io/ppa/key.gpg", "-o", "key.gpg"], check=True)
    
    subprocess.run(["sudo", "apt-key", "add", "key.gpg"], check=True)
    
    subprocess.run(["sudo", "curl", "-SsL", "-o", "/etc/apt/sources.list.d/playit-cloud.list", "https://playit-cloud.github.io/ppa/playit-cloud.list"], check=True)

    result = subprocess.run(["sudo", "apt", "install", "-y", "playit"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if result.returncode == 0:
        log_message("🔄 Playit instalado correctamente...", BLUE)
    else:
        log_message("🔄 Error instalando Playit...", RED)

def get_available_tunnel_services():
    available_services = []

    install_playit()
    
    if subprocess.run(["which", "ngrok"], stdout=subprocess.PIPE).returncode == 0:
        available_services.append(("Ngrok", NgrokTunnel))
    
    if subprocess.run(["which", "playit"], stdout=subprocess.PIPE).returncode == 0:
        available_services.append(("Playit.gg", PlayitGGTunnel))
    
    return available_services

def select_tunnel_service():
    available_services = get_available_tunnel_services()
    
    if not available_services:
        log_message("⚠️ No se encontraron túneles de conexión integrados, integra uno primero:", YELLOW)
        log_message("📦 Ngrok (https://ngrok.com)", BLUE)
        log_message("📦 Playit.gg (https://playit.gg)", BLUE)
        return None

    questions = [
        inquirer.List('tunnel_service',
                     message="Selecciona un túnel de conexión",
                     choices=[name for name, _ in available_services])
    ]
    
    answer = inquirer.prompt(questions)
    selected_service = next((service for name, service in available_services 
                           if name == answer['tunnel_service']), None)
    
    return selected_service(25565) if selected_service else None

# Obtiene las versiones de Minecraft desde el manifiesto de versiones oficial de Mojang
def get_minecraft_versions() -> List[str]:
    try:
        response = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
        if response.status_code == 200:
            versions = response.json().get('versions', [])
            
            # Filtra solo las versiones "release"
            release_versions = [v["id"] for v in versions if v["type"] == "release"]
            
            return release_versions
    except Exception as e:
        log_message(f"Error al obtener las versiones: {e}", RED)
    
    # Versiones por defecto si falla la API
    return ["1.20.4", "1.20.3", "1.20.2", "1.19.4", "1.18.2", "1.18.1", "1.18", "1.17.1", "1.17", "1.16.5", "1.12.2", "1.8.9"]

def get_snapshot_versions() -> List[str]:
    return None

def get_mohist_versions() -> List[str]:
    try:
        response = requests.get("https://mohistmc.com/api/v2/projects/mohist")
        if response.status_code == 200:
            data = response.json()
            data_list = data.get("versions", [])
            data_list.reverse()
            return data_list
        else:
            raise Exception()
    except Exception as e:
        log_message(f"⚠️ Error al obtener la lista de versiones: {str(e)}", RED)

# Descarga el .jar con un indicador de progreso
def download_server(url: str, output_path: str) -> bool:
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
                    log_message(f"Descargando: {percentage}%", end='\r')
            
        return True
    except Exception as e:
        log_message(f"⚠️ Descarga fallida: {str(e)}", RED)
        return False

# Tipos de servidores
def get_vanilla_download_url(version: str) -> Optional[str]:
    manifest_response = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
    if manifest_response.status_code != 200:
        log_message("Error al obtener el manifiesto de versiones.", RED)
        return None
    version_manifest_url = next((v["url"] for v in manifest_response.json()["versions"] if v["id"] == version), None)
    version_manifest = requests.get(version_manifest_url).json() if version_manifest_url else {}
    return version_manifest.get("downloads", {}).get("server", {}).get("url")
    
# def get_snapshot_download_url(version: str) -> Optional[str]:
#     return None

def get_forge_download_url(version: str) -> Optional[str]:
    print(version)
    forge_base_url = "https://maven.minecraftforge.net/net/minecraftforge/forge"
    metadata_url = f"{forge_base_url}/maven-metadata.xml"

    response = requests.get(metadata_url)
    if response.status_code == 200:
        metadata = response.text
        versions = metadata.split('<version>')
        versions = [v.split('</version>')[0] for v in versions[1:]]
        matching_versions = [v for v in versions if v.startswith(version)]

        if matching_versions:
            def version_key(v):
                main_version, sub_version = v.split('-')[0], v.split('-')[1]
                return [int(x) for x in main_version.split('.')] + [int(x) for x in sub_version.split('.')]

            latest_matching_version = max(matching_versions, key=version_key)
            
            return f"{forge_base_url}/{latest_matching_version}/forge-{latest_matching_version}-installer.jar"

def get_paper_download_url(version: str) -> Optional[str]:
    """URL de descarga para PaperMC."""
    response = requests.get(f"https://papermc.io/api/v2/projects/paper/versions/{version}")
    if response.status_code != 200:
        log_message(f"Error al obtener versión PaperMC {version}.", RED)
        return None
    builds = response.json().get('builds', [])
    latest_build = builds[-1] if builds else None

    if not latest_build:
        log_message(f"Error obteniendo el link de descarga de PaperMC.", RED)
        return None
    
    url = f"https://papermc.io/api/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
    return url

def get_fabric_version(api_url: str) -> Optional[str]:
    response = requests.get(api_url)
    if response.status_code == 200:
        url = next((v["version"] for v in response.json() if v.get("stable")), None)
        return url
    return None

def get_fabric_download_url(version: str) -> Optional[str]:
    """URL de descarga para Fabric."""
    loader_version = get_fabric_version("https://meta.fabricmc.net/v2/versions/loader")
    installer_version = get_fabric_version("https://meta.fabricmc.net/v2/versions/installer")

    if not loader_version or not installer_version:
        log_message(f"Error obteniendo el link de descarga de Fabric.", RED)
        return None

    url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_version}/{installer_version}/server/jar"
    return url

def get_mohist_download_url(version: str) -> Optional[str]:
    mohist_builds_url = f"https://mohistmc.com/api/v2/projects/mohist/{version}/builds"
    response = requests.get(mohist_builds_url)

    if response.status_code == 200:
        builds = response.json()["builds"]
        url = builds[-1]["url"]
        return url
    
    log_message(f"Error obteniendo el link de descarga de Mohist.", RED)
    return None
    
def get_purpur_download_url(version: str) -> Optional[str]:
    purpur_api = f"https://api.purpurmc.org/v2/purpur/{version}"
    response = requests.get(purpur_api).json()
    if response.status_code == 200:
        latest_build = response["builds"]["latest"]
        url = f"https://api.purpurmc.org/v2/purpur/{version}/{latest_build}/download"
        return url
    
    log_message(f"Error obteniendo el link de descarga de Purpur.", RED)
    return None

def get_server_download_url(server_type: str, version: str) -> Optional[str]:
    if server_type.lower().startswith('vanilla'):
        return get_vanilla_download_url(version)
    # elif server_type.lower().startswith('snapshot'):
    #     return get_snapshot_download_url(version)
    elif server_type.lower().startswith('forge'):
        return get_forge_download_url(version)
    elif server_type.lower().startswith('paper'):
        return get_paper_download_url(version)
    elif server_type.lower().startswith('fabric'):
        return get_fabric_download_url(version)
    elif server_type.lower().startswith('mohist'):
        return get_mohist_download_url(version)
    elif server_type.lower().startswith('purpur'):
        return get_purpur_download_url(version)
    return None

def get_versions_by_type(server_type: str):
    if server_type.lower().startswith('snapshot'):
        return get_snapshot_versions()
    elif server_type.lower().startswith('mohist'):
        return get_mohist_versions()
    else:
        return get_minecraft_versions()

def create_new_server() -> Optional[str]:
    log_message("🆕 Creando un nuevo servidor...", BLUE)
    
    print()
    server_name = log_input("Ingresa un nombre para el servidor: ").strip()
    if not server_name:
        log_message("⚠️ El nombre del servidor es obligatorio!", RED)
        return None

    print()
    
    # Solicita el tipo de servidor
    server_type = inquirer.prompt([
        inquirer.List("type",
                    message="Selecciona un tipo de servidor", 
                    choices=[
                        "Vanilla",
                        # "Snapshot",
                        "Forge (mods)",
                        "Fabric (mods)",
                        "Mohist (mods y plugins)",
                        "Purpur (mods y plugins)",
                        "Paper (plugins)"
                    ])
    ])["type"]

    # Obtener la lista de versiones y solicitar la selección
    versions = get_versions_by_type(server_type)
    version = inquirer.prompt([
        inquirer.List("version", 
                      message="Selecciona una version", 
                      choices=versions)
    ])["version"]

    server_type_name = server_type.split('(')[0].strip() if len(server_type.split('(')) > 0 else None
    log_message(f"📥 Descargando un servidor {server_type_name} en la versión {version}...", CYAN)

    # Busca la version en el tipo de servidor seleccionado
    url = get_server_download_url(server_type, version)

    if not url:
        log_message("⚠️ No se encontró la URL de descarga.", RED)
        return None

    # Crear el directorio del servidor
    server_dir = os.path.join(BASE_DIR, server_name)
    os.makedirs(server_dir, exist_ok=True)

    # Descarga y guarda el .jar
    jar_path = os.path.join(server_dir, "server.jar")
    if not download_server(url, jar_path):
        return None

    # Crear archivos de configuración para el servidor
    config = {
        "server_type": server_type,
        "version": version,
        "created_at": get_lima_time().format(),
        "last_started": None
    }

    # # Guardar el archivo de configuración en formato JSON
    # with open(os.path.join(server_dir, "server_config.json"), 'w') as f:
        # json.dump(config, f, indent=2)

    # Crear el archivo eula.txt
    with open(os.path.join(server_dir, 'eula.txt'), 'w') as f:
        f.write('eula=true\n')

    # Crear el archivo server.properties
    create_server_properties(server_dir, server_name)

    log_message(f"✅ Servidor '{server_name}' descargado correctamente!\n", GREEN)
    return server_name

def start_server(ram, tunnel_process):
    master, slave = pty.openpty()
    java_command = ["java", f"-Xms{ram}G", f"-Xmx{ram}G", "-jar", "server.jar", "nogui"]
    
    java_flags = [
        f"-Xms{ram}G", f"-Xmx{ram}G",
        "-XX:+UseG1GC",
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

    # Ejecuta el proceso en el pty para mantener los colores
    server_process = subprocess.Popen(
        java_command,
        stdout=slave,
        stderr=slave,
        bufsize=1,
        universal_newlines=True
    )
    
    os.close(slave)

    def monitor_server():
        while True:
            try:
                # Lee y muestra la salida del proceso con colores originales
                output = os.read(master, 1024).decode()
                if output:
                    print(output, end="", flush=True)
                else:
                    break
            except OSError:
                break

    server_thread = threading.Thread(target=monitor_server)
    server_thread.daemon = True
    server_thread.start()

    try:
        server_process.wait()
    except KeyboardInterrupt:
        log_message("\n🛑 Deteniendo servidor...", YELLOW)
    finally:
        os.close(master)
        if tunnel_process:
            tunnel_process.terminate()
            log_message("🔌 Túnel de servicio detenido", YELLOW)


def install_and_run_server(server_name: str) -> None:
    server_dir = os.path.join(BASE_DIR, server_name)

    if not os.path.exists(server_dir):
        log_message(f"⚠️ Directorio del servidor '{server_name}' no encontrado!", RED)
        return

    # Entrar al directorio creado
    os.chdir(server_dir)

    # Start tunnel service
    tunnel_service = select_tunnel_service()
    tunnel_process = tunnel_service.start_tunnel() if tunnel_service else None

    # Iniciar el proceso en un hilo separado para limpiar la RAM
    cache_cleaner_thread = threading.Thread(target=clean_ram_periodically, daemon=True)
    cache_cleaner_thread.start()
    
    # Asignar el 80% de la memoria total si la variable ram es None o no es un entero
    print()
    log_message("Si no se ingresa la cantidad de memoria RAM, se asignará el 80% de la memoria total", GRAY)
    ram = log_input("🔍 Ingresa la cantidad de memoria RAM (en GB) para el servidor: ")
    
    # Validar si la entrada es un número, si no, asignar 80% de la RAM
    if not ram.isdigit():
        total_memory_vm = psutil.virtual_memory().total // (1024 ** 3)
        ram = int(total_memory_vm * 0.8)
    else:
        ram = int(ram)

    start_server(ram, tunnel_process)

def main():
    print()
    log_message("=" * 50, BLUE)
    log_message("🎮 Minecraft Server Manager v2.0", BLUE)
    log_message("=" * 50, BLUE)
    print()
    
    servers = [d for d in os.listdir(BASE_DIR) 
              if os.path.isdir(os.path.join(BASE_DIR, d))]
    
    if servers:
        choices = servers + ["📦 Crear un nuevo servidor"]
        selected = inquirer.prompt([
            inquirer.List("server", 
                         message="Selecciona un servidor existente", 
                         choices=choices)
        ])["server"]
        
        if selected == "📦 Crear un nuevo servidor":
            selected_server = create_new_server()
        else:
            selected_server = selected
    else:
        log_message("No se encontraron servidores en el directorio actual", GRAY)
        selected_server = create_new_server()

    if selected_server:
        install_and_run_server(selected_server)
    else:
        log_message("⚠️ Error al iniciar el servidor", RED)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        log_message("👋 C:", CYAN)
