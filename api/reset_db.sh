#!/bin/bash

# Yes Human Agent Stack Database Reset Script
# Handles both PostgreSQL and SQLite fallback

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default environment variables
POSTGRES_DB=${POSTGRES_DB:-yeshuman}
POSTGRES_USER=${POSTGRES_USER:-yeshuman}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
USE_POSTGRES=${USE_POSTGRES:-true}

echo -e "${BLUE}🚀 Yes Human Agent Stack Database Reset${NC}"
echo "==========================================="

echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
if command -v psql &> /dev/null; then
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d postgres -c "SELECT 1;" &> /dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PostgreSQL available${NC}"
    else
        echo -e "${RED}✗ PostgreSQL connection failed${NC}"
        echo -e "${RED}Please ensure PostgreSQL is running and credentials are correct${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ PostgreSQL client not found${NC}"
    echo -e "${RED}Please install PostgreSQL client tools${NC}"
    exit 1
fi

echo -e "${YELLOW}Using PostgreSQL database: $POSTGRES_DB${NC}"

# Terminate existing connections
echo -e "${YELLOW}Terminating existing database connections...${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname IN ('$POSTGRES_DB', 'test_$POSTGRES_DB')
    AND pid <> pg_backend_pid();" 2>/dev/null || true

# Drop and recreate databases
echo -e "${YELLOW}Dropping existing databases...${NC}"
PGPASSWORD=$POSTGRES_PASSWORD dropdb -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER $POSTGRES_DB --if-exists 2>/dev/null || true
PGPASSWORD=$POSTGRES_PASSWORD dropdb -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER test_$POSTGRES_DB --if-exists 2>/dev/null || true

echo -e "${YELLOW}Creating main database...${NC}"
PGPASSWORD=$POSTGRES_PASSWORD createdb -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER $POSTGRES_DB

echo -e "${YELLOW}Creating test database...${NC}"
PGPASSWORD=$POSTGRES_PASSWORD createdb -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER test_$POSTGRES_DB

# Remove all migrations
echo -e "${YELLOW}Removing all Django migrations...${NC}"
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete 2>/dev/null || true
find . -path "*/migrations/*.pyc" -delete 2>/dev/null || true

# Make migrations
echo -e "${YELLOW}Creating migrations...${NC}"
python manage.py makemigrations

# Apply migrations
echo -e "${YELLOW}Applying migrations...${NC}"
python manage.py migrate

# Create test user
echo -e "${YELLOW}Creating test user...${NC}"
echo "from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='daryl@yeshuman.io').exists():
    User.objects.create_user(
        username='daryl',
        email='daryl@yeshuman.io',
        password='abc',
        is_staff=True,
        is_superuser=True
    )
    print('✓ Created test user: daryl@yeshuman.io / abc')
else:
    print('✓ Test user already exists')" | python manage.py shell

echo -e "${GREEN}🎉 Database reset complete!${NC}"
echo ""
echo -e "${BLUE}📊 Database Status:${NC}"
echo "  Database: PostgreSQL ($POSTGRES_DB)"
echo "  Host: $POSTGRES_HOST:$POSTGRES_PORT"

echo ""
echo -e "${BLUE}👤 Test User:${NC}"
echo "  Email: daryl@yeshuman.io"
echo "  Password: abc"
echo ""
echo -e "${YELLOW}🚀 Ready to run: python manage.py runserver${NC}"
