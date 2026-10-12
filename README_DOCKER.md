# Docker Desktop

Es la aplicación gráfica de Docker para Windows, macOS y Linux que permite crear, ejecutar y administrar contenedores, imágenes, volúmenes y aplicaciones multi-contenedor desde una interfaz unificada. Incluye Docker Engine, Docker CLI, Docker Compose y soporte opcional deKubernetes.[[docker](https://www.docker.com/products/docker-desktop/)][[docs.docker](https://docs.docker.com/desktop/)]

## Qué incluye

- **Docker Engine**: el motor que construye y ejecuta contenedores.
- **Docker CLI**: comandos como `docker build`, `docker run` y `docker ps`.
- **Docker Compose**: orquestación de aplicaciones con varios servicios mediante `docker-compose.yml`.
- **Docker Build**: empaquetado de aplicaciones en imágenes.
- **Kubernetes integrado**: opcional, para probar orquestación localmente.
- **GUI**: gestión visual de contenedores, imágenes, volúmenes y logs.[[docker](https://www.docker.com/products/docker-desktop/)][[docs.docker](https://docs.docker.com/desktop/)]

## Instalación en Windows

Para la mayoría de los casos, conviene instalarlo **por usuario** con backend **WSL 2**, que es la opción recomendada y no requiere privilegios de administrador. Docker Desktop requiere WSL 2.1.5 o posterior.[[docs.docker](https://docs.docker.com/desktop/setup/install/windows-install/)]

1. Descargá Docker Desktop desde el sitio oficial o Microsoft Store.[[docs.docker](https://docs.docker.com/desktop/setup/install/windows-install/)][[apps.microsoft](https://apps.microsoft.com/detail/xp8cbj40xlbwkx?hl=es-ES&gl=ES)]
2. Ejecutá `Docker Desktop Installer.exe`.
3. Elegí **Per-user** como modo de instalación.
4. Seleccioná **Use WSL 2 instead of Hyper-V**.
5. Finalizá el asistente y abrí Docker Desktop desde el menú Inicio.[[docs.docker](https://docs.docker.com/desktop/setup/install/windows-install/)]


Verificación rápida en PowerShell:

```
docker --version
docker run hello-world
```

## Uso básico

```
# Descargar y ejecutar una imagen
docker run -d -p 8080:80 nginx

# Ver contenedores activos
docker ps

# Ver logs
docker logs <container_id>

# Detener y eliminar
docker stop <container_id>
docker rm <container_id>
```

## Alternativa actual en Windows

Microsoft ahora ofrece **WSL Containers** como alternativa integrada para ejecutar contenedores Linux en Windows 11 mediante el comando `wslc`, con sintaxis similar a Docker. Sin embargo, Docker Desktop sigue siendo más completo para flujos de desarrollo: su ecosistema es más maduro y WSL Containers todavía no soporta Docker Compose de formanativa.[[hardwarepremium](https://www.hardwarepremium.com/noticias/67461/wsl-docker-contenedores-wslc-windows/)][[diariobitcoin](https://www.diariobitcoin.com/tecnologia/microsoft-integra-contenedores-linux-en-windows-11-y-reduce-la-dependencia-de-docker-desktop/)][[hwlibre](https://www.hwlibre.com/microsoft-integra-contenedores-linux-en-windows-11-con-wsl-containers/)]

Para desarrollo local con microservicios, APIs, bases de datos y `docker-compose`, **Docker Desktop sigue siendo la opción máspráctica**.[[docker](https://www.docker.com/products/docker-desktop/)][[docs.docker](https://docs.docker.com/desktop/)]

 
