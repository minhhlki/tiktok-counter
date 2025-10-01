#!/usr/bin/env python3
"""
TikTok Channel Total Views Counter - IMPROVED VERSION
Cải thiện độ chính xác khi parse view count
"""

import asyncio
import json
import re
from typing import Dict, List, Optional
from playwright.async_api import async_playwright
import argparse
from datetime import datetime

class TikTokViewCounter:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.total_views = 0
        self.videos_data = []
        
    def parse_view_count(self, view_str: str) -> int:
        """
        Chuyển đổi string view count thành số - IMPROVED VERSION
        Cải thiện: Làm tròn đúng cách để giảm sai số
        
        Ví dụ: "1.2M" -> 1200000, "523K" -> 523000
        """
        if not view_str:
            return 0
            
        view_str = view_str.strip().upper()
        
        # Xử lý các trường hợp đặc biệt
        multipliers = {
            'K': 1000,
            'M': 1000000,
            'B': 1000000000
        }
        
        # Tìm và xử lý số với ký tự viết tắt
        for suffix, multiplier in multipliers.items():
            if suffix in view_str:
                try:
                    # Lấy phần số trước ký tự
                    num_str = view_str.replace(suffix, '').strip()
                    # Chuyển đổi và nhân với hệ số
                    # IMPROVEMENT: Sử dụng round() thay vì int() để làm tròn đúng
                    return round(float(num_str) * multiplier)
                except:
                    continue
        
        # Nếu không có ký tự viết tắt, cố gắng parse số trực tiếp
        try:
            # Loại bỏ các ký tự không phải số (như dấu phẩy)
            clean_str = re.sub(r'[^\d]', '', view_str)
            return int(clean_str) if clean_str else 0
        except:
            return 0
    
    async def get_exact_view_count(self, video_elem) -> tuple:
        """
        Lấy view count chính xác nhất có thể từ nhiều nguồn
        Returns: (view_count, view_text, source)
        """
        view_count = 0
        view_text = "0"
        source = "unknown"
        
        # Chiến lược 1: Tìm trong data attributes (chính xác nhất)
        try:
            # Thử lấy từ aria-label hoặc title (có thể chứa số đầy đủ)
            aria_label = await video_elem.get_attribute('aria-label')
            if aria_label and 'view' in aria_label.lower():
                # Extract số từ aria-label: "5234 views" -> 5234
                numbers = re.findall(r'(\d[\d,]*)\s*view', aria_label, re.IGNORECASE)
                if numbers:
                    clean_num = numbers[0].replace(',', '')
                    view_count = int(clean_num)
                    view_text = numbers[0]
                    source = "aria-label"
                    return (view_count, view_text, source)
        except:
            pass
        
        # Chiến lược 2: Tìm strong element với data attributes
        try:
            view_elem = video_elem.locator('strong[data-e2e="video-views"]').first
            if await view_elem.count() > 0:
                # Thử lấy title attribute
                title = await view_elem.get_attribute('title')
                if title:
                    clean_num = re.sub(r'[^\d]', '', title)
                    if clean_num:
                        view_count = int(clean_num)
                        view_text = title
                        source = "title-attribute"
                        return (view_count, view_text, source)
        except:
            pass
        
        # Chiến lược 3: Parse từ text (ít chính xác nhất - có làm tròn)
        view_selectors = [
            'strong[data-e2e="video-views"]',
            'strong',
            '[data-e2e="video-views"]',
            '.video-count',
            'span[title*="views"]'
        ]
        
        for view_selector in view_selectors:
            try:
                view_elem = video_elem.locator(view_selector)
                if await view_elem.count() > 0:
                    # Thử lấy title trước
                    elem = view_elem.first
                    title = await elem.get_attribute('title')
                    if title and title.strip():
                        clean_num = re.sub(r'[^\d]', '', title)
                        if clean_num:
                            view_count = int(clean_num)
                            view_text = title
                            source = f"title-{view_selector}"
                            return (view_count, view_text, source)
                    
                    # Nếu không có title, lấy text
                    text = await elem.text_content()
                    if text and text.strip():
                        view_text = text.strip()
                        view_count = self.parse_view_count(view_text)
                        source = f"text-{view_selector}"
                        return (view_count, view_text, source)
            except:
                continue
        
        return (view_count, view_text, source)
    
    async def scrape_channel(self, channel_url: str) -> Dict:
        """
        Scrape thông tin và tổng view từ kênh TikTok
        """
        async with async_playwright() as p:
            # Khởi tạo browser với các options để tránh detection
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            # Tạo context với user agent thực
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            try:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang truy cập: {channel_url}")
                
                # Navigate với timeout dài hơn
                await page.goto(channel_url, wait_until='networkidle', timeout=60000)
                
                # Đợi content load
                await page.wait_for_timeout(5000)
                
                # Scroll để load thêm video
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang tải danh sách video...")
                
                previous_height = 0
                scroll_attempts = 0
                max_scrolls = 15
                
                while scroll_attempts < max_scrolls:
                    # Scroll xuống cuối trang
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(3000)
                    
                    # Kiểm tra chiều cao mới
                    current_height = await page.evaluate('document.body.scrollHeight')
                    
                    if current_height == previous_height:
                        scroll_attempts += 1
                        if scroll_attempts >= 3:
                            break
                    else:
                        scroll_attempts = 0
                        previous_height = current_height
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scroll {scroll_attempts + 1}/{max_scrolls}")
                
                # Lấy thông tin channel
                try:
                    channel_name = await page.locator('h1[data-e2e="user-title"]').text_content()
                except Exception:
                    try:
                        channel_name = await page.locator('h2[data-e2e="user-subtitle"]').text_content()
                    except Exception:
                        channel_name = "Unknown"
                
                # Tìm tất cả video items
                video_selectors = [
                    '[data-e2e="user-post-item"]',
                    '[data-e2e="user-post-item-list"] > div',
                    '.video-feed-item',
                    'div[data-e2e="user-post-item-list"] div'
                ]
                
                video_elements = []
                for selector in video_selectors:
                    try:
                        elements = await page.locator(selector).all()
                        if elements:
                            video_elements = elements
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sử dụng selector: {selector}")
                            break
                    except:
                        continue
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Tìm thấy {len(video_elements)} video")
                
                if not video_elements:
                    print("[WARNING] Không tìm thấy video nào. Có thể cần cập nhật selector hoặc page chưa load đủ.")
                
                # Extract thông tin từ mỗi video
                for i, video_elem in enumerate(video_elements, 1):
                    try:
                        # IMPROVED: Sử dụng hàm get_exact_view_count mới
                        views, view_text, source = await self.get_exact_view_count(video_elem)
                        
                        # Lấy link video
                        try:
                            link_elem = video_elem.locator('a').first
                            video_link = await link_elem.get_attribute('href') if await video_elem.locator('a').count() > 0 else ""
                            if video_link and not video_link.startswith('http'):
                                video_link = f"https://www.tiktok.com{video_link}"
                        except:
                            video_link = ""
                        
                        # Lấy caption/description
                        try:
                            caption_selectors = [
                                '[data-e2e="user-post-item-desc"]',
                                '.video-meta-caption',
                                'div[data-e2e="user-post-item-desc"]'
                            ]
                            caption = ""
                            for cap_selector in caption_selectors:
                                try:
                                    caption_elem = video_elem.locator(cap_selector)
                                    if await caption_elem.count() > 0:
                                        caption = await caption_elem.first.text_content()
                                        if caption:
                                            break
                                except:
                                    continue
                        except:
                            caption = ""
                        
                        video_info = {
                            'index': i,
                            'views': views,
                            'view_text': view_text,
                            'source': source,  # IMPROVED: Ghi lại nguồn data
                            'link': video_link,
                            'caption': caption[:100] if caption else ""
                        }
                        
                        self.videos_data.append(video_info)
                        self.total_views += views
                        
                        # In progress với thông tin nguồn
                        if i % 10 == 0 or views > 0:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Video {i}: {view_text} views (source: {source})")
                        
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Lỗi khi xử lý video {i}: {str(e)}")
                        continue
                
                # Tạo kết quả
                result = {
                    'channel_url': channel_url,
                    'channel_name': channel_name,
                    'total_videos': len(self.videos_data),
                    'total_views': self.total_views,
                    'total_views_formatted': self.format_number(self.total_views),
                    'average_views': self.total_views // len(self.videos_data) if self.videos_data else 0,
                    'videos': self.videos_data,
                    'scraped_at': datetime.now().isoformat()
                }
                
                return result
                
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Lỗi khi scrape: {str(e)}")
                return {
                    'error': str(e),
                    'channel_url': channel_url,
                    'scraped_at': datetime.now().isoformat()
                }
                
            finally:
                await browser.close()
    
    def format_number(self, num: int) -> str:
        """
        Format số cho dễ đọc
        """
        if num >= 1000000000:
            return f"{num/1000000000:.2f}B"
        elif num >= 1000000:
            return f"{num/1000000:.2f}M"
        elif num >= 1000:
            return f"{num/1000:.2f}K"
        else:
            return str(num)
    
    def print_report(self, data: Dict):
        """
        In báo cáo kết quả
        """
        print("\n" + "="*60)
        print("📊 BÁO CÁO TỔNG VIEW KÊNH TIKTOK - IMPROVED")
        print("="*60)
        
        if 'error' in data:
            print(f"❌ Lỗi: {data['error']}")
            return
        
        print(f"📱 Kênh: {data['channel_name']}")
        print(f"🔗 URL: {data['channel_url']}")
        print(f"📹 Tổng số video: {data['total_videos']}")
        print(f"👁️ TỔNG LƯỢT XEM: {data['total_views_formatted']} ({data['total_views']:,} views)")
        
        if data['total_videos'] > 0:
            print(f"📈 Trung bình/video: {self.format_number(data['average_views'])}")
        
        print(f"🕐 Thời gian scrape: {data['scraped_at']}")
        
        # Thống kê nguồn dữ liệu
        if data['videos']:
            sources = {}
            for video in data['videos']:
                src = video.get('source', 'unknown')
                sources[src] = sources.get(src, 0) + 1
            
            print(f"\n📊 NGUỒN DỮ LIỆU:")
            for src, count in sources.items():
                print(f"  - {src}: {count} videos")
            
            # Lọc video có views > 0
            videos_with_views = [v for v in data['videos'] if v['views'] > 0]
            print(f"\n📌 VIDEO CÓ VIEW DATA: {len(videos_with_views)}/{len(data['videos'])}")
            print("-"*60)
            
            if videos_with_views:
                # Sắp xếp theo views
                sorted_videos = sorted(videos_with_views, key=lambda x: x['views'], reverse=True)
                for i, video in enumerate(sorted_videos[:10], 1):
                    print(f"{i}. {self.format_number(video['views'])} views ({video['view_text']}) [src: {video['source']}]")
                    if video['caption']:
                        print(f"   Caption: {video['caption'][:70]}...")
                    if video['link']:
                        print(f"   Link: {video['link']}")
                    print()
        
        print("="*60)
    
    async def save_to_file(self, data: Dict, filename: str = None):
        """
        Lưu kết quả vào file JSON
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            channel_name = data.get('channel_name', 'unknown').replace('@', '').replace('/', '_')
            filename = f"tiktok_views_{channel_name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Đã lưu kết quả vào: {filename}")

async def main():
    parser = argparse.ArgumentParser(description='TikTok Channel Views Counter - IMPROVED')
    parser.add_argument('url', nargs='?', default='https://www.tiktok.com/@huongzang007',
                       help='TikTok channel URL')
    parser.add_argument('--headless', action='store_false', default=True,
                       help='Run browser in non-headless mode (show browser window)')
    parser.add_argument('--save', action='store_true',
                       help='Save results to JSON file')
    
    args = parser.parse_args()
    
    print(f"🚀 Bắt đầu scrape kênh: {args.url}")
    print(f"🖥️ Chế độ headless: {args.headless}")
    
    # Khởi tạo counter
    counter = TikTokViewCounter(headless=args.headless)
    
    # Scrape channel
    result = await counter.scrape_channel(args.url)
    
    # In báo cáo
    counter.print_report(result)
    
    # Lưu file nếu cần
    if args.save:
        await counter.save_to_file(result)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════╗
║  TIKTOK CHANNEL VIEWS COUNTER IMPROVED   ║
║         Phiên bản: 1.0.2                 ║
║      CẢI THIỆN ĐỘ CHÍNH XÁC VIEW         ║
╚══════════════════════════════════════════╝
    """)
    
    asyncio.run(main())

