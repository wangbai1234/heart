#!/usr/bin/env python3
"""Test script for Batch 1 validation"""

import sys
sys.path.insert(0, "/Users/wanglixun/heart/backend")

from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.draft_new_models import ChromeDraft, PremiseCardDraft, PremiseRowDraft

# Test 1: quick mode + public visibility should fail
print("Test 1: quick mode cannot be public")
try:
    draft = CharacterDraft(
        display_name={"zh": "测试"},
        persona="这是一个测试角色的人设描述至少要二十个字才能通过验证",
        creation_mode="quick",
        visibility="public"
    )
    print("❌ FAILED - Should have raised ValueError")
except ValueError as e:
    print(f"✅ PASSED - {e}")

# Test 2: quick mode + custom_html should fail
print("\nTest 2: quick mode cannot set workshop fields")
try:
    draft = CharacterDraft(
        display_name={"zh": "测试"},
        persona="这是一个测试角色的人设描述至少要二十个字才能通过验证",
        creation_mode="quick",
        custom_html="<div>test</div>"
    )
    print("❌ FAILED - Should have raised ValueError")
except ValueError as e:
    print(f"✅ PASSED - {e}")

# Test 3: Color value CSS injection prevention
print("\nTest 3: Color validation - should reject CSS injection")
try:
    chrome = ChromeDraft(
        bg="red; }body{display:none}",
        coverBg="#000",
        scrimGradient="linear-gradient(to bottom, rgba(0,0,0,0.5), transparent)",
        nameColor="#fff",
        ageColor="#ccc",
        taglineColor="#aaa",
        chipActiveBg="#333",
        chipActiveBorder="#444",
        chipActiveText="#fff",
        chipInactiveBg="#eee",
        chipInactiveBorder="#ddd",
        chipInactiveText="#888",
        ctaGradient="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        ctaShadow="0 4px 12px rgba(102, 126, 234, 0.4)"
    )
    print("❌ FAILED - Should have rejected malicious color")
except ValueError as e:
    print(f"✅ PASSED - {e}")

# Test 4: Valid ctaShadow (box-shadow syntax)
print("\nTest 4: Color validation - should accept valid box-shadow")
try:
    chrome = ChromeDraft(
        bg="#000",
        coverBg="#111",
        scrimGradient="linear-gradient(to bottom, rgba(0,0,0,0.5), transparent)",
        nameColor="#fff",
        ageColor="#ccc",
        taglineColor="#aaa",
        chipActiveBg="#333",
        chipActiveBorder="#444",
        chipActiveText="#fff",
        chipInactiveBg="#eee",
        chipInactiveBorder="#ddd",
        chipInactiveText="#888",
        ctaGradient="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        ctaShadow="0 4px 12px rgba(255,107,107,0.3)"
    )
    print("✅ PASSED - Valid box-shadow accepted")
except ValueError as e:
    print(f"❌ FAILED - Should have accepted valid box-shadow: {e}")

# Test 5: Workshop mode with all new fields should work
print("\nTest 5: Workshop mode with full fields")
try:
    draft = CharacterDraft(
        display_name={"zh": "高级角色"},
        persona="这是一个用角色创作模式创建的角色人设至少要二十个字才能通过",
        creation_mode="workshop",
        visibility="public",
        ui_chrome=chrome,
        profile_blocks=[
            {
                "type": "dossier",
                "title": "基本信息",
                "rows": [
                    {"label": "职业", "value": "医生"},
                    {"label": "年龄", "value": "28"}
                ]
            }
        ],
        premise_card={
            "accent": "#ff6b6b",
            "leadIn": "首次相遇档案",
            "title": "初次见面",
            "rows": [{"label": "地点", "value": "医院"}]
        },
        starter_config={
            "type": "flat",
            "prompts": ["你好", "需要帮助吗", "感觉怎么样"]
        },
        opening_format="rich"
    )
    print("✅ PASSED - Workshop mode accepts all fields")
except Exception as e:
    print(f"❌ FAILED - {e}")

print("\n" + "="*50)
print("Batch 1 validation tests completed")
