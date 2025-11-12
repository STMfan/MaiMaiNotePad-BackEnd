import json

# 读取JSON文件中的用户
with open('data/users.json', 'r', encoding='utf-8') as f:
    users = json.load(f)

print(f'JSON用户数: {len(users)}')
for user in users:
    print(f'用户: {user["username"]}, ID: {user["userID"]}')