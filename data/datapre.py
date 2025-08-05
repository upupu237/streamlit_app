import json
import os

def txt_to_json(file_path):
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('问题：'):
                    question = line.replace('问题：', '')
                    i += 1
                    answer = ""
                    while i < len(lines) and not lines[i].strip().startswith('问题：'):
                        answer += lines[i].strip().replace('答案：', '') + " "
                        i += 1
                    answer = answer.strip()
                    if answer:
                        item = {
                            "问题": question,
                            "答案": answer
                        }
                        data.append(item)
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到。")
    return data

# 定义三个TXT文件的路径
file_paths = [
    'interview_question/数据分析.txt',
    'interview_question/产品经理.txt',
    'interview_question/运维.txt',
    'interview_question/后端开发.txt',
    'interview_question/软件测试.txt'
]

# 创建data目录（如果不存在）
if not os.path.exists(''):
    os.makedirs('')

for file_path in file_paths:
    file_data = txt_to_json(file_path)
    # 从文件路径中提取文件名
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    json_file_path = os.path.join('', f'{file_name}.json')
    # 将结果保存为JSON文件
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(file_data, json_file, ensure_ascii=False, indent=4)
    print(f"转换完成，结果已保存到 {json_file_path}")