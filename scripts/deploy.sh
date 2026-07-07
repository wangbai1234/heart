#!/bin/bash
# Heart/yuoyuo Production Deployment Script
#
# Usage: ./scripts/deploy.sh [command]
#
# Commands:
#   setup     - Initial setup (create .env.prod, generate keys)
#   build     - Build frontend and Docker images
#   start     - Start all services
#   stop      - Stop all services
#   migrate   - Run database migrations
#   logs      - View logs
#   status    - Check service status
#   backup    - Backup database

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env.prod exists
check_env() {
    if [ ! -f .env.prod ]; then
        log_error ".env.prod not found. Run './scripts/deploy.sh setup' first."
        exit 1
    fi
}

# Setup command
cmd_setup() {
    log_info "Setting up production environment..."
    
    if [ -f .env.prod ]; then
        log_warn ".env.prod already exists. Skipping setup."
        return
    fi
    
    # Generate random passwords
    POSTGRES_PASSWORD=$(openssl rand -hex 32)
    REDIS_PASSWORD=$(openssl rand -hex 32)
    OTP_PEPPER=$(openssl rand -hex 32)
    
    # Create .env.prod from template
    cp .env.prod.example .env.prod
    
    # Replace placeholders with generated values
    sed -i.bak "s/<generate-with-openssl-rand-hex-32>/$POSTGRES_PASSWORD/g" .env.prod
    sed -i.bak "s/<generate-with-openssl-rand-hex-32>/$REDIS_PASSWORD/g" .env.prod
    sed -i.bak "s/<generate-random-pepper>/$OTP_PEPPER/g" .env.prod
    rm -f .env.prod.bak
    
    log_info "Generated .env.prod with random passwords"
    log_warn "Please edit .env.prod to add your API keys and JWT keys"
    
    # Generate JWT keys if they don't exist
    if [ ! -f private.pem ] || [ ! -f public.pem ]; then
        log_info "Generating JWT RSA keypair..."
        openssl genpkey -algorithm RSA -out private.pem -pkeyopt rsa_keygen_bits:2048 2>/dev/null
        openssl rsa -pubout -in private.pem -out public.pem 2>/dev/null
        
        # Update .env.prod with PEM contents
        PRIVATE_KEY=$(cat private.pem | tr '\n' '\\' | sed 's/\\/\\n/g')
        PUBLIC_KEY=$(cat public.pem | tr '\n' '\\' | sed 's/\\/\\n/g')
        
        sed -i.bak "s|<paste-private-pem-here>|$PRIVATE_KEY|g" .env.prod
        sed -i.bak "s|<paste-public-pem-here>|$PUBLIC_KEY|g" .env.prod
        rm -f .env.prod.bak
        
        log_info "Generated JWT keys (private.pem, public.pem)"
    fi
    
    log_info "Setup complete! Please review .env.prod and add your API keys."
}

# Build command
cmd_build() {
    log_info "Building frontend..."
    cd web && npm run build && cd ..
    
    log_info "Building Docker images..."
    docker compose -f docker-compose.prod.yml build
}

# Start command
cmd_start() {
    check_env
    log_info "Starting production services..."
    docker compose -f docker-compose.prod.yml up -d
    
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check health
    cmd_status
}

# Stop command
cmd_stop() {
    log_info "Stopping production services..."
    docker compose -f docker-compose.prod.yml down
}

# Migrate command
cmd_migrate() {
    check_env
    log_info "Running database migrations..."
    docker compose -f docker-compose.prod.yml exec api alembic upgrade heads
}

# Logs command
cmd_logs() {
    docker compose -f docker-compose.prod.yml logs -f
}

# Status command
cmd_status() {
    log_info "Service status:"
    docker compose -f docker-compose.prod.yml ps
    
    echo ""
    log_info "Health checks:"
    
    # Check API
    if curl -s -f http://localhost:8000/health/ready > /dev/null 2>&1; then
        log_info "  API: healthy"
    else
        log_warn "  API: unhealthy or not running"
    fi
    
    # Check Caddy
    if curl -s -f http://localhost:80 > /dev/null 2>&1; then
        log_info "  Caddy: healthy"
    else
        log_warn "  Caddy: unhealthy or not running"
    fi
}

# Backup command
cmd_backup() {
    check_env
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    log_info "Backing up database to $BACKUP_FILE..."
    
    docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U heart heart > "$BACKUP_FILE"
    
    log_info "Backup complete: $BACKUP_FILE"
}

# Main command dispatcher
case "${1:-help}" in
    setup)
        cmd_setup
        ;;
    build)
        cmd_build
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    migrate)
        cmd_migrate
        ;;
    logs)
        cmd_logs
        ;;
    status)
        cmd_status
        ;;
    backup)
        cmd_backup
        ;;
    help|*)
        echo "Heart/yuoyuo Production Deployment Script"
        echo ""
        echo "Usage: ./scripts/deploy.sh [command]"
        echo ""
        echo "Commands:"
        echo "  setup     - Initial setup (create .env.prod, generate keys)"
        echo "  build     - Build frontend and Docker images"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  migrate   - Run database migrations"
        echo "  logs      - View logs"
        echo "  status    - Check service status"
        echo "  backup    - Backup database"
        ;;
esac
