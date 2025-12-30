"""数据库查看工具"""

import sqlite3
import json
from datetime import datetime

def view_database(db_path='data.db'):
    """查看数据库内容"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 80)
    print("数据库内容查看工具")
    print("=" * 80)
    
    # 1. 查看所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    print(f"\n📊 数据库表列表 ({len(tables)} 个):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        print(f"  • {table}: {count} 条记录")
    
    # 2. 查看对话
    print("\n" + "=" * 80)
    print("💬 对话列表（最近 5 条）:")
    print("=" * 80)
    cursor.execute('''
        SELECT id, title, persona, created_at, updated_at 
        FROM conversations 
        ORDER BY updated_at DESC 
        LIMIT 5
    ''')
    for row in cursor.fetchall():
        print(f"\nID: {row['id']}")
        print(f"  标题: {row['title']}")
        print(f"  人格: {row['persona']}")
        print(f"  创建: {row['created_at']}")
        print(f"  更新: {row['updated_at']}")
    
    # 3. 查看人格
    print("\n" + "=" * 80)
    print("🤖 人格配置列表:")
    print("=" * 80)
    cursor.execute('SELECT key, name, icon, type, description FROM personas')
    for row in cursor.fetchall():
        print(f"\n{row['icon']} {row['name']} ({row['key']})")
        print(f"  类型: {row['type']}")
        if row['description']:
            print(f"  描述: {row['description'][:50]}...")
    
    # 4. 查看模型
    print("\n" + "=" * 80)
    print("📦 模型配置列表（前 10 个）:")
    print("=" * 80)
    cursor.execute('''
        SELECT name, params, category, subcategory, ctx, lang 
        FROM models 
        LIMIT 10
    ''')
    for row in cursor.fetchall():
        lang = json.loads(row['lang'])
        print(f"\n• {row['name']} ({row['params']})")
        print(f"  分类: {row['category']} / {row['subcategory']}")
        print(f"  上下文: {row['ctx']} tokens")
        print(f"  语言: {', '.join(lang)}")
    
    # 5. 查看下载记录
    print("\n" + "=" * 80)
    print("📥 下载记录:")
    print("=" * 80)
    cursor.execute('''
        SELECT record_key, model_name, quantization, file_exists 
        FROM download_records
    ''')
    records = cursor.fetchall()
    if records:
        for row in records:
            status = "✓" if row['file_exists'] else "✗"
            print(f"  {status} {row['model_name']} ({row['quantization']})")
    else:
        print("  暂无下载记录")
    
    # 6. 查看个人设置
    print("\n" + "=" * 80)
    print("⚙️ 个人设置:")
    print("=" * 80)
    cursor.execute('SELECT key, value FROM personal_settings')
    settings = cursor.fetchall()
    if settings:
        for row in settings:
            try:
                value = json.loads(row['value'])
            except:
                value = row['value']
            
            # 截断长值
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            elif isinstance(value, list) and len(value) > 3:
                value = f"[{len(value)} 项]"
            
            print(f"  • {row['key']}: {value}")
    else:
        print("  暂无个人设置")
    
    # 7. 统计信息
    print("\n" + "=" * 80)
    print("📈 统计信息:")
    print("=" * 80)
    
    cursor.execute('SELECT COUNT(*) as count FROM conversations')
    conv_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM messages')
    msg_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM personas')
    persona_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM models')
    model_count = cursor.fetchone()['count']
    
    print(f"  • 对话总数: {conv_count}")
    print(f"  • 消息总数: {msg_count}")
    print(f"  • 人格总数: {persona_count}")
    print(f"  • 模型总数: {model_count}")
    
    conn.close()
    print("\n" + "=" * 80)


def export_table_to_json(db_path='data.db', table_name='personas', output_file=None):
    """导出表数据为 JSON"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(f'SELECT * FROM {table_name}')
    rows = cursor.fetchall()
    
    data = []
    for row in rows:
        row_dict = dict(row)
        # 尝试解析 JSON 字段
        for key, value in row_dict.items():
            if isinstance(value, str) and value.startswith('['):
                try:
                    row_dict[key] = json.loads(value)
                except:
                    pass
        data.append(row_dict)
    
    if output_file is None:
        output_file = f'{table_name}_export.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已导出 {len(data)} 条记录到: {output_file}")
    conn.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'export' and len(sys.argv) > 2:
            table_name = sys.argv[2]
            output_file = sys.argv[3] if len(sys.argv) > 3 else None
            export_table_to_json(table_name=table_name, output_file=output_file)
        else:
            print("用法:")
            print("  python view_database.py              # 查看数据库")
            print("  python view_database.py export personas  # 导出表")
    else:
        view_database()
