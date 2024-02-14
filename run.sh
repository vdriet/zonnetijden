docker stop zonnetijden
docker rm -f zonnetijden
docker run --detach --restart always --name zonnetijden --publish 8083:8083 zonnetijden
