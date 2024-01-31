docker stop zonnetijden
docker rm -f zonnetijden
docker run --detach --name zonnetijden --publish 8083:8083 --rm zonnetijden
