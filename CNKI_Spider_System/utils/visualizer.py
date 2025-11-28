import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import pandas as pd
from collections import Counter
import jieba
from typing import List, Dict
import os


class DataVisualizer:
    """数据可视化工具"""

    def __init__(self):
        plt.style.use('seaborn-v0_8')
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']

    def create_year_distribution(self, papers: List[Dict], save_path: str = None):
        """创建年份分布图"""
        years = [paper.get('year', '未知') for paper in papers]
        year_counts = Counter(years)

        # 过滤掉非数字年份
        valid_years = {k: v for k, v in year_counts.items() if k.isdigit()}

        if not valid_years:
            return

        # 按年份排序
        sorted_years = sorted(valid_years.items(), key=lambda x: int(x[0]))
        years_list = [item[0] for item in sorted_years]
        counts_list = [item[1] for item in sorted_years]

        plt.figure(figsize=(12, 6))
        bars = plt.bar(years_list, counts_list, color=self.colors[0])
        plt.title('文献年份分布', fontsize=16, fontweight='bold')
        plt.xlabel('年份', fontsize=12)
        plt.ylabel('文献数量', fontsize=12)
        plt.xticks(rotation=45)

        # 在柱子上显示数量
        for bar, count in zip(bars, counts_list):
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                     str(count), ha='center', va='bottom', fontsize=10)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()

    def create_wordcloud(self, papers: List[Dict], save_path: str = None):
        """创建词云图"""
        # 提取标题和摘要文本
        text = ' '.join([
            paper.get('title', '') + ' ' + paper.get('abstract', '')
            for paper in papers
        ])

        if not text.strip():
            return

        # 使用jieba进行中文分词
        words = jieba.cut(text)
        word_text = ' '.join(words)

        # 生成词云
        wordcloud = WordCloud(
            font_path='simhei.ttf',
            width=800,
            height=400,
            background_color='white',
            colormap='viridis',
            max_words=100
        ).generate(word_text)

        plt.figure(figsize=(12, 6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('文献关键词词云', fontsize=16, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()

    def create_abstract_length_distribution(self, papers: List[Dict], save_path: str = None):
        """创建摘要长度分布图"""
        abstract_lengths = [len(paper.get('abstract', '')) for paper in papers]

        plt.figure(figsize=(10, 6))
        plt.hist(abstract_lengths, bins=20, color=self.colors[1], alpha=0.7, edgecolor='black')
        plt.title('摘要长度分布', fontsize=16, fontweight='bold')
        plt.xlabel('摘要长度（字符数）', fontsize=12)
        plt.ylabel('频次', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()

    def create_source_analysis(self, papers: List[Dict], save_path: str = None):
        """创建来源分析图"""
        # 提取关键词或来源信息
        sources = []
        for paper in papers:
            if 'keyword' in paper and paper['keyword']:
                sources.append(paper['keyword'])
            elif 'link' in paper and 'kns.cnki.net' in paper['link']:
                sources.append('知网检索')
            else:
                sources.append('其他来源')

        source_counts = Counter(sources)

        plt.figure(figsize=(10, 8))
        plt.pie(
            source_counts.values(),
            labels=source_counts.keys(),
            autopct='%1.1f%%',
            colors=self.colors,
            startangle=90
        )
        plt.title('文献来源分布', fontsize=16, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()

    def create_comprehensive_dashboard(self, papers: List[Dict], save_path: str = None):
        """创建综合仪表板"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('文献数据分析仪表板', fontsize=20, fontweight='bold')

        # 1. 年份分布
        years = [paper.get('year', '未知') for paper in papers]
        year_counts = Counter([y for y in years if y.isdigit()])
        if year_counts:
            sorted_years = sorted(year_counts.items(), key=lambda x: int(x[0]))
            years_list = [item[0] for item in sorted_years[-10:]]  # 最近10年
            counts_list = [item[1] for item in sorted_years[-10:]]
            axes[0, 0].bar(years_list, counts_list, color=self.colors[0])
            axes[0, 0].set_title('近10年文献分布', fontweight='bold')
            axes[0, 0].tick_params(axis='x', rotation=45)

        # 2. 摘要长度分布
        abstract_lengths = [len(paper.get('abstract', '')) for paper in papers]
        axes[0, 1].hist(abstract_lengths, bins=15, color=self.colors[1], alpha=0.7, edgecolor='black')
        axes[0, 1].set_title('摘要长度分布', fontweight='bold')
        axes[0, 1].set_xlabel('字符数')
        axes[0, 1].set_ylabel('频次')

        # 3. 来源分析
        sources = [paper.get('keyword', '其他') for paper in papers]
        source_counts = Counter(sources)
        if len(source_counts) > 1:
            axes[1, 0].pie(
                source_counts.values(),
                labels=source_counts.keys(),
                autopct='%1.1f%%',
                colors=self.colors
            )
            axes[1, 0].set_title('检索来源分布', fontweight='bold')

        # 4. 数据质量分析
        valid_abstracts = sum(1 for paper in papers if
                              paper.get('abstract') and paper['abstract'] not in ['无摘要', '获取摘要失败',
                                                                                  '未找到摘要'])
        quality_metrics = {
            '有效摘要': valid_abstracts,
            '无效摘要': len(papers) - valid_abstracts
        }
        axes[1, 1].bar(quality_metrics.keys(), quality_metrics.values(), color=[self.colors[2], self.colors[0]])
        axes[1, 1].set_title('数据质量分析', fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()