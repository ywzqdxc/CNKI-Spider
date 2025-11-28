import pandas as pd
import json
import os
from .config import FINETUNE_DIR


def convert_csv_to_jsonl(csv_path):
    """将采集的CSV转换为大模型微调所需的JSONL格式"""
    try:
        filename = os.path.basename(csv_path).replace('.csv', '.jsonl')
        output_path = os.path.join(FINETUNE_DIR, filename)

        df = pd.read_csv(csv_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            for _, row in df.iterrows():
                # 简单的数据清洗
                title = str(row.get('title', '')).strip()
                abstract = str(row.get('abstract', '')).strip()

                if not title or not abstract or abstract == 'nan' or abstract == '无摘要':
                    continue

                # 构建微调格式
                data = {
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术科研助手。"},
                        {"role": "user", "content": f"请介绍一下关于《{title}》的研究内容。"},
                        {"role": "assistant", "content": abstract}
                    ]
                }
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        return True, output_path
    except Exception as e:
        return False, str(e)