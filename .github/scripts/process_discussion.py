import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime

# 配置
REPO_PATH = os.getenv('GITHUB_WORKSPACE', '.')
DISCUSSION_BODY = os.getenv('DISCUSSION_BODY', '')

# 文件夹路径
BLOG_DIR = Path(REPO_PATH) / 'Blog'
NOTICE_DIR = Path(REPO_PATH) / 'Notice'
LOG_DIR = Path(REPO_PATH) / 'Log'
BLOG_LIST_FILE = BLOG_DIR / 'Blist.json'
LOG_FILE = LOG_DIR / 'log.json'
NOTICE_FILE = NOTICE_DIR / 'Notice.md'

# 正则表达式
BLOG_PATTERN = r'^//w-([^@]+)@d-([^@]+)@n-([^@]+)//'
NOTICE_PATTERN = r'^//d-([^@]+)//'

# 操作代号
ACTION_BLOG_SUCCESS = "Update blog"
ACTION_BLOG_ERROR = "Blog error"
ACTION_NOTICE_SUCCESS = "Update Notice"
ACTION_NOTICE_ERROR = "Notice error"


def safe_load_json(filepath):
    """安全加载 JSON，任何错误都返回空列表"""
    if not filepath.exists():
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if not isinstance(data, list):
                return []
            return data
    except (json.JSONDecodeError, ValueError):
        return []


def check_folders():
    """检查必要文件夹是否存在"""
    missing = []
    if not BLOG_DIR.exists():
        missing.append('Blog')
    if not NOTICE_DIR.exists():
        missing.append('Notice')
    if not LOG_DIR.exists():
        missing.append('Log')
    
    if missing:
        error_msg = f"缺少必要文件夹: {', '.join(missing)}，工作流已中止"
        print(f"❌ {error_msg}")
        if LOG_DIR.exists():
            add_log(ACTION_BLOG_ERROR if 'Blog' in missing else ACTION_NOTICE_ERROR, 
                    f"缺少文件夹: {', '.join(missing)}")
        sys.exit(1)
    return True


def parse_and_process():
    """解析并处理讨论内容"""
    if not DISCUSSION_BODY:
        print("⚠️ 讨论内容为空，跳过处理")
        return
    
    body_lines = DISCUSSION_BODY.strip().split('\n')
    first_line = body_lines[0].strip() if body_lines else ''
    
    # 尝试匹配博客格式
    blog_match = re.match(BLOG_PATTERN, first_line)
    if blog_match:
        author = blog_match.group(1)
        date = blog_match.group(2)
        title = blog_match.group(3)
        content = '\n'.join(body_lines[1:]).strip()
        
        if not content:
            print("⚠️ 博客正文为空，记录错误日志")
            add_log(ACTION_BLOG_ERROR, "正文内容为空")
            return
        
        print(f"✅ 识别为博客格式: 作者={author}, 日期={date}, 标题={title}")
        process_blog(author, date, title, content)
        return
    
    # 尝试匹配公告格式
    notice_match = re.match(NOTICE_PATTERN, first_line)
    if notice_match:
        date = notice_match.group(1)
        content = '\n'.join(body_lines[1:]).strip()
        
        if not content:
            print("⚠️ 公告正文为空，记录错误日志")
            add_log(ACTION_NOTICE_ERROR, "正文内容为空")
            return
        
        print(f"✅ 识别为公告格式: 日期={date}")
        process_notice(date, content)
        return
    
    # 没有匹配任何格式 - 静默忽略
    print(f"❌ 未识别有效格式，忽略此消息")


def process_blog(author, date, title, content):
    """处理博客格式"""
    try:
        # 1. 创建 Markdown 文件
        safe_title = title.strip()
        filename = re.sub(r'[<>:"/\\|?*]', '_', safe_title) + '.md'
        filepath = BLOG_DIR / filename
        
        # 构建元数据 + 正文
        md_content = f"""---
author: {author}
date: {date}
title: {safe_title}
---

{content}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"📝 已创建博客文件: {filepath}")
        
        # 2. 修改 Blist.json
        blist_data = safe_load_json(BLOG_LIST_FILE)
        
        entry = {
            "title": safe_title,
            "author": author,
            "date": date,
            "filename": filename
        }
        
        # 避免重复
        existing = [e for e in blist_data if e.get('filename') == filename]
        if not existing:
            blist_data.append(entry)
            blist_data.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            with open(BLOG_LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(blist_data, f, ensure_ascii=False, indent=2)
            print(f"📋 已更新 Blist.json，当前共 {len(blist_data)} 篇文章")
        
        # 3. 添加成功日志
        add_log(ACTION_BLOG_SUCCESS, f"{safe_title} (作者: {author})")
        print(f"✅ 博客发布成功: {safe_title}")
        
    except Exception as e:
        error_msg = f"处理博客时出错: {str(e)}"
        print(f"❌ {error_msg}")
        add_log(ACTION_BLOG_ERROR, error_msg)


def process_notice(date, content):
    """处理公告格式"""
    try:
        # 1. 替换 Notice.md
        with open(NOTICE_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📢 已更新公告文件: {NOTICE_FILE}")
        
        # 2. 添加成功日志
        add_log(ACTION_NOTICE_SUCCESS, f"日期: {date}")
        print(f"✅ 公告更新成功: {date}")
        
    except Exception as e:
        error_msg = f"处理公告时出错: {str(e)}"
        print(f"❌ {error_msg}")
        add_log(ACTION_NOTICE_ERROR, error_msg)


def add_log(action, detail=""):
    """添加日志到 Log/log.json"""
    log_data = safe_load_json(LOG_FILE)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "detail": detail
    }
    
    log_data.append(log_entry)
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"📝 已添加日志: [{action}] {detail}")


if __name__ == "__main__":
    # 先检查文件夹
    check_folders()
    # 解析处理
    parse_and_process()
    
    # 输出标记（新版 GitHub Actions 语法）
    with open(os.getenv('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        print("changed=true", file=f)
