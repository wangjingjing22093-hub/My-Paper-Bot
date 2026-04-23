import arxiv
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
import time
import os

# ================= 1. 配置数据源 =================

SEARCH_QUERY = 'cat:math.CO'

RSS_FEEDS = {
    "Linear Algebra and its Applications (LAA)": "https://rss.sciencedirect.com/publication/science/00243795",
    "Journal of Combinatorial Theory, Series B (JCTB)": "https://rss.sciencedirect.com/publication/science/00958956",
    "Journal of Combinatorial Theory, Series A (JCTA)": "https://rss.sciencedirect.com/publication/science/00973165",
    "Discrete Mathematics (DM)": "https://rss.sciencedirect.com/publication/science/0012365X",
    "Discrete Applied Mathematics (DAM)": "https://rss.sciencedirect.com/publication/science/0166218X",
    "Journal of Graph Theory (JGT)": "https://onlinelibrary.wiley.com/feed/10970118/most-recent",
    "European Journal of Combinatorics (EJC)": "https://rss.sciencedirect.com/publication/science/01956698",
    "SIAM Journal on Discrete Mathematics (SIDMA)": "https://epubs.siam.org/action/showFeed?type=etoc&feed=rss&jc=sjdmec"
}

# ================= 2. 时间过滤器设置 =================
CUTOFF_DAYS = 2
cutoff_date = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)

# ================= 3. 抓取函数 =================

def fetch_arxiv_papers():
    client = arxiv.Client()
    search = arxiv.Search(
        query = SEARCH_QUERY,
        max_results = 50, 
        sort_by = arxiv.SortCriterion.SubmittedDate
    )
    papers = []
    for result in client.results(search):
        if result.published >= cutoff_date:
            papers.append({
                'source': 'arXiv (预印本)',
                'title': result.title,
                'authors': ', '.join(author.name for author in result.authors),
                'summary': result.summary.replace('\n', ' '),
                'link': result.entry_id
            })
    return papers

def fetch_journal_papers():
    papers = []
    for journal_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                published_time = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_time = entry.published_parsed
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_time = entry.updated_parsed
                
                if published_time:
                    entry_date = datetime.fromtimestamp(time.mktime(published_time), timezone.utc)
                    if entry_date < cutoff_date:
                        continue 
                
                papers.append({
                    'source': journal_name,
                    'title': entry.title,
                    'link': entry.link
                })
        except Exception as e:
            print(f"抓取 {journal_name} 时出错: {e}")
    return papers

# ================= 4. 邮件发送函数 =================

def send_email(arxiv_papers, journal_papers):
    if not arxiv_papers and not journal_papers:
        print("今天没有最近更新的论文，暂不发送邮件。")
        return

    SMTP_SERVER = "smtp.qq.com" 
    SMTP_PORT = 465
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
    SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
    RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    
    # 【修复点】：将 datetime.date.today() 替换为了 datetime.now().date()
    msg['Subject'] = f"📚 图论文献速递 (去重版) - {datetime.now().date()}"

    html_content = f"<h2>📅 {datetime.now().date()} 学术速递 (去重版)</h2>"
    html_content += f"<p><em>*此版本已开启时间过滤，只为您推送最近 {CUTOFF_DAYS} 天内的新增内容。</em></p>"

    if journal_papers:
        html_content += "<h3>🌟 顶级与权威期刊最新发表</h3><ul>"
        for p in journal_papers:
            html_content += f"<li style='margin-bottom: 8px;'><strong>[{p['source']}]</strong> <a href='{p['link']}'>{p['title']}</a></li>"
        html_content += "</ul><hr>"

    if arxiv_papers:
        html_content += "<h3>🚀 arXiv 最新预印本</h3>"
        for idx, p in enumerate(arxiv_papers, 1):
            html_content += f"""
            <h4>{idx}. <a href="{p['link']}">{p['title']}</a></h4>
            <p><strong>作者:</strong> {p['authors']}</p>
            <p style="color: #555; font-size: 14px;"><strong>摘要:</strong> {p['summary']}</p>
            """
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    print("开始抓取 arXiv 预印本...")
    arxiv_results = fetch_arxiv_papers()
    
    print("开始抓取各大期刊 RSS 源...")
    journal_results = fetch_journal_papers()
    
    print(f"经过时间过滤，共抓取到 {len(arxiv_results)} 篇近期 arXiv 文章，{len(journal_results)} 篇近期期刊文章，准备发送...")
    send_email(arxiv_results, journal_results)
