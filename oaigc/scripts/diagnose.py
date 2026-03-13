#!/usr/bin/env python3
"""
OAI API 诊断脚本 - 用于排查API调用问题
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_URL = "https://oaigc.cn/api"

def curl_post(url: str, payload: dict, headers: dict, timeout: int = 60):
    """发送POST请求"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp_path = f.name
    try:
        cmd = ["curl", "-s", "-S", "-X", "POST", url,
               "--max-time", str(timeout), "-d", f"@{tmp_path}"]
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
        return subprocess.run(cmd, capture_output=True, text=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

def curl_get(url: str, headers: dict, timeout: int = 60):
    """发送GET请求"""
    cmd = ["curl", "-s", "-S", "-X", "GET", url, "--max-time", str(timeout)]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    print("=" * 60)
    print("OAI API 诊断工具")
    print("=" * 60)
    
    # 获取API Key
    api_key = input("\n请输入你的API Key: ").strip()
    if not api_key:
        print("错误: API Key不能为空")
        return
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    print("\n" + "-" * 60)
    print("测试 1: 检查API Key有效性 (获取模型列表)")
    print("-" * 60)
    result = curl_get(f"{BASE_URL}/v1/model/list", headers, timeout=15)
    print(f"HTTP状态: {result.returncode}")
    print(f"响应: {result.stdout[:500] if result.stdout else result.stderr}")
    
    print("\n" + "-" * 60)
    print("测试 2: 检查账户信息")
    print("-" * 60)
    result = curl_get(f"{BASE_URL}/v1/user/account-info", headers, timeout=15)
    print(f"HTTP状态: {result.returncode}")
    print(f"响应: {result.stdout[:500] if result.stdout else result.stderr}")
    
    print("\n" + "-" * 60)
    print("测试 3: 提交任务 (阿里造相-文生图)")
    print("-" * 60)
    
    # 测试不同的请求格式
    test_payloads = [
        {
            "name": "格式A: appId + parameter包装",
            "payload": {
                "appId": "z-imagewenshengt",
                "parameter": {
                    "prompt": "a cute cat",
                    "num": 1,
                    "magnification": 1.1,
                    "aspect_ratio": "1:1"
                }
            }
        },
        {
            "name": "格式B: 直接参数",
            "payload": {
                "appId": "z-imagewenshengt",
                "prompt": "a cute cat"
            }
        },
        {
            "name": "格式C: 仅appId",
            "payload": {
                "appId": "z-imagewenshengt"
            }
        }
    ]
    
    for test in test_payloads:
        print(f"\n尝试 {test['name']}:")
        print(f"请求体: {json.dumps(test['payload'], ensure_ascii=False)}")
        result = curl_post(f"{BASE_URL}/v1/task/submit", test['payload'], headers, timeout=30)
        print(f"HTTP返回码: {result.returncode}")
        print(f"响应: {result.stdout[:800] if result.stdout else '无响应'}")
        if result.stderr:
            print(f"错误: {result.stderr[:500]}")
        
        # 解析响应
        try:
            resp = json.loads(result.stdout)
            if resp.get("code") == 200:
                print("✅ 成功! 任务已提交")
                task_id = resp.get("data", {}).get("taskId")
                if task_id:
                    print(f"任务ID: {task_id}")
                break
            else:
                print(f"❌ 失败: code={resp.get('code')}, message={resp.get('message', resp.get('msg'))}")
        except:
            print("❌ 响应解析失败")
    
    print("\n" + "-" * 60)
    print("测试 4: 提交任务 (即梦绘画)")
    print("-" * 60)
    
    jimeng_payloads = [
        {
            "name": "格式A: appId + parameter包装",
            "payload": {
                "appId": "jimeng",
                "parameter": {
                    "prompt": "a cute cat playing with a ball"
                }
            }
        },
        {
            "name": "格式B: 直接参数",
            "payload": {
                "appId": "jimeng",
                "prompt": "a cute cat playing with a ball"
            }
        }
    ]
    
    for test in jimeng_payloads:
        print(f"\n尝试 {test['name']}:")
        print(f"请求体: {json.dumps(test['payload'], ensure_ascii=False)}")
        result = curl_post(f"{BASE_URL}/v1/task/submit", test['payload'], headers, timeout=30)
        print(f"HTTP返回码: {result.returncode}")
        print(f"响应: {result.stdout[:800] if result.stdout else '无响应'}")
        
        try:
            resp = json.loads(result.stdout)
            if resp.get("code") == 200:
                print("✅ 成功!")
                break
            else:
                print(f"❌ 失败: code={resp.get('code')}, message={resp.get('message', resp.get('msg'))}")
        except:
            print("❌ 响应解析失败")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
