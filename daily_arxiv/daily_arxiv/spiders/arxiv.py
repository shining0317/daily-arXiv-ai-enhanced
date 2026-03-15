import scrapy
import os
import re


class ArxivSpider(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = os.environ.get("CATEGORIES", "cs.CV")
        categories = categories.split(",")
        # 保存目标分类列表，用于后续验证
        self.target_categories = set(map(str.strip, categories))
        self.start_urls = [
            f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        ]  # 起始URL（计算机科学领域的最新论文）

    name = "arxiv"  # 爬虫名称
    allowed_domains = ["arxiv.org"]  # 允许爬取的域名

def parse(self, response):
        # 提取每篇论文的信息
        anchors = []
        for li in response.css("div[id=dlpage] ul li"):
            href = li.css("a::attr(href)").get()
            if href and "item" in href:
                anchors.append(int(href.split("item")[-1]))

        count = 0  # 【新增1】设置一个计数器，初始值为0

        # 遍历每篇论文的详细信息
        for paper in response.css("dl dt"):
            if count >= 30:  # 【新增2】如果已经抓够了5篇，直接停止抓取
                break

            paper_anchor = paper.css("a[name^='item']::attr(name)").get()
            if not paper_anchor:
                continue
                
            paper_id = int(paper_anchor.split("item")[-1])
            if anchors and paper_id >= anchors[-1]:
                continue

            # 获取论文ID
            abstract_link = paper.css("a[title='Abstract']::attr(href)").get()
            if not abstract_link:
                continue
                
            arxiv_id = abstract_link.split("/")[-1]
            
            # 获取对应的论文描述部分 (dd元素)
            # ================== 【新增：精准关键词拦截器】 ==================
            # 1. 提取网页上的论文标题，并全部转换为小写
            title_parts = paper_dd.css(".list-title::text, .list-title *::text").getall()
            title_text = "".join(title_parts).lower()
            
            # 2. 定义你毕设的核心关键词（注意：必须全部用小写英文字母）
            my_keywords = [
                # === 物质与物理性质 (DES核心) ===
                "eutectic",          # 共晶 (涵盖 Deep Eutectic Solvents)
                "polarity",          # 极性
                "melting point",     # 熔点
                "enthalpy",          # 焓变/熔化焓

                # === 算法与预测基础 ===
                "machine learning",  # 机器学习
                "property prediction",# 性质预测
                "tabular",           # 表格数据 (追踪 TabPFN 等表格基础模型)

                # === 【新增】小样本与低数据量场景 ===
                "small data",        # 小数据集 (如 Nature 标题中的 small data)
                "small sample",      # 小样本
                "few-shot",          # 少样本学习 (带连字符)
                "few shot",          # 少样本学习 (无连字符)
                "low data",          # 低数据量
                "data-efficient",    # 数据高效利用 (在小数据领域极常用)
                "scarce data",       # 稀缺数据

                # === 【新增】前沿网络架构 (结合物理与多任务) ===
                "pinn",              # 物理信息神经网络 (Physics-Informed Neural Networks)
                "physics-informed",  # 融合物理信息的 (带连字符)
                "physics informed",  # 融合物理信息的 (无连字符)
                "multi-task",        # 多任务预测/学习 (带连字符)
                "multitask"          # 多任务预测/学习 (连写)
            ]
            
            # 3. 如果标题中不包含以上【任何一个】关键词，直接无情抛弃，去看下一篇！
            if not any(kw in title_text for kw in my_keywords):
                continue
            # ==============================================================
            
            # 提取论文分类信息 - 在subjects部分
            subjects_text = paper_dd.css(".list-subjects .primary-subject::text").get()
            if not subjects_text:
                # 如果找不到主分类，尝试其他方式获取分类
                subjects_text = paper_dd.css(".list-subjects::text").get()
            
            if subjects_text:
                # 解析分类信息，通常格式如 "Computer Vision and Pattern Recognition (cs.CV)"
                # 提取括号中的分类代码
                categories_in_paper = re.findall(r'\(([^)]+)\)', subjects_text)
                
                # 检查论文分类是否与目标分类有交集
                paper_categories = set(categories_in_paper)
                if paper_categories.intersection(self.target_categories):
                    count += 1  # 【新增3】成功找到一篇目标大类的论文，计数器加1
                    yield {
                        "id": arxiv_id,
                        "categories": list(paper_categories),  # 添加分类信息用于调试
                    }
                    self.logger.info(f"Found paper {arxiv_id} with categories {paper_categories}")
                else:
                    self.logger.debug(f"Skipped paper {arxiv_id} with categories {paper_categories} (not in target {self.target_categories})")
            else:
                # 如果无法获取分类信息，记录警告但仍然返回论文（保持向后兼容）
                self.logger.warning(f"Could not extract categories for paper {arxiv_id}, including anyway")
                count += 1  # 【新增(可选)】如果没分类信息但强行返回了，也算进额度里
                yield {
                    "id": arxiv_id,
                    "categories": [],
                }
