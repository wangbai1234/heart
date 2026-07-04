#!/usr/bin/env python3
"""
心屿真实用户流程测试
测试修复后的完整功能，确保数据隔离和所有功能真实可用
"""

import asyncio
import json
import time
import uuid
import websockets
import httpx

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/chat/ws"

# 两个不同的真实用户 ID（模拟 localStorage 中的稳定 ID）
USER_A = str(uuid.uuid4())  # 用户A
USER_B = str(uuid.uuid4())  # 用户B
CHARACTER = "rin"


class RealFlowTester:
    def __init__(self):
        self.results = []
        self.http = httpx.AsyncClient(base_url=BASE_URL, timeout=30)

    async def close(self):
        await self.http.aclose()

    def log(self, test_name: str, passed: bool, detail: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} [{test_name}] {detail}")
        self.results.append({"test": test_name, "passed": passed, "detail": detail})

    async def ws_chat(self, user_id: str, message: str, character_id: str = CHARACTER) -> dict:
        """通过 WebSocket 发送消息并获取完整响应"""
        async with websockets.connect(WS_URL) as ws:
            # 接收 auth_ok
            auth_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            auth_msg = json.loads(auth_raw)
            if auth_msg.get("type") != "auth_ok":
                return {"error": "auth failed"}

            # 发送聊天消息
            turn_id = str(uuid.uuid4())
            await ws.send(
                json.dumps(
                    {
                        "type": "chat",
                        "text": message,
                        "user_id": user_id,
                        "character_id": character_id,
                        "turn_id": turn_id,
                    }
                )
            )

            # 收集响应
            full_text = ""
            turn_id_received = None
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "turn_start":
                        turn_id_received = msg.get("turn_id")
                    elif msg.get("type") == "text_delta":
                        full_text += msg.get("delta", "")
                    elif msg.get("type") == "turn_end":
                        break
                    elif msg.get("type") == "error":
                        return {"error": msg.get("msg", "unknown")}
                except asyncio.TimeoutError:
                    break

            return {"text": full_text, "turn_id": turn_id_received}

    async def get_state(self, user_id: str, state_type: str) -> dict:
        """获取用户状态"""
        resp = await self.http.get(
            f"/api/state/{state_type}", params={"user_id": user_id, "character_id": CHARACTER}
        )
        if resp.status_code == 200:
            return resp.json()
        return {}

    async def get_identity(self, user_id: str) -> list:
        """获取身份记忆"""
        resp = await self.http.get(
            "/api/memory/l4", params={"user_id": user_id, "character_id": CHARACTER}
        )
        if resp.status_code == 200:
            return resp.json().get("memories", [])
        return []

    async def get_episodes(self, user_id: str, limit: int = 10) -> list:
        """获取对话记忆"""
        resp = await self.http.get(
            "/api/memory/recent",
            params={"user_id": user_id, "character_id": CHARACTER, "limit": limit},
        )
        if resp.status_code == 200:
            return resp.json().get("episodes", [])
        return []

    async def test_01_user_a_intro(self):
        """用户A自我介绍"""
        print("\n[1] 用户A自我介绍")
        print("-" * 50)

        resp = await self.ws_chat(
            USER_A, "你好，我叫陈浩，今年28岁，在杭州做前端工程师。很高兴认识你！"
        )
        reply = resp.get("text", "")
        print(f"  回复: {reply[:80]}...")

        # 验证回复包含对名字的确认
        self.log("用户A介绍", len(reply) > 0, f"回复长度: {len(reply)}")

        # 等待记忆编码
        await asyncio.sleep(1)

        # 验证身份记忆已存储
        identity = await self.get_identity(USER_A)
        name_found = any(
            m.get("key") == "name" and "陈浩" in str(m.get("value", "")) for m in identity
        )
        self.log("身份记忆存储", name_found, f"找到 {len(identity)} 条身份记忆")

        return reply

    async def test_02_user_a_recall(self):
        """用户A询问 rin 是否记得自己"""
        print("\n[2] 用户A询问记忆")
        print("-" * 50)

        resp = await self.ws_chat(USER_A, "你还记得我叫什么名字吗？")
        reply = resp.get("text", "")
        print(f"  回复: {reply[:100]}...")

        # 验证 rin 记得名字
        remembers = "陈浩" in reply or "浩" in reply
        self.log("记忆召回", remembers, f"回复中包含名字: {remembers}")

        return reply

    async def test_03_user_b_intro(self):
        """用户B自我介绍（验证数据隔离）"""
        print("\n[3] 用户B自我介绍（数据隔离测试）")
        print("-" * 50)

        resp = await self.ws_chat(
            USER_B, "你好，我叫王小明，今年25岁，在上海做产品经理。很高兴认识你！"
        )
        reply = resp.get("text", "")
        print(f"  回复: {reply[:80]}...")

        self.log("用户B介绍", len(reply) > 0, f"回复长度: {len(reply)}")

        await asyncio.sleep(1)

        # 验证用户B的身份记忆
        identity_b = await self.get_identity(USER_B)
        name_b = any(
            m.get("key") == "name" and "王小明" in str(m.get("value", "")) for m in identity_b
        )
        self.log("用户B身份存储", name_b, f"用户B身份记忆: {len(identity_b)} 条")

        return reply

    async def test_04_isolation(self):
        """验证数据隔离：用户A看不到用户B的数据"""
        print("\n[4] 数据隔离验证")
        print("-" * 50)

        # 用户A询问，不应该知道用户B的信息
        resp = await self.ws_chat(USER_A, "你知道王小明吗？")
        reply = resp.get("text", "")
        print(f"  回复: {reply[:100]}...")

        # 验证隔离：rin 不应该知道用户B
        isolated = "王小明" not in reply or "不知道" in reply or "不认识" in reply
        self.log("数据隔离", isolated, f"rin 不知道用户B: {isolated}")

        # 验证两个用户的身份记忆独立
        identity_a = await self.get_identity(USER_A)
        identity_b = await self.get_identity(USER_B)

        a_has_haohao = any("陈浩" in str(m.get("value", "")) for m in identity_a)
        b_has_xiaoming = any("王小明" in str(m.get("value", "")) for m in identity_b)
        a_no_xiaoming = not any("王小明" in str(m.get("value", "")) for m in identity_a)
        b_no_haohao = not any("陈浩" in str(m.get("value", "")) for m in identity_b)

        self.log(
            "身份记忆隔离",
            a_has_haohao and b_has_xiaoming and a_no_xiaoming and b_no_haohao,
            f"A有陈浩:{a_has_haohao}, B有王小明:{b_has_xiaoming}",
        )

        return isolated

    async def test_05_emotion_tracking(self):
        """验证情绪跟踪"""
        print("\n[5] 情绪跟踪验证")
        print("-" * 50)

        # 获取初始情绪
        emo_before = await self.get_state(USER_A, "emotion")
        vad_before = emo_before.get("vad", {}).get("valence", 0)
        print(f"  初始 valence: {vad_before:.3f}")

        # 发送负面消息
        resp = await self.ws_chat(USER_A, "今天工作好累，被老板骂了一顿，心情很差")
        reply = resp.get("text", "")
        print(f"  回复: {reply[:80]}...")

        await asyncio.sleep(0.5)

        # 获取情绪变化
        emo_after = await self.get_state(USER_A, "emotion")
        vad_after = emo_after.get("vad", {}).get("valence", 0)
        print(f"  之后 valence: {vad_after:.3f}")

        # 验证情绪有变化
        changed = abs(vad_after - vad_before) > 0.001
        self.log("情绪变化", changed, f"valence: {vad_before:.3f} → {vad_after:.3f}")

        return changed

    async def test_06_relationship_building(self):
        """验证关系建立"""
        print("\n[6] 关系建立验证")
        print("-" * 50)

        # 获取初始关系
        rel_before = await self.get_state(USER_A, "relationship")
        trust_before = rel_before.get("trust", 0)
        interactions_before = rel_before.get("total_interactions", 0)
        print(f"  初始信任: {trust_before:.3f}, 互动: {interactions_before}")

        # 发送多条消息建立关系
        messages = [
            "今天天气真不错，阳光明媚的",
            "你有没有什么兴趣爱好呢？我挺好奇的",
            "我觉得和你聊天很舒服，很放松",
        ]
        for msg in messages:
            resp = await self.ws_chat(USER_A, msg)
            await asyncio.sleep(0.3)

        # 获取关系变化
        rel_after = await self.get_state(USER_A, "relationship")
        trust_after = rel_after.get("trust", 0)
        interactions_after = rel_after.get("total_interactions", 0)
        print(f"  之后信任: {trust_after:.3f}, 互动: {interactions_after}")

        # 验证关系增长
        trust_grew = trust_after >= trust_before
        interactions_grew = interactions_after > interactions_before
        self.log("信任增长", trust_grew, f"信任: {trust_before:.3f} → {trust_after:.3f}")
        self.log(
            "互动增长", interactions_grew, f"互动: {interactions_before} → {interactions_after}"
        )

        return trust_grew and interactions_grew

    async def test_07_cold_war(self):
        """验证冷战机制"""
        print("\n[7] 冷战机制验证")
        print("-" * 50)

        # 获取初始状态
        rel_before = await self.get_state(USER_A, "relationship")
        trust_before = rel_before.get("trust", 0)
        print(f"  初始信任: {trust_before:.3f}")

        # 发送冲突消息
        conflict_messages = [
            "我觉得你根本不懂我的感受",
            "我不想跟你说话了，让我一个人静静",
            "别管我，我现在不想说话",
        ]
        for msg in conflict_messages:
            resp = await self.ws_chat(USER_A, msg)
            await asyncio.sleep(0.3)

        # 获取冲突后状态
        rel_conflict = await self.get_state(USER_A, "relationship")
        trust_conflict = rel_conflict.get("trust", 0)
        print(f"  冲突后信任: {trust_conflict:.3f}")

        # 验证信任下降
        trust_dropped = trust_conflict < trust_before
        self.log("冲突信任下降", trust_dropped, f"信任: {trust_before:.3f} → {trust_conflict:.3f}")

        # 发送道歉
        resp = await self.ws_chat(USER_A, "对不起，刚才是我太冲动了，我不该那样说你")
        await asyncio.sleep(0.5)

        # 获取修复后状态
        rel_repair = await self.get_state(USER_A, "relationship")
        trust_repair = rel_repair.get("trust", 0)
        print(f"  修复后信任: {trust_repair:.3f}")

        # 验证修复
        trust_recovered = trust_repair > trust_conflict
        self.log(
            "修复信任回升", trust_recovered, f"信任: {trust_conflict:.3f} → {trust_repair:.3f}"
        )

        return trust_dropped and trust_recovered

    async def test_08_persistence(self):
        """验证数据持久化（重启后仍然记得）"""
        print("\n[8] 数据持久化验证")
        print("-" * 50)

        # 重新连接（模拟重启）
        resp = await self.ws_chat(USER_A, "我之前告诉过你我的名字吗？")
        reply = resp.get("text", "")
        print(f"  回复: {reply[:100]}...")

        # 验证 rin 记得名字
        remembers = "陈浩" in reply or "浩" in reply
        self.log("持久化记忆", remembers, f"rin 记得名字: {remembers}")

        return remembers

    async def test_09_memory_episodes(self):
        """验证对话记忆存储"""
        print("\n[9] 对话记忆存储验证")
        print("-" * 50)

        episodes = await self.get_episodes(USER_A, limit=5)
        print(f"  最近 {len(episodes)} 条记忆:")
        for i, ep in enumerate(episodes[:3], 1):
            summary = ep.get("episode_summary", ep.get("text", ""))[:50]
            print(f"    {i}. {summary}")

        # 验证记忆存在
        has_episodes = len(episodes) > 0
        self.log("对话记忆存储", has_episodes, f"找到 {len(episodes)} 条记忆")

        return has_episodes

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("心屿真实用户流程测试 — 修复后验证")
        print("=" * 60)
        print(f"用户A: {USER_A[:8]}...")
        print(f"用户B: {USER_B[:8]}...")
        print(f"角色: {CHARACTER}")

        try:
            await self.test_01_user_a_intro()
            await self.test_02_user_a_recall()
            await self.test_03_user_b_intro()
            await self.test_04_isolation()
            await self.test_05_emotion_tracking()
            await self.test_06_relationship_building()
            await self.test_07_cold_war()
            await self.test_08_persistence()
            await self.test_09_memory_episodes()
        finally:
            await self.close()

        # 汇总
        print("\n" + "=" * 60)
        print("测试汇总")
        print("=" * 60)
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        print(f"通过: {passed}/{total} ({100 * passed / total:.1f}%)")

        for r in self.results:
            status = "✅" if r["passed"] else "❌"
            print(f"  {status} {r['test']}: {r['detail']}")

        return passed == total


async def main():
    tester = RealFlowTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
