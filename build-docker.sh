#!/bin/bash

# MinerU Web Docker Build Script
# Version: v2.8.0
# This script builds both frontend and backend Docker images

set -e

# Configuration
VERSION="${VERSION:-v2.8.0}"
REGISTRY="${REGISTRY:-}"  # Set your registry, e.g., "docker.io/yourusername/"

echo "============================================"
echo "  MinerU Web Docker Build Script"
echo "  Version: ${VERSION}"
echo "============================================"

# Build Frontend Image
echo ""
echo ">>> Building Frontend Image..."
echo ""

cd frontend
docker build \
    -t ${REGISTRY}mineru-web-frontend:${VERSION} \
    -t ${REGISTRY}mineru-web-frontend:latest \
    .
cd ..

echo ""
echo ">>> Frontend image built successfully!"
echo "    - ${REGISTRY}mineru-web-frontend:${VERSION}"
echo "    - ${REGISTRY}mineru-web-frontend:latest"

# Build Backend Image
echo ""
echo ">>> Building Backend Image..."
echo ""

cd backend
docker build \
    -t ${REGISTRY}mineru-web-backend:${VERSION} \
    -t ${REGISTRY}mineru-web-backend:latest \
    .
cd ..

echo ""
echo ">>> Backend image built successfully!"
echo "    - ${REGISTRY}mineru-web-backend:${VERSION}"
echo "    - ${REGISTRY}mineru-web-backend:latest"

echo ""
echo "============================================"
echo "  Build Complete!"
echo "============================================"
echo ""
echo "To push images to registry (if REGISTRY is set):"
echo "  docker push ${REGISTRY}mineru-web-frontend:${VERSION}"
echo "  docker push ${REGISTRY}mineru-web-backend:${VERSION}"
echo ""
echo "To run with docker-compose:"
echo "  docker-compose up -d"
echo ""
