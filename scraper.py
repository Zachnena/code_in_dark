import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
import json
from datetime import datetime
import webbrowser
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Target URL
base_url = "https://qa1parts.cat.com/en/catcorp"

# Headers to mimic a browser visit
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Global tracking variables
visited_urls = set()
all_broken_links = []
all_missing_images = []
all_pages_checked = 0
max_pages_to_check = 5  # Limit to prevent infinite crawling

def check_url(url):
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        return response.status_code == 200
    except requests.RequestException:
        return False

def should_crawl_url(url):
    """Determine if we should crawl this URL"""
    # Only crawl URLs from the same domain
    if not url.startswith(base_url.split('/')[0] + '//' + base_url.split('/')[2]):
        return False
    
    # Skip certain file types
    skip_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.doc', '.docx', '.xls', '.xlsx']
    if any(url.lower().endswith(ext) for ext in skip_extensions):
        return False
    
    # Skip already visited URLs
    if url in visited_urls:
        return False
    
    # Skip external links, mailto, tel, etc.
    if url.startswith(('mailto:', 'tel:', 'javascript:', '#')):
        return False
        
    return True

def scrape_page_for_errors(url, depth=0):
    """Scrape a single page for errors"""
    global all_broken_links, all_missing_images, all_pages_checked
    
    if all_pages_checked >= max_pages_to_check:
        return [], []
    
    try:
        print(f"{'  ' * depth}📄 Accessing {url}...")
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        print(f"{'  ' * depth}✅ Successfully accessed!")
        visited_urls.add(url)
        all_pages_checked += 1
    except requests.RequestException as e:
        print(f"{'  ' * depth}❌ Failed to access {url}: {e}")
        return [], []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    page_broken_links = []
    page_missing_images = []
    links_to_crawl = []

    # Find all links on this page
    links = soup.find_all('a', href=True)
    print(f"{'  ' * depth}🔗 Found {len(links)} links on this page")
    
    for i, link in enumerate(links):
        full_url = urljoin(url, link['href'])
        
        # Check if link is working
        if not check_url(full_url):
            page_broken_links.append(full_url)
            print(f"{'  ' * depth}  ❌ BROKEN LINK: {full_url}")
        else:
            # If link is working and we should crawl it, add to crawl list
            if should_crawl_url(full_url) and depth < 2:  # Limit depth to prevent infinite crawling
                links_to_crawl.append(full_url)

    # Find all images on this page
    images = soup.find_all('img', src=True)
    print(f"{'  ' * depth}🖼️ Found {len(images)} images on this page")
    
    for i, img in enumerate(images):
        full_url = urljoin(url, img['src'])
        if not check_url(full_url):
            page_missing_images.append(full_url)
            print(f"{'  ' * depth}  ❌ MISSING IMAGE: {full_url}")

    # Add to global lists
    all_broken_links.extend(page_broken_links)
    all_missing_images.extend(page_missing_images)
    
    # Recursively crawl other pages (limit to first few to prevent overwhelming)
    crawl_limit = min(3, len(links_to_crawl))  # Only crawl first 3 links from each page
    for i in range(crawl_limit):
        if all_pages_checked >= max_pages_to_check:
            break
        link_url = links_to_crawl[i]
        print(f"{'  ' * depth}🔍 Crawling deeper: {link_url}")
        scrape_page_for_errors(link_url, depth + 1)
    
    return page_broken_links, page_missing_images
