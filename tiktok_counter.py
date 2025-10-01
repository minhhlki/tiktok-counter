#!/usr/bin/env python3
"""
TikTok Channel Statistics Analyzer
Phân tích toàn diện thông số kênh TikTok: views, likes, followers, engagement rate
"""

import asyncio
import json
import re
import csv
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import argparse
from datetime import datetime
from pathlib import Path

class TikTokStatsAnalyzer:
    def __init__(self, headless: bool = True, max_scrolls: int = 20):
        self.headless = headless
        self.max_scrolls = max_scrolls
        self.total_views = 0
        self.total_likes = 0
        self.total_comments = 0
        self.total_shares = 0
        self.videos_data = []
        self.channel_info = {}
        
    def parse_count(self, count_str: str) -> int:
        """
        Chuyển đổi string count thành số
        Ví dụ: "1.2M" -> 1200000, "523K" -> 523000, "1.5B" -> 1500000000
        """
        if not count_str:
            return 0
            
        count_str = count_str.strip().upper()
        
        # Xử lý các trường hợp đặc biệt
        multipliers = {
            'K': 1000,
            'M': 1000000,
            'B': 1000000000,
            'T': 1000000000000
        }
        
        # Tìm và xử lý số với ký tự viết tắt
        for suffix, multiplier in multipliers.items():
            if suffix in count_str:
                try:
                    # Lấy phần số trước ký tự
                    num_str = count_str.replace(suffix, '').strip()
                    # Chuyển đổi và nhân với hệ số
                    return int(float(num_str) * multiplier)
                except:
                    continue
        
        # Nếu không có ký tự viết tắt, cố gắng parse số trực tiếp
        try:
            # Loại bỏ các ký tự không phải số (như dấu phẩy)
            clean_str = re.sub(r'[^\d]', '', count_str)
            return int(clean_str) if clean_str else 0
        except:
            return 0
    
    def parse_view_count(self, view_str: str) -> int:
        """Backward compatibility"""
        return self.parse_count(view_str)
    
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
                
                while scroll_attempts < self.max_scrolls:
                    # Scroll xuống cuối trang
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(3000)  # Đợi content load
                    
                    # Kiểm tra chiều cao mới
                    current_height = await page.evaluate('document.body.scrollHeight')
                    
                    if current_height == previous_height:
                        scroll_attempts += 1
                        if scroll_attempts >= 3:  # Sau 3 lần không có content mới thì dừng
                            break
                    else:
                        scroll_attempts = 0
                        previous_height = current_height
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scroll {scroll_attempts + 1}/{self.max_scrolls}")
                
                # Lấy thông tin channel chi tiết
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang lấy thông tin kênh...")
                
                # Tên kênh
                try:
                    channel_name = await page.locator('h1[data-e2e="user-title"]').text_content()
                except Exception:
                    try:
                        channel_name = await page.locator('h2[data-e2e="user-subtitle"]').text_content()
                    except Exception:
                        channel_name = "Unknown"
                
                # Username/handle
                try:
                    username = await page.locator('h2[data-e2e="user-subtitle"]').text_content()
                except Exception:
                    username = ""
                
                # Bio/Description
                try:
                    bio = await page.locator('h2[data-e2e="user-bio"]').text_content()
                except Exception:
                    bio = ""
                
                # Followers, Following, Likes
                channel_stats = {'followers': 0, 'following': 0, 'channel_likes': 0}
                try:
                    stats_elements = await page.locator('[data-e2e="following-count"], [data-e2e="followers-count"], [data-e2e="likes-count"]').all()
                    for elem in stats_elements:
                        try:
                            stat_text = await elem.text_content()
                            stat_type = await elem.get_attribute('data-e2e')
                            
                            if stat_type == 'followers-count':
                                channel_stats['followers'] = self.parse_count(stat_text)
                            elif stat_type == 'following-count':
                                channel_stats['following'] = self.parse_count(stat_text)
                            elif stat_type == 'likes-count':
                                channel_stats['channel_likes'] = self.parse_count(stat_text)
                        except:
                            continue
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Không lấy được stats kênh: {str(e)}")
                
                self.channel_info = {
                    'name': channel_name,
                    'username': username,
                    'bio': bio,
                    **channel_stats
                }
                
                # Tìm tất cả video items - thử nhiều selector
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
                        # Tìm view count - thử nhiều selector khác nhau
                        view_selectors = [
                            'strong[data-e2e="video-views"]',
                            'strong',
                            '[data-e2e="video-views"]',
                            '.video-count',
                            'span[title*="views"]'
                        ]
                        
                        view_text = "0"
                        for view_selector in view_selectors:
                            try:
                                view_elem = video_elem.locator(view_selector)
                                if await view_elem.count() > 0:
                                    view_text = await view_elem.first.text_content()
                                    if view_text and view_text.strip():
                                        break
                            except:
                                continue
                        
                        # Parse view count
                        views = self.parse_count(view_text)
                        
                        # Lấy likes, comments, shares (nếu có)
                        likes = 0
                        comments = 0
                        shares = 0
                        
                        # Note: TikTok thường không hiển thị likes/comments/shares ở channel page
                        # Chỉ hiển thị views. Để lấy full stats cần vào từng video riêng
                        
                        # Lấy link video nếu có
                        try:
                            link_elem = video_elem.locator('a').first
                            video_link = await link_elem.get_attribute('href') if await video_elem.locator('a').count() > 0 else ""
                            if video_link and not video_link.startswith('http'):
                                video_link = f"https://www.tiktok.com{video_link}"
                        except:
                            video_link = ""
                        
                        # Lấy caption/description nếu có
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
                            'view_text': view_text.strip() if view_text else "0",
                            'likes': likes,
                            'comments': comments,
                            'shares': shares,
                            'link': video_link,
                            'caption': caption[:100] if caption else ""  # Giới hạn 100 ký tự
                        }
                        
                        self.videos_data.append(video_info)
                        self.total_views += views
                        self.total_likes += likes
                        self.total_comments += comments
                        self.total_shares += shares
                        
                        # In progress
                        if i % 10 == 0 or views > 0:  # Hiển thị khi có views hoặc mỗi 10 video
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Video {i}: {view_text} views")
                        
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Lỗi khi xử lý video {i}: {str(e)}")
                        continue
                
                # Tính toán engagement rate (nếu có đủ data)
                engagement_rate = 0
                if self.channel_info.get('followers', 0) > 0 and self.total_views > 0:
                    # Engagement rate = (Total interactions / (Followers * Videos)) * 100
                    total_interactions = self.total_likes + self.total_comments + self.total_shares
                    if total_interactions > 0:
                        engagement_rate = (total_interactions / (self.channel_info['followers'] * len(self.videos_data))) * 100
                
                # Tạo kết quả chi tiết
                result = {
                    'channel_url': channel_url,
                    'channel_info': self.channel_info,
                    'statistics': {
                        'total_videos': len(self.videos_data),
                        'total_views': self.total_views,
                        'total_views_formatted': self.format_number(self.total_views),
                        'total_likes': self.total_likes,
                        'total_likes_formatted': self.format_number(self.total_likes),
                        'total_comments': self.total_comments,
                        'total_comments_formatted': self.format_number(self.total_comments),
                        'total_shares': self.total_shares,
                        'total_shares_formatted': self.format_number(self.total_shares),
                        'average_views': self.total_views // len(self.videos_data) if self.videos_data else 0,
                        'engagement_rate': round(engagement_rate, 2)
                    },
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
        In báo cáo kết quả chi tiết
        """
        print("\n" + "="*70)
        print("📊 BÁO CÁO PHÂN TÍCH KÊNH TIKTOK")
        print("="*70)
        
        if 'error' in data:
            print(f"❌ Lỗi: {data['error']}")
            return
        
        channel_info = data.get('channel_info', {})
        stats = data.get('statistics', {})
        
        # Thông tin kênh
        print(f"\n🎯 THÔNG TIN KÊNH:")
        print(f"  📱 Tên: {channel_info.get('name', 'N/A')}")
        print(f"  👤 Username: {channel_info.get('username', 'N/A')}")
        if channel_info.get('bio'):
            print(f"  📝 Bio: {channel_info['bio'][:100]}")
        print(f"  👥 Followers: {self.format_number(channel_info.get('followers', 0))} ({channel_info.get('followers', 0):,})")
        print(f"  ➕ Following: {self.format_number(channel_info.get('following', 0))} ({channel_info.get('following', 0):,})")
        print(f"  ❤️ Channel Likes: {self.format_number(channel_info.get('channel_likes', 0))} ({channel_info.get('channel_likes', 0):,})")
        
        # Thống kê video
        print(f"\n📈 THỐNG KÊ VIDEO:")
        print(f"  📹 Tổng số video: {stats.get('total_videos', 0)}")
        print(f"  👁️ TỔNG LƯỢT XEM: {stats.get('total_views_formatted', '0')} ({stats.get('total_views', 0):,} views)")
        
        if stats.get('total_likes', 0) > 0:
            print(f"  ❤️ Tổng Likes: {stats.get('total_likes_formatted', '0')} ({stats.get('total_likes', 0):,})")
        if stats.get('total_comments', 0) > 0:
            print(f"  💬 Tổng Comments: {stats.get('total_comments_formatted', '0')} ({stats.get('total_comments', 0):,})")
        if stats.get('total_shares', 0) > 0:
            print(f"  🔄 Tổng Shares: {stats.get('total_shares_formatted', '0')} ({stats.get('total_shares', 0):,})")
        
        if stats.get('total_videos', 0) > 0:
            print(f"  📊 Trung bình views/video: {self.format_number(stats.get('average_views', 0))}")
        
        if stats.get('engagement_rate', 0) > 0:
            print(f"  🔥 Engagement Rate: {stats['engagement_rate']}%")
        
        print(f"\n🔗 URL: {data['channel_url']}")
        print(f"🕐 Thời gian scrape: {data['scraped_at']}")
        
        if data.get('videos'):
            # Lọc video có views > 0
            videos_with_views = [v for v in data['videos'] if v['views'] > 0]
            print(f"\n📌 TOP 10 VIDEO HOT NHẤT: (từ {len(videos_with_views)} video có data)")
            print("-"*70)
            
            if videos_with_views:
                # Sắp xếp theo views
                sorted_videos = sorted(videos_with_views, key=lambda x: x['views'], reverse=True)
                for i, video in enumerate(sorted_videos[:10], 1):
                    print(f"\n{i}. 👁️ {self.format_number(video['views'])} views ({video['view_text']})")
                    if video.get('likes', 0) > 0:
                        print(f"   ❤️ {self.format_number(video['likes'])} likes")
                    if video['caption']:
                        print(f"   📝 {video['caption'][:70]}...")
                    if video['link']:
                        print(f"   🔗 {video['link']}")
        
        print("\n" + "="*70)
    
    async def save_to_json(self, data: Dict, filename: str = None):
        """
        Lưu kết quả vào file JSON
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            channel_name = data.get('channel_info', {}).get('name', 'unknown').replace('@', '').replace('/', '_').replace(' ', '_')
            filename = f"tiktok_stats_{channel_name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Đã lưu JSON vào: {filename}")
        return filename
    
    async def save_to_csv(self, data: Dict, filename: str = None):
        """
        Lưu danh sách video vào file CSV
        """
        if 'error' in data or not data.get('videos'):
            print("⚠️ Không có dữ liệu video để xuất CSV")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            channel_name = data.get('channel_info', {}).get('name', 'unknown').replace('@', '').replace('/', '_').replace(' ', '_')
            filename = f"tiktok_videos_{channel_name}_{timestamp}.csv"
        
        # Chuẩn bị headers
        headers = ['Index', 'Views', 'Likes', 'Comments', 'Shares', 'Caption', 'Link']
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for video in data['videos']:
                writer.writerow({
                    'Index': video.get('index', ''),
                    'Views': video.get('views', 0),
                    'Likes': video.get('likes', 0),
                    'Comments': video.get('comments', 0),
                    'Shares': video.get('shares', 0),
                    'Caption': video.get('caption', ''),
                    'Link': video.get('link', '')
                })
        
        print(f"📊 Đã lưu CSV vào: {filename}")
        return filename

