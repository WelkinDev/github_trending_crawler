from flask import Flask, render_template, request
from database import Database
import logging

app = Flask(__name__)
db = Database()

# 添加自定义过滤器，用于格式化数字为带千位分隔符的字符串
@app.template_filter('commaint')
def commaint_filter(value):
    """将整数格式化为带千位分隔符的字符串"""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

@app.route('/', methods=['GET'])
def index():
    """主页面：处理搜索请求并展示结果"""
    languages = db.get_languages()
    dates = db.get_dates_with_data()
    
    # 获取搜索参数
    search_query = request.args.get('search')
    language = request.args.get('language')
    date = request.args.get('date')
    
    # 获取分页参数
    page = int(request.args.get('page', 1))
    per_page = 30  # 每页显示数量，修改为与database.py一致的参数名
    
    # 执行搜索 - 使用per_page参数名
    repositories = db.search_repositories(
        query=search_query,
        language=language,
        date=date,
        page=page,
        per_page=per_page  # 修改参数名与database.py一致
    )
    
    # 获取总记录数
    total_count = db.count_repositories(
        query=search_query,
        language=language,
        date=date
    )
    
    # 计算总页数
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template(
        'index.html',
        repositories=repositories,
        languages=languages,
        dates=dates,
        search_query=search_query,
        selected_language=language,
        selected_date=date,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5001)    