#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：将 JSON 文件数据迁移到数据库
"""

import json
import os
import sys
from core.database import get_database

def migrate_models():
    """迁移模型配置"""
    print("开始迁移模型配置...")
    
    if not os.path.exists('models.json'):
        print("⚠️ models.json 不存在，跳过")
        return
    
    with open('models.json', 'r', encoding='utf-8') as f:
        models_data = json.load(f)
    
    db = get_database()
    count = 0
    
    for category, subcategories in models_data.items():
        for subcategory, models in subcategories.items():
            for model in models:
                success = db.add_model(
                    model_id=model['id'],
                    category=category,
                    subcategory=subcategory,
                    name=model['name'],
                    params=model['params'],
                    params_b=model['params_b'],
                    ctx=model['ctx'],
                    lang=model['lang'],
                    distilled=model['distilled'],
                    quantizations=model['quantizations'],
                    file_pattern=model['file_pattern']
                )
                if success:
                    count += 1
    
    print(f"✅ 成功迁移 {count} 个模型配置")

def migrate_personas():
    """迁移助手配置"""
    print("开始迁移助手配置...")
    
    if not os.path.exists('personas.json'):
        print("⚠️ personas.json 不存在，跳过")
        return
    
    with open('personas.json', 'r', encoding='utf-8') as f:
        personas_data = json.load(f)
    
    db = get_database()
    count = 0
    
    for key, persona in personas_data.items():
        success = db.add_persona(
            key=key,
            name=persona.get('name', ''),
            icon=persona.get('icon', '🤖'),
            icon_path=persona.get('icon_path', ''),
            description=persona.get('description', ''),
            system_prompt=persona.get('system_prompt', ''),
            persona_type=persona.get('type', 'assistant'),
            background_images=persona.get('background_images', '')
        )
        if success:
            count += 1
    
    print(f"✅ 成功迁移 {count} 个助手配置")

def migrate_personal_settings():
    """迁移个人设置"""
    print("开始迁移个人设置...")
    
    if not os.path.exists('personal_settings.json'):
        print("⚠️ personal_settings.json 不存在，跳过")
        return
    
    with open('personal_settings.json', 'r', encoding='utf-8') as f:
        settings_data = json.load(f)
    
    db = get_database()
    count = 0
    
    for key, value in settings_data.items():
        success = db.set_personal_setting(key, value)
        if success:
            count += 1
    
    print(f"✅ 成功迁移 {count} 个个人设置")

def migrate_download_records():
    """迁移下载记录"""
    print("开始迁移下载记录...")
    
    if not os.path.exists('download_records.json'):
        print("⚠️ download_records.json 不存在，跳过")
        return
    
    with open('download_records.json', 'r', encoding='utf-8') as f:
        records_data = json.load(f)
    
    db = get_database()
    count = 0
    
    for record_key, record in records_data.items():
        success = db.add_download_record(
            record_key=record_key,
            model_name=record.get('model_name', ''),
            ollama_name=record.get('ollama_name', ''),
            gguf_path=record.get('gguf_path', ''),
            quantization=record.get('quantization', ''),
            model_id=record.get('model_id', '')
        )
        if success:
            count += 1
    
    print(f"✅ 成功迁移 {count} 个下载记录")

def backup_json_files():
    """备份 JSON 文件"""
    print("备份原始 JSON 文件...")
    
    backup_dir = 'json_backup'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    files = ['models.json', 'personas.json', 'personal_settings.json', 'download_records.json']
    count = 0
    
    for filename in files:
        if os.path.exists(filename):
            backup_path = os.path.join(backup_dir, filename)
            with open(filename, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            count += 1
    
    print(f"✅ 已备份 {count} 个文件到 {backup_dir}/")

def main():
    """主函数"""
    print("=" * 60)
    print("数据迁移工具 - 将 JSON 文件迁移到数据库")
    print("=" * 60)
    print()
    
    # 备份原始文件
    backup_json_files()
    print()
    
    # 执行迁移
    migrate_models()
    migrate_personas()
    migrate_personal_settings()
    migrate_download_records()
    
    print()
    print("=" * 60)
    print("✅ 数据迁移完成！")
    print("=" * 60)
    print()
    print("提示：")
    print("1. 原始 JSON 文件已备份到 json_backup/ 目录")
    print("2. 应用现在将从数据库读取配置")
    print("3. 如需回滚，可以从备份恢复 JSON 文件")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
