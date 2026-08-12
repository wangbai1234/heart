#!/bin/bash
# Test workshop character draft save and load

# Get auth token (assumes you're already logged in via browser)
TOKEN=$(cat ~/.claude/temp_heart_token 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  echo "No token found. Please log in first and save token to ~/.claude/temp_heart_token"
  exit 1
fi

# Create a workshop character with dossier
echo "Creating workshop character..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/characters \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": {"zh": "测试档案角色"},
    "gender": "female",
    "persona": "这是一个用来测试档案信息是否能正确保存和加载的测试角色。",
    "creation_mode": "workshop",
    "profile_blocks": [
      {
        "type": "dossier",
        "title": "档案",
        "rows": [
          {"label": "职业", "value": "测试工程师"},
          {"label": "年龄", "value": "25岁"},
          {"label": "特长", "value": "发现bug"}
        ]
      }
    ]
  }')

echo "$RESPONSE"
CHAR_ID=$(echo "$RESPONSE" | jq -r '.id')

if [ -z "$CHAR_ID" ] || [ "$CHAR_ID" = "null" ]; then
  echo "Failed to create character"
  exit 1
fi

echo "\nCharacter created with ID: $CHAR_ID"

# Fetch the draft
echo "\nFetching draft..."
curl -s -X GET "http://localhost:8000/api/characters/$CHAR_ID/draft" \
  -H "Authorization: Bearer $TOKEN" | jq '.profile_blocks'
