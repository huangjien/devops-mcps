#!/bin/bash

# Extract version from pyproject.toml
VERSION=$(grep -m 1 'version =' pyproject.toml | cut -d '"' -f 2)

# Build Docker image with version and latest tags
docker build -t huangjien/devops-mcps:$VERSION -t huangjien/devops-mcps:latest .

echo "Successfully built huangjien/devops-mcps:$VERSION and huangjien/devops-mcps:latest"