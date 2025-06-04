import webbrowser
import subprocess
import os
import re
import platform
from ..utils import logger

class LauncherService:
    """
    Service for launching websites and applications.
    Handles opening URLs and starting local applications.
    """
    
    def __init__(self):
        """Initialize the launcher service."""
        self.multimedia_service = None
        self.common_websites = {
            'google': 'https://www.google.com',
            'youtube': 'https://www.youtube.com',
            'facebook': 'https://www.facebook.com',
            'gmail': 'https://mail.google.com',
            'maps': 'https://maps.google.com',
            'github': 'https://github.com',
            'netflix': 'https://www.netflix.com',
            'shopee': 'https://shopee.vn',
            'tiki': 'https://tiki.vn',
            'lazada': 'https://www.lazada.vn',
            'zalo': 'https://chat.zalo.me',
            'ued': 'https://qlht.ued.udn.vn/sinhvien',
            'tiktok': 'https://www.tiktok.com',
            'chatgpt': 'https://chat.openai.com',
            'grok': 'https://grok.com/',
            'soundcloud': 'https://soundcloud.com',
            'claude': 'https://claude.ai/',
            
        }
        self.common_apps = {
            'notepad': 'notepad.exe',
            'teams': 'Teams.exe',
            'calculator': 'calc.exe',
            'explorer': 'explorer.exe',
            'paint': 'mspaint.exe',
            'wordpad': 'wordpad.exe',
            'terminal': 'cmd.exe',
            'powershell': 'powershell.exe',
            'control panel': 'control.exe',
            'task manager': 'taskmgr.exe',
            'word': 'winword.exe',
            'excel': 'excel.exe',
            'powerpoint': 'powerpnt.exe',
        }
        logger.info("Launcher service initialized")
    
    def set_multimedia_service(self, multimedia_service):
        """Set the multimedia service reference."""
        self.multimedia_service = multimedia_service
        logger.info("Multimedia service reference set in launcher service")
    
    def is_launch_command(self, query):
        """
        Check if the query is a command to launch a website or application.
        
        Args:
            query (str): The user's query
            
        Returns:
            bool: True if it's a launch command, False otherwise
        """
        query_lower = query.lower()
        
        # Check for launch-related keywords
        launch_keywords = [
            "open", "launch", "start", "run", "go to", "navigate to", "visit", "browse",
            "mở", "khởi chạy", "bắt đầu", "chạy", "đi tới", "truy cập", "duyệt"
        ]
        
        if any(keyword in query_lower for keyword in launch_keywords):
            return True
            
        # Check for common websites by name
        for name in self.common_websites.keys():
            if name in query_lower:
                return True
                
        # Check for common apps by name
        for name in self.common_apps.keys():
            if name in query_lower:
                return True
                
        # Check for URL patterns
        url_pattern = r"(https?://[^\s]+)|(www\.[^\s]+\.)"
        if re.search(url_pattern, query_lower):
            return True
            
        return False
    
    def is_music_request(self, query):
        """
        Check if the query is a music-related request.
        
        Args:
            query (str): The user's query
            
        Returns:
            bool: True if it's a music request, False otherwise
        """
        if not self.multimedia_service:
            return False
            
        query_lower = query.lower().strip()
        
        opening_prefixes = ["mở", "open", "launch", "start", "run", "go to"]
        for prefix in opening_prefixes:
            if query_lower.startswith(prefix):
                remaining_text = query_lower[len(prefix):].strip()
                # Check for known websites
                for site in self.common_websites.keys():
                    if remaining_text == site or remaining_text.startswith(site + " "):
                        return False
                # Check for known apps
                for app in self.common_apps.keys():
                    if remaining_text == app or remaining_text.startswith(app + " "):
                        return False
        
        for name in list(self.common_websites.keys()) + list(self.common_apps.keys()):
            if name in query_lower:
                return False
        
        # Check if the multimedia service considers this a media command
        if hasattr(self.multimedia_service, 'is_media_command') and self.multimedia_service.is_media_command(query):
            return True
        
        # Music-specific keywords that aren't ambiguous
        specific_music_keywords = [
            "play song", "listen to song", "play music", "listen to music", 
            "phát bài hát", "nghe bài hát", "phát nhạc", "nghe nhạc",
            "spotify", "youtube music", "play album", "nhạc sĩ", "ca sĩ", "ca khúc"
        ]
        
        for keyword in specific_music_keywords:
            if keyword in query_lower:
                return True
                
        general_music_keywords = ["play", "pause", "song", "music", "track", "album", "artist"]
        
        for keyword in general_music_keywords:
            if keyword in query_lower:
                # Check if this keyword is part of a website or app name
                is_part_of_name = False
                for name in list(self.common_websites.keys()) + list(self.common_apps.keys()):
                    if keyword in name:
                        is_part_of_name = True
                        break
                        
                if not is_part_of_name:
                    return True
                
        return False
    
    def open_website(self, query):
        """
        Open a website based on the query.
        
        Args:
            query (str): The query containing the website to open
            
        Returns:
            str: Message about what was opened
        """
        # Clean up the query
        query = query.lower().strip()
        
        # Remove common phrases like "open", "go to", etc.
        for phrase in ["open", "go to", "navigate to", "visit", "browse", "show me", "mở", "đi tới", "truy cập"]:
            if query.startswith(phrase):
                query = query[len(phrase):].strip()
                logger.info(f"Removed prefix '{phrase}', new query: '{query}'")
        
        # Check if this is a common website
        for name, url in self.common_websites.items():
            if query == name or name in query or name.replace(' ', '') in query.replace(' ', ''):
                logger.info(f"Found match for website: '{name}' with URL: {url}")
                webbrowser.open(url)
                logger.info(f"Opened website: {url}")
                return f"Đã mở {name.capitalize()} thành công."
        
        # Check if query contains a URL
        url_pattern = r"(https?://[^\s]+)"
        url_match = re.search(url_pattern, query)
        if url_match:
            url = url_match.group(1)
            webbrowser.open(url)
            logger.info(f"Opened URL: {url}")
            return f"Đã mở {url} thành công."
        
        # If query doesn't contain a proper URL, assume it's a search
        if not query.startswith(('http://', 'https://', 'www.')):
            if 'youtube' in query or 'video' in query:
                # If YouTube specific, search on YouTube
                query = query.replace('youtube', '').replace('video', '').strip()
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            else:
                # Otherwise search on Google
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            webbrowser.open(url)
            logger.info(f"Searched for: {query} using URL: {url}")
            return f"Đã tìm kiếm '{query}'"
        
        # Try to open as a direct URL with www prefix if needed
        if not query.startswith(('http://', 'https://')):
            if not query.startswith('www.'):
                query = 'www.' + query
            url = 'https://' + query
        else:
            url = query
            
        try:
            webbrowser.open(url)
            logger.info(f"Opened URL: {url}")
            return f"Đã mở {url} thành công."
        except Exception as e:
            logger.error(f"Error opening URL {url}: {str(e)}")
            return f"Không thể mở {url}. Lỗi: {str(e)}"
    
    def launch_application(self, query):
        """
        Launch a local application based on the query.
        
        Args:
            query (str): The query containing the application to launch
            
        Returns:
            str: Message about what was launched
        """
        query = query.lower().strip()
        
        # Remove common phrases
        for phrase in ["launch", "start", "open", "run", "execute", "mở", "chạy", "khởi chạy", "bắt đầu"]:
            if query.startswith(phrase):
                query = query[len(phrase):].strip()
        
        # Check if this is a common application
        system = platform.system()
        
        if system == "Windows":
            for name, app in self.common_apps.items():
                if name in query or name.replace(' ', '') in query.replace(' ', ''):
                    try:
                        subprocess.Popen(app, shell=True)
                        logger.info(f"Launched application: {app}")
                        return f"Đã mở {name.capitalize()}"
                    except Exception as e:
                        logger.error(f"Error launching {app}: {str(e)}")
                        return f"Không thể mở {name}. Lỗi: {str(e)}"
        
        # Try the query as a direct command or path
        try:
            subprocess.Popen(query, shell=True)
            logger.info(f"Executed command: {query}")
            return f"Đã thực thi lệnh: {query}"
        except Exception as e:
            logger.error(f"Error executing command {query}: {str(e)}")
            return f"Không thể thực thi: {query}. Lỗi: {str(e)}"
    
    def process_launch_command(self, query):
        """
        Process a launch command - ensures compatibility with GeminiClient's _launch_response method.
        This method identifies if the query is a music request and routes it accordingly.
        
        Args:
            query (str): The user's query
            
        Returns:
            str: Response message
        """
        query_lower = query.lower()
        logger.info(f"Processing launch command: '{query}'")
        
        # Check for website keywords and website names first to prioritize them
        for name in self.common_websites.keys():
            if name in query_lower:
                logger.info(f"Detected website launch request for '{name}': {query}")
                return self.open_website(query)
                
        # Next check for application names
        for name in self.common_apps.keys():
            if name in query_lower:
                logger.info(f"Detected application launch request for '{name}': {query}")
                return self.launch_application(query)
        
        # If it doesn't match a website or app specifically, then check for music
        if self.is_music_request(query):
            logger.info(f"Detected music request: {query}")
            if self.multimedia_service:
                return self.multimedia_service.process_music_request(query)
            else:
                return "Dịch vụ đa phương tiện không khả dụng"
                
        # If still no match, process as a regular launch command
        logger.info(f"Processing general launch command: {query}")
        return self.process_request(query)
    
    def process_request(self, query):
        """
        Process a request to launch a website or application.
        
        Args:
            query (str): The user's query
            
        Returns:
            str: Response message
        """
        # Do NOT check for music requests here to avoid recursion with process_launch_command
        query_lower = query.lower()
        
        # Prioritize website detection for common sites
        for name in self.common_websites.keys():
            if name in query_lower:
                return self.open_website(query)
        
        # Check website keywords
        website_keywords = ["website", "site", "web", "browse", "internet", "url", "http", 
                           "trang web", "web", "mạng", "truy cập", "duyệt"]
        if any(keyword in query_lower for keyword in website_keywords) or "." in query_lower:
            return self.open_website(query)
        
        # Check application keywords
        app_keywords = ["app", "application", "program", "software", "run", "execute", 
                       "ứng dụng", "phần mềm", "chương trình", "chạy"]
        if any(keyword in query_lower for keyword in app_keywords):
            return self.launch_application(query)
        
        for name in self.common_apps.keys():
            if name in query_lower:
                return self.launch_application(query)
        
        return self.open_website(query)