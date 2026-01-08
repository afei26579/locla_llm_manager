#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
场景导入脚本
用于将 JSON 格式的场景数据导入到指定角色
"""

import json
import sys
import os

# 添加项目根目录到路径
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from core.database import get_database


# 时间段映射
TIME_MAPPING = {
    "凌晨": "midnight",
    "拂晓": "dawn",
    "晨间": "morning",
    "上午": "forenoon",
    "中午": "noon",
    "午后": "afternoon",
    "傍晚": "dusk",
    "夜晚": "night",
    "任意": "any",
}


def parse_time_period(time_str: str) -> str:
    """解析时间字符串，返回时间段 key"""
    for cn_name, key in TIME_MAPPING.items():
        if cn_name in time_str:
            return key
    return "any"


def convert_scene(scene_data: dict) -> dict:
    """将导入的场景数据转换为系统格式"""
    # 解析时间段
    time_period = parse_time_period(scene_data.get("time", ""))
    
    # 获取场景名称
    scene_name = scene_data.get("scene", "")
    
    # 获取开场白
    opening = scene_data.get("opening", "")
    
    # 解析推荐回复
    recommendations = scene_data.get("recommendations", {})
    suggestions = []
    
    # 按 key 排序后提取值
    for key in sorted(recommendations.keys()):
        suggestions.append(recommendations[key])
    
    # 最多3个
    suggestions = suggestions[:3]
    
    return {
        "name": scene_name if scene_name else "未命名场景",
        "time_period": time_period,
        "scene": opening,
        "suggestions": suggestions
    }


def list_personas():
    """列出所有角色扮演类型的角色"""
    db = get_database()
    personas = db.list_personas()
    
    roleplay_personas = []
    for key, data in personas.items():
        if data.get("type") == "roleplay":
            roleplay_personas.append({
                "key": key,
                "name": data.get("name", key),
                "description": data.get("description", "")
            })
    
    return roleplay_personas


def import_scenes(persona_key: str, json_file: str, replace: bool = False):
    """
    导入场景到指定角色
    
    Args:
        persona_key: 角色 key
        json_file: JSON 文件路径
        replace: 是否替换现有场景（False 则追加）
    """
    db = get_database()
    
    # 获取角色信息
    persona = db.get_persona(persona_key)
    if not persona:
        print(f"❌ 未找到角色: {persona_key}")
        return False
    
    if persona.get("type") != "roleplay":
        print(f"❌ 角色 {persona.get('name')} 不是角色扮演类型")
        return False
    
    # 读取 JSON 文件
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            scenes_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
        return False
    
    if not isinstance(scenes_data, list):
        print("❌ JSON 格式错误，应为数组")
        return False
    
    # 转换场景数据
    new_scenes = []
    for i, scene_data in enumerate(scenes_data):
        try:
            converted = convert_scene(scene_data)
            new_scenes.append(converted)
            print(f"  ✓ 场景 {i+1}: {scene_data.get('scene', '未命名')} ({scene_data.get('time', '任意时间')})")
        except Exception as e:
            print(f"  ✗ 场景 {i+1} 转换失败: {e}")
    
    if not new_scenes:
        print("❌ 没有有效的场景数据")
        return False
    
    # 获取现有场景
    existing_scenes = persona.get("scene_designs", [])
    if not isinstance(existing_scenes, list):
        existing_scenes = []
    
    # 合并或替换
    if replace:
        final_scenes = new_scenes
        print(f"\n📝 替换模式：共 {len(new_scenes)} 个场景")
    else:
        final_scenes = existing_scenes + new_scenes
        print(f"\n📝 追加模式：原有 {len(existing_scenes)} 个，新增 {len(new_scenes)} 个，共 {len(final_scenes)} 个")
    
    # 更新数据库
    success = db.add_persona(
        key=persona_key,
        name=persona.get("name", ""),
        icon=persona.get("icon", "🎭"),
        icon_path=persona.get("icon_path", ""),
        description=persona.get("description", ""),
        system_prompt=persona.get("system_prompt", ""),
        persona_type="roleplay",
        background_images=persona.get("background_images", ""),
        scene_designs=final_scenes,
        enable_suggestions=persona.get("enable_suggestions", True),
        gender=persona.get("gender", ""),
        user_identity=persona.get("user_identity", "")
    )
    
    if success:
        print(f"\n✅ 成功导入场景到角色: {persona.get('name')}")
        return True
    else:
        print(f"\n❌ 导入失败")
        return False


def main():
    print("=" * 50)
    print("       场景导入工具")
    print("=" * 50)
    
    # 列出可用角色
    personas = list_personas()
    
    if not personas:
        print("\n❌ 没有找到角色扮演类型的角色")
        print("请先在应用中创建角色扮演角色")
        input("\n按回车键退出...")
        return
    
    print("\n可用的角色扮演角色：")
    print("-" * 40)
    for i, p in enumerate(personas, 1):
        print(f"  {i}. {p['name']}")
        if p['description']:
            print(f"     {p['description']}")
    print("-" * 40)
    
    # 选择角色
    while True:
        try:
            choice = input(f"\n请选择角色 (1-{len(personas)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(personas):
                selected_persona = personas[idx]
                break
            else:
                print("无效的选择，请重新输入")
        except ValueError:
            print("请输入数字")
    
    print(f"\n已选择: {selected_persona['name']}")
    
    # 输入 JSON 文件路径
    json_file = input("\n请输入场景 JSON 文件路径: ").strip()
    json_file = json_file.strip('"').strip("'")  # 去除引号
    
    if not os.path.exists(json_file):
        print(f"❌ 文件不存在: {json_file}")
        input("\n按回车键退出...")
        return
    
    # 选择导入模式
    mode = input("\n导入模式 (1=追加, 2=替换): ").strip()
    replace = mode == "2"
    
    print("\n" + "-" * 40)
    print("开始导入...")
    print("-" * 40)
    
    # 执行导入
    success = import_scenes(selected_persona['key'], json_file, replace)
    
    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
