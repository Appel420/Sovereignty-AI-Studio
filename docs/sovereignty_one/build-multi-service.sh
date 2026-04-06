echo "🏗 Building all Docker services locally..."

docker build -t sov-backend:local ./backend
docker build -t sov-gateway:local ./gateway
docker build -t sov-frontend:local ./frontend
docker build -t sov-main:local .  # root Dockerfile