async def main():
    parser = argparse.ArgumentParser(
        description='TikTok Channel Statistics Analyzer - Phân tích toàn diện kênh TikTok',
        epilog='Ví dụ: python tiktok_counter.py https://www.tiktok.com/@username --save-json --save-csv'
    )
    parser.add_argument('url', nargs='?', 
                       help='TikTok channel URL (ví dụ: https://www.tiktok.com/@username)')
    parser.add_argument('--headless', action='store_false', default=True,
                       help='Hiển thị browser (không chạy ẩn)')
    parser.add_argument('--save-json', action='store_true',
                       help='Lưu kết quả vào file JSON')
    parser.add_argument('--save-csv', action='store_true',
                       help='Lưu danh sách video vào file CSV')
    parser.add_argument('--max-scrolls', type=int, default=20,
                       help='Số lần scroll tối đa để load video (default: 20)')
    
    args = parser.parse_args()
    
    # Nếu không có URL, yêu cầu nhập
    if not args.url:
        print("\n🔗 Nhập URL kênh TikTok (ví dụ: https://www.tiktok.com/@username):")
        args.url = input("URL: ").strip()
        
        if not args.url:
            print("❌ URL không được để trống!")
            return
    
    # Validate URL
    if 'tiktok.com' not in args.url:
        print("⚠️ URL không hợp lệ. Vui lòng nhập URL TikTok đúng định dạng!")
        return
    
    print(f"\n🚀 Bắt đầu phân tích kênh: {args.url}")
    print(f"🖥️ Chế độ headless: {args.headless}")
    print(f"📜 Max scrolls: {args.max_scrolls}")
    
    # Khởi tạo analyzer
    analyzer = TikTokStatsAnalyzer(headless=args.headless, max_scrolls=args.max_scrolls)
    
    # Scrape channel
    result = await analyzer.scrape_channel(args.url)
    
    # In báo cáo
    analyzer.print_report(result)
    
    # Lưu file nếu cần
    if args.save_json:
        await analyzer.save_to_json(result)
    
    if args.save_csv:
        await analyzer.save_to_csv(result)

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════╗
║   TIKTOK CHANNEL STATISTICS ANALYZER           ║
║   Phân tích toàn diện kênh TikTok              ║
║   Version: 2.0.0 - Enhanced Edition            ║
╚════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Đã dừng chương trình bởi người dùng.")
    except Exception as e:
        print(f"\n\n❌ Lỗi: {str(e)}")