import arxiv
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import os

# ================= 1. 配置数据源 =================

# arXiv 关键词检索 (保留原有的极值图论、图谱理论等关键词)
SEARCH_QUERY = 'cat:math.CO AND (all:"extremal graph" OR all:"spectral graph" OR all:"spectral radius" OR all:"Turan")'

# 正式期刊的 RSS 订阅源 (为你精选并寻找了核心期刊的真实链接)
RSS_FEEDS = {
    "Linear Algebra and its Applications (LAA)": "https://rss.sciencedirect.com/publication/science/00243795",
    "Journal of Combinatorial Theory, Series B (JCTB)": "https://rss.sciencedirect.com/publication/science/00958956",
    "Discrete Mathematics (DM)": "https://rss.sciencedirect.com/publication/science/0012365X",
    "Discrete Applied Mathematics (DAM)": "https://rss.sciencedirect.com/publication/science/0166218X",
    "Journal of Graph Theory (JGT)": "https://onlinelibrary.wiley.com/feed/10970118/most-recent",
    "European Journal of Combinatorics (EJC)": "https://rss.sciencedirect.com/publication/science/01956698"
}

# ================= 2. 抓取函数 =================

def fetch_arxiv_papers():
    """抓取 arXiv 的预印本论文"""
    client = arxiv.Client()
    search = arxiv.Search(
        query = SEARCH_QUERY,
        max_results = 5, # 每天最多看5篇最新的 arXiv
        sort_by = arxiv.SortCriterion.SubmittedDate
    )
    papers = []
    for result in client.results(search):
        papers.append({
            'source': 'arXiv (预印本)',
            'title': result.title,
            'authors': ', '.join(author.name for author in result.authors),
            'summary': result.summary.replace('\n', ' '),
            'link': result.entry_id
        })
    return papers

def fetch_journal_papers():
    """抓取正式期刊的最新发表论文"""
    papers = []
    for journal_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            # 每个期刊每次只取最新更新的 2 篇文章，防止邮箱塞满
            for entry in feed.entries[:2]:
                papers.append({
                    'source': journal_name,
                    'title': entry.title,
                    'link': entry.link
                })
        except Exception as e:
            print(f"抓取 {journal_name} 时出错: {e}")
    return papers

# ================= 3. 邮件发送函数 =================

def send_email(arxiv_papers, journal_papers):
    if not arxiv_papers and not journal_papers:
        print("今天没有任何新论文。")
        return

    # 从 GitHub Secrets 中安全读取邮箱信息
    SMTP_SERVER = "smtp.qq.com"  # 如果用163请改为 smtp.163.com
    SMTP_PORT = 465
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
    SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
    RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"📚 图论与图谱理论 每日文献速递 - {datetime.date.today()}"

    # 构造 HTML 邮件内容
    html_content = f"<h2>📅 {datetime.date.today()} 学术速递</h2>"

    # 模块 A：正式期刊部分
    if journal_papers:
        html_content += "<h3>🌟 顶级与权威期刊最新发表</h3><ul>"
        for p in journal_papers:
            html_content += f"<li><strong>[{p['source']}]</strong> <a href='{p['link']}'>{p['title']}</a></li>"
        html_content += "</ul><hr>"

    # 模块 B：arXiv 预印本部分
    if arxiv_papers:
        html_content += "<h3>🚀 arXiv 最新预印本 (数学/组合)</h3>"
        for idx, p in enumerate(arxiv_papers, 1):
            html_content += f"""
            <h4>{idx}. <a href="{p['link']}">{p['title']}</a></h4>
            <p><strong>作者:</strong> {p['authors']}</p>
            <p style="color: #555; font-size: 14px;"><strong>摘要:</strong> {p['summary']}</p>
            """
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    # 发送邮件
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

# ================= 4. 主程序运行 =================
if __name__ == "__main__":
    print("开始抓取 arXiv 预印本...")
    arxiv_results = fetch_arxiv_papers()
    
    print("开始抓取各大期刊 RSS 源...")
    journal_results = fetch_journal_papers()
    
    print(f"共抓取到 {len(arxiv_results)} 篇 arXiv 文章，{len(journal_results)} 篇期刊文章，准备发送...")
    send_email(arxiv_results, journal_results)
