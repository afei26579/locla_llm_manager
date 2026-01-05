import sqlite3

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# 查看最新对话使用的模型
cursor.execute('SELECT DISTINCT model FROM messages WHERE conversation_id="20251231_174459"')
models = cursor.fetchall()
print("对话 20251231_174459 使用的模型:")
for m in models:
    print(f"  - {m[0]}")

# 查看所有消息
cursor.execute('SELECT id, model, role, substr(content, 1, 30) FROM messages WHERE conversation_id="20251231_174459" ORDER BY timestamp')
messages = cursor.fetchall()
print("\n消息列表:")
for msg in messages:
    print(f"  ID:{msg[0]} | 模型:{msg[1]} | 角色:{msg[2]} | 内容:{msg[3]}...")

conn.close()
