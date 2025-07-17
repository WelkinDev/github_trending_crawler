import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any
import time
import random
import json
import os

class GitHubTrendingCrawler:
    def __init__(self):
        self.trending_url = "https://github.com/trending"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.max_retries = 10  # 最大重试次数
        self.timeout = 10     # 请求超时时间（秒）
        self.state_file = "crawler_state.json"  # 状态保存文件
    
    def _fetch_page(self, language: str = None) -> str:
        """获取指定语言的Trending页面，带重试机制"""
        url = self.trending_url
        if language:
            url += f"/{language}"
        
        for attempt in range(self.max_retries):
            try:
                logging.info(f"请求页面: {url} (尝试 {attempt+1}/{self.max_retries})")
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.exceptions.Timeout:
                logging.warning(f"请求超时: {url}")
            except requests.exceptions.RequestException as e:
                logging.warning(f"请求异常: {url}, 错误: {str(e)}")
            
            # 指数退避重试
            wait_time = 2 ** attempt + random.random()
            logging.info(f"等待 {wait_time:.2f} 秒后重试")
            time.sleep(wait_time)
        
        logging.error(f"请求失败: {url}, 达到最大重试次数")
        return ""
    
    def get_trending_repos(self, language: str = None) -> List[Dict[str, Any]]:
        """获取 GitHub 每日 Trending 仓库"""
        page_content = self._fetch_page(language)
        if not page_content:
            return []
        
        try:
            logging.info(f"开始解析 {language or '所有语言'} 的 Trending 页面")
            soup = BeautifulSoup(page_content, 'html.parser')
            repo_items = soup.select('article.Box-row')
            
            if not repo_items:
                logging.info(f"未找到 {language or '所有语言'} 的 Trending 仓库")
                return []
            
            trending_repos = []
            for idx, item in enumerate(repo_items, 1):
                try:
                    # 获取仓库名称和作者
                    full_name_element = item.select_one('h2 a')
                    if not full_name_element:
                        continue
                    
                    # 彻底清除所有多余空格
                    full_name = ''.join(full_name_element.get_text().split())
                    full_name = full_name.replace('/', '/')
                    owner, name = full_name.split('/', 1)
                    
                    # 获取仓库描述
                    desc_element = item.select_one('p.col-9')
                    description = desc_element.get_text(strip=True) if desc_element else ""
                    
                    # 获取编程语言
                    lang_element = item.select_one('span[itemprop="programmingLanguage"]')
                    language = lang_element.get_text(strip=True) if lang_element else None
                    
                    # 获取 star 和 fork 数量
                    links = item.select('a.Link--muted.d-inline-block.mr-3')
                    stars = links[0].get_text(strip=True) if len(links) > 0 else "0"
                    fork = links[1].get_text(strip=True) if len(links) > 1 else "0"
                    
                    # 标准化 star 和 fork 数量
                    stars = self._normalize_count(stars)
                    fork = self._normalize_count(fork)
                    
                    trending_repos.append({
                        'idx': idx,
                        'name': name,
                        'full_name': full_name,
                        'language': language,
                        'stars': stars,
                        'fork': fork,
                        'url': f'https://github.com/{full_name}',
                        'description': description
                    })
                except Exception as e:
                    logging.error(f"解析单个仓库时出错: {str(e)}")
                    continue
            
            logging.info(f"成功获取 {len(trending_repos)} 个 {language or '所有语言'} 的 Trending 仓库")
            return trending_repos
        except Exception as e:
            logging.error(f"解析 Trending 页面失败: {str(e)}")
            return []
    
    def _normalize_count(self, count_str: str) -> int:
        """将类似 "1.2k" 的计数转换为整数"""
        count_str = count_str.strip().replace(',', '')
        if 'k' in count_str:
            return int(float(count_str.replace('k', '')) * 1000)
        return int(count_str)
    
    def load_state(self) -> Dict[str, Any]:
        """加载爬虫状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"加载状态文件失败: {str(e)}")
        return {"completed_languages": []}
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """保存爬虫状态"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logging.error(f"保存状态文件失败: {str(e)}")
    
    def clear_state(self) -> None:
        """清除爬虫状态文件"""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                logging.info("已清除状态文件")
            except Exception as e:
                logging.error(f"清除状态文件失败: {str(e)}")    