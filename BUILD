#!/bin/bash

echo "Removing previous container"
yes | rm *.simg

echo "Building docker image..."
if sudo docker build --no-cache --tag=fmriprep-qc .; then
	echo "Converting to singularity..."
	sudo docker run -v /var/run/docker.sock:/var/run/docker.sock -v $(pwd):/output --privileged -t --rm singularityware/docker2singularity --name fmriprep-qc fmriprep-qc

	echo "Deleting none images"
	docker rmi --force $(docker images | grep none | awk '{ print $3; }')

	echo "Transferring image to beluga..."
	rsync -rltv --info=progress2 fmriprep-qc.simg beluga:~/projects/rrg-pbellec/containers
else
    echo "Docker build was not successfull"
fi
