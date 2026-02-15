#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up Telegram Webhook...${NC}"

# Check if required environment variables are set
if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}Error: BOT_TOKEN is not set${NC}"
    exit 1
fi

if [ -z "$WEBHOOK_URL" ]; then
    echo -e "${RED}Error: WEBHOOK_URL is not set${NC}"
    exit 1
fi

if [ -z "$WEBHOOK_SECRET" ]; then
    echo -e "${RED}Error: WEBHOOK_SECRET is not set${NC}"
    exit 1
fi

# Build the URL for Telegram API
TELEGRAM_API_URL="https://api.telegram.org/bot${BOT_TOKEN}/setWebhook"

echo -e "${YELLOW}Using webhook URL: $WEBHOOK_URL${NC}"
echo -e "${YELLOW}Using webhook secret: $WEBHOOK_SECRET${NC}"

# Set the webhook with secret token
RESPONSE=$(curl -s -X POST "$TELEGRAM_API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "'${WEBHOOK_URL}'",
    "secret_token": "'${WEBHOOK_SECRET}'"
  }')

echo -e "${YELLOW}Telegram API Response:${NC}"
echo "$RESPONSE"

# Check if successful
if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo -e "${GREEN}✓ Webhook set successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Failed to set webhook${NC}"
    exit 1
fi