def scrape_for_errors(url):
    """Main scraping function that orchestrates the crawling"""
    global all_broken_links, all_missing_images, all_pages_checked, visited_urls
    
    # Reset global variables
    all_broken_links = []
    all_missing_images = []
    all_pages_checked = 0
    visited_urls = set()
    
    print(f"🚀 Starting comprehensive website scan...")
    print(f"📊 Will check up to {max_pages_to_check} pages for errors")
    print(f"{'='*60}")
    
    # Start the recursive crawling
    scrape_page_for_errors(url, 0)
    
    # Count total links and images found across all pages
    total_links_found = 0
    total_images_found = 0
    
    for visited_url in visited_urls:
        try:
            response = requests.get(visited_url, headers=headers, timeout=5, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            total_links_found += len(soup.find_all('a', href=True))
            total_images_found += len(soup.find_all('img', src=True))
        except:
            continue
    
    # Generate and open dashboard
    print(f"\n{'='*60}")
    print("🎨 GENERATING COMPREHENSIVE DASHBOARD...")
    print(f"{'='*60}")
    
    dashboard_file = generate_dashboard(
        url, 
        list(set(all_broken_links)),  # Remove duplicates
        list(set(all_missing_images)),  # Remove duplicates
        total_links_found, 
        total_images_found
    )
    print(f"📋 Dashboard generated: {dashboard_file}")
    
    # Open dashboard in browser
    webbrowser.open(f'file://{dashboard_file}')
    print("🌐 Dashboard opened in your default browser!")
    
    # Print comprehensive summary
    print(f"\n📊 COMPREHENSIVE SCAN SUMMARY:")
    print(f"{'='*60}")
    print(f"🔍 Pages Scanned: {len(visited_urls)}")
    print(f"🔗 Total Links Found: {total_links_found}")
    print(f"❌ Broken Links: {len(set(all_broken_links))}")
    print(f"🖼️ Total Images Found: {total_images_found}")
    print(f"❌ Missing Images: {len(set(all_missing_images))}")
    print(f"{'='*60}")
    
    # Show which pages were scanned
    print(f"\n📄 Pages Scanned:")
    for i, page in enumerate(visited_urls, 1):
        print(f"  {i}. {page}")
    
    return list(set(all_broken_links)), list(set(all_missing_images))

def generate_dashboard(url, broken_links, missing_images, total_links, total_images):
    """Generate an HTML dashboard with the scraping results"""
    
    # Calculate stats
    working_links = total_links - len(broken_links)
    working_images = total_images - len(missing_images)
    
    # Create pages scanned section
    pages_scanned_html = ""
    for i, page in enumerate(visited_urls, 1):
        pages_scanned_html += f'<div class="page-item">📄 {page}</div>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Comprehensive Website Scraper Dashboard</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            
            .header p {{
                font-size: 1.2em;
                opacity: 0.9;
            }}
            
            .scan-info {{
                background: #34495e;
                color: white;
                padding: 20px;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                text-align: center;
            }}
            
            .scan-stat {{
                background: rgba(255,255,255,0.1);
                padding: 15px;
                border-radius: 8px;
            }}
            
            .scan-stat-number {{
                font-size: 2em;
                font-weight: bold;
                color: #3498db;
            }}
            
            .scan-stat-label {{
                font-size: 0.9em;
                margin-top: 5px;
                opacity: 0.8;
            }}
            
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                padding: 30px;
                background: #f8f9fa;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 10px;
                padding: 25px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-number {{
                font-size: 3em;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            
            .stat-label {{
                font-size: 1.1em;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .success {{ color: #27ae60; }}
            .error {{ color: #e74c3c; }}
            .info {{ color: #3498db; }}
            
            .results {{
                padding: 30px;
            }}
            
            .section {{
                margin-bottom: 40px;
            }}
            
            .section h2 {{
                font-size: 1.8em;
                margin-bottom: 20px;
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            
            .pages-scanned {{
                background: #e8f4f8;
                border: 1px solid #b8daff;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
            }}
            
            .page-item {{
                background: white;
                border-left: 4px solid #3498db;
                padding: 10px;
                margin-bottom: 8px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                font-family: monospace;
                font-size: 0.9em;
            }}
            
            .page-item:last-child {{
                margin-bottom: 0;
            }}
            
            .error-list {{
                background: #fff5f5;
                border: 1px solid #fed7d7;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            
            .error-item {{
                background: white;
                border-left: 4px solid #e74c3c;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            
            .error-item:last-child {{
                margin-bottom: 0;
            }}
            
            .error-url {{
                word-break: break-all;
                font-family: monospace;
                font-size: 0.9em;
                color: #e74c3c;
            }}
            
            .no-errors {{
                background: #f0fff4;
                border: 1px solid #9ae6b4;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                color: #27ae60;
                font-size: 1.1em;
            }}
            
            .timestamp {{
                text-align: center;
                color: #666;
                font-size: 0.9em;
                padding: 20px;
                border-top: 1px solid #eee;
            }}
            
            .progress-bar {{
                background: #ecf0f1;
                border-radius: 10px;
                height: 20px;
                margin-top: 10px;
                overflow: hidden;
            }}
            
            .progress-fill {{
                height: 100%;
                transition: width 0.3s ease;
            }}
            
            .progress-success {{
                background: linear-gradient(90deg, #27ae60, #2ecc71);
            }}
            
            .progress-error {{
                background: linear-gradient(90deg, #e74c3c, #c0392b);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 Comprehensive Website Scraper Dashboard</h1>
                <p>Multi-page scan results for: <strong>{url}</strong></p>
            </div>
            
            <div class="scan-info">
                <div class="scan-stat">
                    <div class="scan-stat-number">{len(visited_urls)}</div>
                    <div class="scan-stat-label">Pages Scanned</div>
                </div>
                <div class="scan-stat">
                    <div class="scan-stat-number">{total_links}</div>
                    <div class="scan-stat-label">Total Links Found</div>
                </div>
                <div class="scan-stat">
                    <div class="scan-stat-number">{total_images}</div>
                    <div class="scan-stat-label">Total Images Found</div>
                </div>
                <div class="scan-stat">
                    <div class="scan-stat-number">{len(broken_links) + len(missing_images)}</div>
                    <div class="scan-stat-label">Total Errors Found</div>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number success">{working_links}</div>
                    <div class="stat-label">Working Links</div>
                    <div class="progress-bar">
                        <div class="progress-fill progress-success" style="width: {(working_links/total_links*100) if total_links > 0 else 0:.1f}%"></div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number error">{len(broken_links)}</div>
                    <div class="stat-label">Broken Links</div>
                    <div class="progress-bar">
                        <div class="progress-fill progress-error" style="width: {(len(broken_links)/total_links*100) if total_links > 0 else 0:.1f}%"></div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number success">{working_images}</div>
                    <div class="stat-label">Working Images</div>
                    <div class="progress-bar">
                        <div class="progress-fill progress-success" style="width: {(working_images/total_images*100) if total_images > 0 else 0:.1f}%"></div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number error">{len(missing_images)}</div>
                    <div class="stat-label">Missing Images</div>
                    <div class="progress-bar">
                        <div class="progress-fill progress-error" style="width: {(len(missing_images)/total_images*100) if total_images > 0 else 0:.1f}%"></div>
                    </div>
                </div>
            </div>
            
            <div class="results">
                <div class="section">
                    <h2>� Pages Scanned ({len(visited_urls)})</h2>
                    <div class="pages-scanned">
                        {pages_scanned_html}
                    </div>
                </div>
                
                <div class="section">
                    <h2>�🔗 Broken Links ({len(broken_links)})</h2>
                    {generate_error_section(broken_links, "No broken links found across all pages! 🎉")}
                </div>
                
                <div class="section">
                    <h2>🖼️ Missing Images ({len(missing_images)})</h2>
                    {generate_error_section(missing_images, "No missing images found across all pages! 🎉")}
                </div>
            </div>
            
            <div class="timestamp">
                Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Comprehensive multi-page scan completed
            </div>
        </div>
    </body>
    </html>
    """
    
    # Write HTML file
    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return os.path.abspath('dashboard.html')

def generate_error_section(errors, no_error_message):
    """Generate HTML for error sections"""
    if not errors:
        return f'<div class="no-errors">{no_error_message}</div>'
    
    html = '<div class="error-list">'
    for error in errors:
        html += f'''
        <div class="error-item">
            <div class="error-url">{error}</div>
        </div>
        '''
    html += '</div>'
    return html

# Run the scraper
scrape_for_errors(base_url)
