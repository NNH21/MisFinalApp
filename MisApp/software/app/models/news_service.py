"""
MIS Smart Assistant - News Service
Module for fetching latest news from NewsData.io API
Supports Vietnamese news across different categories
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from ..utils import config, logger

class NewsService:
    """
    Service for retrieving latest Vietnamese news from NewsData.io API.
    Supports various news categories like general, business, sports, technology, etc.
    """
    
    def __init__(self):
        """Initialize the news service with API configuration."""
        self.api_key = config.NEWSDATA_API_KEY
        self.base_url = "https://newsdata.io/api/1/news"
        # Note: Country filter "vn" is not supported by NewsData.io API
        # We'll use language filter instead to get Vietnamese content
        self.language = "vi"  # Vietnamese
        self.cached_news = {}
        self.cache_expiry = {}
        self.cache_duration = 30  # Cache for 30 minutes
        
        # Category mapping for Vietnamese queries
        self.category_map = {
            # General news
            "tin mới nhất": "general",
            "tin tức mới nhất": "general", 
            "tin hot": "general",
            "tin nóng": "general",
            "tin trong nước": "general",
            "tin việt nam": "general",
            
            # Business/Economy
            "kinh tế": "business",
            "tin kinh tế": "business",
            "thị trường": "business",
            "chứng khoán": "business",
            "doanh nghiệp": "business",
            "tài chính": "business",
            
            # Sports
            "thể thao": "sports",
            "tin thể thao": "sports",
            "bóng đá": "sports",
            "v-league": "sports",
            "sea games": "sports",
            "olympic": "sports",
            
            # Technology
            "công nghệ": "technology",
            "tin công nghệ": "technology",
            "tech": "technology",
            "điện thoại": "technology",
            "smartphone": "technology",
            "ai": "technology",
            "trí tuệ nhân tạo": "technology",
            
            # Health
            "sức khỏe": "health",
            "y tế": "health",
            "covid": "health",
            "bệnh viện": "health",
            
            # Entertainment
            "giải trí": "entertainment",
            "showbiz": "entertainment",
            "ca sĩ": "entertainment",
            "diễn viên": "entertainment",
            "phim": "entertainment",
            
            # Politics
            "chính trị": "politics",
            "chính phủ": "politics",
            "quốc hội": "politics",
            "thủ tướng": "politics",
            
            # World news
            "thế giới": "world",
            "quốc tế": "world",
            "ukraine": "world",
            "mỹ": "world",
            "trung quốc": "world"
        }
        
        logger.info("News service initialized")
    
    def is_news_query(self, query: str) -> bool:
        """
        Check if the query is asking for news.
        
        Args:
            query (str): User's query
            
        Returns:
            bool: True if it's a news query
        """
        query_lower = query.lower()
        
        news_keywords = [
            "tin tức", "tin mới", "tin nóng", "tin hot", "news",
            "báo", "thông tin", "cập nhật", "kinh tế", "thể thao", 
            "công nghệ", "chính trị", "thế giới", "trong nước",
            "showbiz", "giải trí", "sức khỏe", "y tế", "tin mới nhất"
        ]
        
        return any(keyword in query_lower for keyword in news_keywords)
    
    def get_category_from_query(self, query: str) -> str:
        """
        Extract news category from user query.
        
        Args:
            query (str): User's query
            
        Returns:
            str: News category or 'general' as default
        """
        query_lower = query.lower()
        
        for keyword, category in self.category_map.items():
            if keyword in query_lower:
                return category
        
        return "general"  # Default category
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache_expiry:
            return False
        
        return datetime.now() < self.cache_expiry[cache_key]
    
    def _get_cached_news(self, cache_key: str) -> Optional[List[Dict]]:
        """Get news from cache if valid."""
        if self._is_cache_valid(cache_key) and cache_key in self.cached_news:
            logger.info(f"Returning cached news for: {cache_key}")
            return self.cached_news[cache_key]
        return None
    
    def _cache_news(self, cache_key: str, news_data: List[Dict]):
        """Cache news data."""
        self.cached_news[cache_key] = news_data
        self.cache_expiry[cache_key] = datetime.now() + timedelta(minutes=self.cache_duration)
        logger.info(f"Cached news for: {cache_key}")
    
    def fetch_news(self, category: str = "general", limit: int = 6) -> List[Dict]:
        """
        Fetch news from NewsData.io API.
        
        Args:
            category (str): News category
            limit (int): Number of articles to fetch (default 6)
            
        Returns:
            List[Dict]: List of news articles
        """
        if not self.api_key or self.api_key == "YOUR_NEWSDATA_API_KEY":
            logger.error("NewsData API key not configured")
            return []
        
        cache_key = f"{category}_{limit}"
        
        # Try to get from cache first
        cached_news = self._get_cached_news(cache_key)
        if cached_news:
            return cached_news
        
        try:
            # Prepare API parameters - removed country filter as "vn" is not supported
            params = {
                "apikey": self.api_key,
                "language": self.language,
                "size": limit,
                "category": category if category != "general" else None
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            logger.info(f"Fetching news for category: {category}")
            
            # Make API request
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "success" and "results" in data:
                articles = data["results"]
                processed_articles = []
                
                for article in articles[:limit]:
                    # Process each article
                    processed_article = {
                        "title": article.get("title", "Không có tiêu đề"),
                        "description": article.get("description", "Không có mô tả"),
                        "url": article.get("link", ""),
                        "published_at": article.get("pubDate", ""),
                        "source": article.get("source_id", "Nguồn không xác định"),
                        "image": article.get("image_url", ""),
                        "category": article.get("category", [category] if category else ["general"])
                    }
                    
                    # Format published date
                    if processed_article["published_at"]:
                        try:
                            pub_date = datetime.fromisoformat(processed_article["published_at"].replace("Z", "+00:00"))
                            processed_article["formatted_date"] = pub_date.strftime("%d/%m/%Y %H:%M")
                        except:
                            processed_article["formatted_date"] = "Thời gian không xác định"
                    else:                        processed_article["formatted_date"] = "Thời gian không xác định"
                    
                    processed_articles.append(processed_article)
                
                # Cache the results
                self._cache_news(cache_key, processed_articles)
                
                logger.info(f"Successfully fetched {len(processed_articles)} news articles")
                return processed_articles
            else:
                logger.error(f"API returned error: {data.get('message', 'Unknown error')}")
                return []                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing news response: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in news service: {str(e)}")
            return []
    
    def format_news_response(self, query: str) -> str:
        """
        Format news response based on user query.
        
        Args:
            query (str): User's query
            
        Returns:
            str: Formatted news response with HTML formatting for clickable links
        """
        category = self.get_category_from_query(query)
        articles = self.fetch_news(category, limit=5)  # Limit to 5 news items as requested
        
        if not articles:
            return "Xin lỗi, hiện tại không thể lấy tin tức. Vui lòng thử lại sau."
        
        # Format published date to correct format
        for article in articles:
            if article.get("published_at"):
                try:
                    # Parse the ISO date format from API
                    pub_date = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
                    # Format to YYYY-MM-DD HH:MM:SS
                    article["formatted_date"] = pub_date.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    article["formatted_date"] = "2025-05-31 02:31:00"  # Default fallback
            else:
                article["formatted_date"] = "2025-05-31 02:31:00"  # Default fallback
        
        # Build response with the exact format requested
        total_articles = len(articles)
        response = f'<span style="color: #3498db; font-weight: bold; font-size: 16px;">Tin tức mới nhất từ Việt Nam ({total_articles} tin):</span>\n\n'
        
        for article in articles:
            # Get title
            title = article.get("title", "Không có tiêu đề")
            
            # Get description and limit to first sentence or reasonable length
            description = article.get("description", "Không có mô tả")
            if len(description) > 120:
                # Find the first sentence end or cut at reasonable length
                sentences = description.split('. ')
                if len(sentences) > 1 and len(sentences[0]) < 120:
                    description = sentences[0] + "."
                else:
                    description = description[:120] + "..."
            
            # Get formatted date
            formatted_date = article.get("formatted_date", "2025-05-31 02:31:00")
            
            # Get URL
            url = article.get("url", "#")
            
            # Add each news item in the requested format
            response += f"{title}\n"
            response += f"{description}\n"
            response += f"📅 {formatted_date}\n"
            response += f'<a href="{url}" target="_blank" style="color: #3498db; text-decoration: none; font-weight: bold;">Đọc thêm →</a>\n\n'
        
        return response
    
    def get_formatted_news(self, query: str) -> str:
        """
        Get formatted news response for a query.
        This is the main method to be called from GeminiClient.
        
        Args:
            query (str): User's query
            
        Returns:
            str: Formatted news response
        """
        return self.format_news_response(query)
    
    def format_news_for_voice(self, query: str) -> str:
        """
        Format news specifically for voice reading with the custom format:
        "Tin tức mới nhất hôm nay, ngày tháng năm hiện tại" followed by news titles only.
        
        Args:
            query (str): User's query
            
        Returns:
            str: Text formatted specifically for voice reading
        """
        category = self.get_category_from_query(query)
        articles = self.fetch_news(category, limit=5)  # Limit to 5 news items as requested
        
        if not articles:
            return "Xin lỗi, hiện tại không thể lấy tin tức. Vui lòng thử lại sau."
        
        # Get current date for voice announcement
        from datetime import datetime
        now = datetime.now()
        current_date_voice = f"ngày {now.day} tháng {now.month} năm {now.year}"
        
        # Start with date announcement
        voice_text = f"Tin tức mới nhất hôm nay, {current_date_voice}. "
        
        # Add news titles (only titles, no descriptions)
        for i, article in enumerate(articles, 1):
            title = article.get("title", "Không có tiêu đề")
            voice_text += f"{title}. "
            
        # Add closing message
        voice_text += "Bạn có thể click vào 'Đọc thêm' để hiểu sâu hơn về tin tức, xin cảm ơn."
            
        return voice_text