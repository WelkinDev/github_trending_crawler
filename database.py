import sqlite3
import datetime
from typing import List, Dict, Any

class Database:
    def __init__(self, db_path: str = "github_trending.db"):
        self.db_path = db_path
        self._create_tables()
        self._initialize_fts()  # 确保全文搜索表初始化
    
    def _create_tables(self) -> None:
        """创建数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建仓库表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idx INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    full_name TEXT UNIQUE NOT NULL,
                    language TEXT,
                    stars INTEGER,
                    fork INTEGER,
                    url TEXT NOT NULL,
                    description TEXT,
                    date TEXT NOT NULL
                )
            ''')
            
            # 创建全文搜索虚拟表
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS repo_fts 
                USING fts5(name, full_name, description, content=repositories, 
                           content_rowid=id, tokenize=porter)
            ''')
            
            # 创建触发器，确保全文搜索表与主表同步
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS repo_ai AFTER INSERT ON repositories
                BEGIN
                    INSERT INTO repo_fts(rowid, name, full_name, description)
                    VALUES (new.id, new.name, new.full_name, new.description);
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS repo_ad AFTER DELETE ON repositories
                BEGIN
                    INSERT INTO repo_fts(repo_fts, rowid, name, full_name, description)
                    VALUES ('delete', old.id, old.name, old.full_name, old.description);
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS repo_au AFTER UPDATE ON repositories
                BEGIN
                    INSERT INTO repo_fts(repo_fts, rowid, name, full_name, description)
                    VALUES ('delete', old.id, old.name, old.full_name, old.description);
                    INSERT INTO repo_fts(rowid, name, full_name, description)
                    VALUES (new.id, new.name, new.full_name, new.description);
                END
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_repositories_language 
                ON repositories (language)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_repositories_date 
                ON repositories (date)
            ''')
            
            conn.commit()
    
    def _initialize_fts(self) -> None:
        """初始化全文搜索表数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查全文搜索表是否有数据
            cursor.execute('SELECT COUNT(*) FROM repo_fts')
            count = cursor.fetchone()[0]
            
            # 如果没有数据，从主表导入
            if count == 0:
                print("初始化全文搜索表数据...")
                cursor.execute('INSERT INTO repo_fts(rowid, name, full_name, description) SELECT id, name, full_name, description FROM repositories')
                conn.commit()
    
    def search_repositories(self, query: str = "", language: str = None, date: str = None, 
                            page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
        """搜索仓库，支持全文搜索和过滤条件，支持分页"""
        offset = (page - 1) * per_page
        
        base_query = '''
            SELECT r.*
            FROM repositories r
        '''
        
        # 仅当有关键词时才需要连接全文搜索表
        if query:
            base_query += ' JOIN repo_fts fts ON r.id = fts.rowid '
            where_clauses = ['repo_fts MATCH ?']
            params = [query]
        else:
            where_clauses = []
            params = []
        
        # 添加语言和日期筛选条件
        if language:
            where_clauses.append('r.language = ?')
            params.append(language)
        
        if date:
            where_clauses.append('r.date = ?')
            params.append(date)
        
        # 组合WHERE子句
        if where_clauses:
            base_query += ' WHERE ' + ' AND '.join(where_clauses)
        
        # 添加排序和分页
        base_query += ' ORDER BY r.date DESC, r.idx ASC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(base_query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def count_repositories(self, query: str = "", language: str = None, date: str = None) -> int:
        """计算符合条件的仓库数量"""
        base_query = '''
            SELECT COUNT(*)
            FROM repositories r
        '''
        
        # 仅当有关键词时才需要连接全文搜索表
        if query:
            base_query += ' JOIN repo_fts fts ON r.id = fts.rowid '
            where_clauses = ['repo_fts MATCH ?']
            params = [query]
        else:
            where_clauses = []
            params = []
        
        # 添加语言和日期筛选条件
        if language:
            where_clauses.append('r.language = ?')
            params.append(language)
        
        if date:
            where_clauses.append('r.date = ?')
            params.append(date)
        
        # 组合WHERE子句
        if where_clauses:
            base_query += ' WHERE ' + ' AND '.join(where_clauses)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(base_query, params)
            return cursor.fetchone()[0]
    
    def insert_repositories(self, repos: List[Dict[str, Any]]) -> None:
        """插入或更新仓库信息"""
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for repo in repos:
                try:
                    # 处理 star 和 fork 数量
                    stars = int(repo['stars']) if repo['stars'] else 0
                    fork = int(repo['fork']) if repo['fork'] else 0
                    
                    # 插入或替换仓库信息
                    cursor.execute('''
                        INSERT OR REPLACE INTO repositories 
                        (idx, name, full_name, language, stars, fork, url, description, date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        repo['idx'],
                        repo['name'],
                        repo['full_name'],
                        repo['language'],
                        stars,
                        fork,
                        repo['url'],
                        repo['description'],
                        today
                    ))
                except Exception as e:
                    print(f"Error inserting repo {repo['full_name']}: {e}")
            
            conn.commit()
    
    def get_languages(self) -> List[str]:
        """获取所有出现过的编程语言"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT language 
                FROM repositories 
                WHERE language IS NOT NULL
                ORDER BY language
            ''')
            return [row[0] for row in cursor.fetchall()]
    
    def get_dates_with_data(self) -> List[str]:
        """获取有数据的日期列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT date 
                FROM repositories
                ORDER BY date DESC
            ''')
            return [row[0] for row in cursor.fetchall()]    