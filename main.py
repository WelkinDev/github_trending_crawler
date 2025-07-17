import logging
import time
from crawler import GitHubTrendingCrawler
from database import Database
import random  # 添加缺失的导入

def main():
    """主程序入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='github_trending_crawler.log'
    )
    
    try:
        logging.info("===== 开始执行 GitHub Trending 爬虫 =====")
        
        # 创建爬虫和数据库实例
        crawler = GitHubTrendingCrawler()
        db = Database()
        
        # 加载状态
        state = crawler.load_state()
        completed_languages = state.get("completed_languages", [])
        
        # 获取所有语言的 Trending 仓库
        languages = [
            '',  # 所有语言
            'python',
            'javascript',
            'java',
            'typescript',
            'c++',
            'c#',
            'go',
            'rust',
            'php',
            'ruby',
            'swift',
            'kotlin',
            'dart',
            'html',
            'css',
            'shell',
            'objective-c'
            'scala',
            'groovy',
            'haskell',
            'perl'
        ]
        
        all_repos = []
        
        for lang in languages:
            # 跳过已完成的语言
            if lang in completed_languages:
                logging.info(f"跳过已完成的语言: {lang}")
                continue
            
            logging.info(f"开始爬取 {lang if lang else '所有语言'} 的 Trending 仓库")
            repos = crawler.get_trending_repos(lang if lang else None)
            
            if repos:
                all_repos.extend(repos)
                db.insert_repositories(repos)
                logging.info(f"成功保存 {len(repos)} 个 {lang if lang else '所有语言'} 的仓库")
            else:
                logging.warning(f"未找到 {lang if lang else '所有语言'} 的 Trending 仓库")
            
            # 更新状态
            completed_languages.append(lang)
            crawler.save_state({"completed_languages": completed_languages})
            
            # 避免频繁请求
            wait_time = random.uniform(3, 7)
            logging.info(f"等待 {wait_time:.2f} 秒后继续下一种语言")
            time.sleep(wait_time)
        
        if all_repos:
            logging.info(f"总共成功保存 {len(all_repos)} 个仓库到数据库")
        else:
            logging.warning("未获取到任何 Trending 仓库")
        
        # 清除状态文件（爬取完成后）
        crawler.clear_state()
        logging.info("===== GitHub Trending 爬虫执行完成 =====")
        
    except Exception as e:
        logging.critical(f"程序执行失败: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()    