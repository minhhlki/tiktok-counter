#!/usr/bin/env python3
"""
Ví dụ sử dụng TikTok Stats Analyzer với Python code
"""

import asyncio
from tiktok_counter import TikTokStatsAnalyzer

async def analyze_channel(url: str):
    """
    Phân tích một kênh TikTok
    """
    # Khởi tạo analyzer
    analyzer = TikTokStatsAnalyzer(
        headless=True,      # Chạy ẩn browser
        max_scrolls=25      # Scroll 25 lần để load nhiều video
    )
    
    # Scrape dữ liệu
    print(f"🔍 Đang phân tích: {url}\n")
    result = await analyzer.scrape_channel(url)
    
    # Hiển thị báo cáo
    analyzer.print_report(result)
    
    # Lưu kết quả
    await analyzer.save_to_json(result)
    await analyzer.save_to_csv(result)
    
    return result

async def compare_channels(urls: list):
    """
    So sánh nhiều kênh
    """
    results = []
    
    for url in urls:
        analyzer = TikTokStatsAnalyzer(headless=True, max_scrolls=20)
        result = await analyzer.scrape_channel(url)
        results.append(result)
        print("\n" + "="*70 + "\n")
    
    # So sánh
    print("📊 SO SÁNH CÁC KÊNH:")
    print("="*70)
    
    for i, result in enumerate(results, 1):
        if 'error' not in result:
            channel_info = result['channel_info']
            stats = result['statistics']
            
            print(f"\n{i}. {channel_info.get('name', 'N/A')}")
            print(f"   Followers: {stats.get('total_views_formatted', 'N/A')}")
            print(f"   Total Views: {stats.get('total_views_formatted', 'N/A')}")
            print(f"   Videos: {stats.get('total_videos', 0)}")
            print(f"   Avg Views: {stats.get('average_views', 0):,}")

async def main():
    # Ví dụ 1: Phân tích 1 kênh
    print("="*70)
    print("VÍ DỤ 1: PHÂN TÍCH 1 KÊNH")
    print("="*70)
    
    channel_url = "https://www.tiktok.com/@tiktok"
    await analyze_channel(channel_url)
    
    # Ví dụ 2: So sánh nhiều kênh
    # print("\n\n" + "="*70)
    # print("VÍ DỤ 2: SO SÁNH NHIỀU KÊNH")
    # print("="*70)
    # 
    # channels_to_compare = [
    #     "https://www.tiktok.com/@channel1",
    #     "https://www.tiktok.com/@channel2",
    #     "https://www.tiktok.com/@channel3"
    # ]
    # await compare_channels(channels_to_compare)

if __name__ == "__main__":
    asyncio.run(main())

