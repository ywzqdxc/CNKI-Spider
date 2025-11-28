import os
import json
import csv
import pandas as pd
from typing import List, Dict


class DataExporter:
    """数据导出工具"""

    @staticmethod
    def ensure_directory(directory: str) -> None:
        """确保目录存在"""
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def export_to_json(papers: List[Dict], filename: str):
        """导出为JSON文件"""
        DataExporter.ensure_directory(os.path.dirname(filename) if os.path.dirname(filename) else '.')

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        print(f"✓ 数据已导出到: {filename}")

    @staticmethod
    def export_to_csv(papers: List[Dict], filename: str):
        """导出为CSV文件"""
        DataExporter.ensure_directory(os.path.dirname(filename) if os.path.dirname(filename) else '.')

        if not papers:
            print("✗ 没有数据可导出")
            return

        df = pd.DataFrame(papers)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✓ 数据已导出到: {filename}")

    @staticmethod
    def export_to_jsonl(papers: List[Dict], filename: str):
        """导出为JSONL格式，适合大模型训练"""
        DataExporter.ensure_directory(os.path.dirname(filename) if os.path.dirname(filename) else '.')

        with open(filename, 'w', encoding='utf-8') as f:
            for paper in papers:
                # 构建适合大模型训练的格式
                messages = [
                    {"role": "system", "content": "你是一个专业的学术助手"},
                    {"role": "user", "content": f"请总结这篇论文的主要内容：{paper.get('title', '')}"},
                    {"role": "assistant", "content": paper.get('abstract', '')}
                ]

                record = {
                    "messages": messages,
                    "metadata": {
                        "title": paper.get('title', ''),
                        "year": paper.get('year', ''),
                        "source": paper.get('link', ''),
                        "keyword": paper.get('keyword', '')
                    }
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"✓ 训练数据已导出到: {filename}")

    @staticmethod
    def export_to_excel(papers: List[Dict], filename: str):
        """导出为Excel文件"""
        DataExporter.ensure_directory(os.path.dirname(filename) if os.path.dirname(filename) else '.')

        if not papers:
            print("✗ 没有数据可导出")
            return

        df = pd.DataFrame(papers)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"✓ 数据已导出到: {filename}")

    @staticmethod
    def print_summary(papers: List[Dict]):
        """打印摘要信息"""
        if not papers:
            print("✗ 未找到相关论文")
            return

        print(f"\n✓ 找到 {len(papers)} 篇相关论文:")
        print("=" * 80)

        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.get('title', '未知标题')}")
            print(f"   年份: {paper.get('year', '未知')}")

            abstract = paper.get('abstract', '')
            if abstract:
                # 截断过长的摘要
                if len(abstract) > 150:
                    abstract = abstract[:150] + "..."
                print(f"   摘要: {abstract}")

            if paper.get('link'):
                print(f"   链接: {paper.get('link')}")

            print("-" * 80)