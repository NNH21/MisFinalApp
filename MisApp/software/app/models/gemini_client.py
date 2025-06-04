import google.generativeai as genai
import os
import time
import re
import threading
from datetime import datetime
from ..utils import config, logger

class GeminiClient:
    """
    Client for interacting with Google's Gemini AI model.
    Handles sending queries and receiving responses.
    """    
    def __init__(self, time_service=None, weather_service=None, launcher_service=None, multimedia_service=None, hardware_interface=None, lcd_service=None, news_service=None):
        self.api_key = config.GEMINI_API_KEY
        self._initialize_client()
        self.conversation_history = []
        self.max_history_length = 3  
        self.is_generating = False
        self.stop_generation = False
        self._temp_voice_text = None 
        
        self.time_service = time_service
        self.weather_service = weather_service
        self.launcher_service = launcher_service
        self.multimedia_service = multimedia_service
        self.hardware_interface = hardware_interface
        self.lcd_service = lcd_service
        self.news_service = news_service
        
        self.custom_responses = {
            "identity": self._identity_response,
            "greeting": self._greeting_response,
            "time": self._time_response,
            "date": self._date_response,
            "weather": self._weather_response,
            "launch": self._launch_response,
            "media": self._media_response,
            "lcd": self._lcd_response,
            "news": self._news_response,
        }
        
    def _initialize_client(self):
        """Initialize the Gemini API client with the API key."""
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY":
            logger.error("Gemini API key not configured. Please set it in config.py")
            raise ValueError("Gemini API key not configured")
            
        genai.configure(api_key=self.api_key)
        
        try:
            available_models = list(genai.list_models()) 
            model_names = [model.name for model in available_models]
            logger.info(f"Available models: {model_names}")
            
            gemini_models = [model for model in available_models if 'gemini' in model.name.lower()]
            
            if not gemini_models:
                if available_models:
                    fallback_model = available_models[0]
                    logger.warning(f"No Gemini models available. Using fallback model: {fallback_model.name}")
                    self.model = genai.GenerativeModel(fallback_model.name)
                    logger.info(f"Using fallback model: {fallback_model.name}")
                else:
                    raise ValueError("No models available. Please check your API key and permissions.")
            else:
                preferred_models = [
                    "gemini-1.5-flash", 
                    "gemini-1.0-pro-vision",
                    "gemini-1.5-pro", 
                    "gemini-1.0-pro", 
                    "gemini-pro",
                    "gemini-2.0-pro"
                ]
                
                selected_model = None
                
                for preferred in preferred_models:
                    for model in gemini_models:
                        if preferred in model.name.lower():
                            selected_model = model.name
                            break
                    if selected_model:
                        break
                
                if not selected_model:
                    selected_model = gemini_models[0].name
                    
                self.model = genai.GenerativeModel(
                    selected_model,
                    generation_config={
                        "temperature": 0.2,  
                        "max_output_tokens": 1024,  
                        "top_p": 0.85, 
                        "top_k": 30  
                    }
                )
                logger.info(f"Using Gemini model: {selected_model} with optimized settings")
            
            # Start a conversation
            self.chat = self.model.start_chat(history=[])
            logger.info("Gemini API client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise
    
    def generate_response(self, query):
        """
        Generate a response to the given query using Gemini AI.
        
        Args:
            query (str): The user's question or prompt
            
        Returns:
            str: The AI-generated response
        """
        if not query:
            return "Tôi không nghe rõ câu hỏi của bạn. Vui lòng thử lại."
        
        self.is_generating = True
        self.stop_generation = False
        
        try:
            special_response = self._handle_special_queries(query)
            if special_response:
                self.conversation_history.append({"role": "user", "content": query})
                self.conversation_history.append({"role": "assistant", "content": special_response})
                
                if len(self.conversation_history) > self.max_history_length * 2:
                    self.conversation_history = self.conversation_history[-self.max_history_length*2:]
                
                logger.log_conversation(query, special_response)
                
                self.is_generating = False
                return special_response
            
            logger.info(f"Sending query to Gemini: {query}")
            
            system_prompt = "Bạn là MIS Assistant. Trả lời ngắn gọn, chính xác bằng tiếng Việt. Giới hạn 100 từ."
            
            start_time = time.time()
            
            response = self.chat.send_message(
                query,
                generation_config={
                    "temperature": 0.7,  # Giảm từ mặc định xuống 0.7
                    "top_p": 0.8,  # Giảm từ mặc định xuống 0.8
                    "top_k": 20,  # Giảm từ mặc định xuống 20
                    "max_output_tokens": 200,  # Giới hạn độ dài câu trả lời
                }
            )
            
            # Extract the text from the response
            response_text = response.text
            
            # Process the response to fix formatting issues
            response_text = self._format_response(response_text)
            
            # Calculate response time
            end_time = time.time()
            response_time = end_time - start_time
            logger.info(f"Gemini response received in {response_time:.2f} seconds")
            
            # Check if we were asked to stop
            if self.stop_generation:
                self.is_generating = False
                return "Phản hồi bị dừng lại."
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": query})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Trim history if needed
            if len(self.conversation_history) > self.max_history_length * 2:
                # Keep only the most recent conversations
                self.conversation_history = self.conversation_history[-self.max_history_length*2:]
            
            # Log the conversation
            logger.log_conversation(query, response_text)
            
            # Reset generating flag
            self.is_generating = False
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {str(e)}")
            self.is_generating = False
            return f"Xin lỗi, có lỗi khi xử lý yêu cầu của bạn: {str(e)}"
    
    def stop_response_generation(self):
        """Stop any ongoing response generation."""
        if self.is_generating:
            logger.info("Stopping response generation")
            self.stop_generation = True
            return True
        return False
    
    def _format_response(self, text):
        """
        Format response text to fix common issues with special characters.
        
        Args:
            text (str): The raw response text from Gemini
            
        Returns:
            str: Properly formatted response text
        """
        # Handle markdown bullet points (asterisks)
        # Replace "* " at the beginning of a line with "• "
        text = re.sub(r'(?m)^\*\s+', '• ', text)
        
        # Replace other asterisks used for emphasis with proper formatting
        # Preserve any natural asterisks that aren't used for formatting
        text = re.sub(r'(?<!\*)\*\*(?!\*)(.+?)(?<!\*)\*\*(?!\*)', r'\1', text)  # Remove bold
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)      # Remove italic
        
        # Fix other common formatting issues that might appear
        text = text.replace('__', '')  # Remove underscores for emphasis
        text = text.replace('~~', '')  # Remove strikethrough
        
        return text
    
    def _handle_special_queries(self, query):
        """
        Handle special queries that don't need to be sent to Gemini.
        
        Args:
            query (str): The user's query
            
        Returns:
            str or None: Response if query was handled, None otherwise
        """
        query_lower = query.lower()
        
        # Check for launch commands first (e.g., "Mở YouTube") to prioritize them
        if self.launcher_service and self._is_launch_command(query_lower):
            logger.info(f"Detected launch command: {query}")
            return self.custom_responses["launch"](query)
        
        # Identity questions
        if self._is_identity_query(query_lower):
            return self.custom_responses["identity"](query)
            
        # Hey Mis/greeting detection
        if self._is_greeting_query(query_lower):
            return self.custom_responses["greeting"](query)
            
        # Alarm commands
        if self.time_service and self._is_alarm_command(query_lower):
            return self._handle_alarm_command(query)
            
        # Clock display commands - prioritize these over regular time queries
        if self.time_service and (
            "hiển thị thời gian" in query_lower or 
            "hiển thị đồng hồ" in query_lower or
            "tắt hiển thị thời gian" in query_lower or
            "tắt đồng hồ" in query_lower
        ):
            return self.custom_responses["time"](query)
            
        # Time-related queries
        if self.time_service and self._is_time_query(query_lower):
            # Extract location from query if present
            location = self.time_service.get_location_from_query(query)
            
            # Get formatted time response
            return self.time_service.format_time_response(location)
            
        # Date-related queries
        if self._is_date_query(query_lower):
            return self.custom_responses["date"](query)        # Weather-related queries
        if self.weather_service and self._is_weather_query(query_lower):
            # Try to extract location from the query
            location = self.weather_service.extract_location_from_query(query)
            
            # Get formatted weather response
            return self.weather_service.get_formatted_weather(location)
        
        # News-related queries
        if self.news_service and self._is_news_query(query_lower):
            news_result = self.custom_responses["news"](query)
            # News response returns tuple (display_text, voice_text)
            if isinstance(news_result, tuple) and len(news_result) == 2:
                # Mark this as a news response that needs special voice handling
                display_text, voice_text = news_result
                # Store the voice text for later use
                self._temp_voice_text = voice_text
                return display_text
            else:
                # Fallback for backward compatibility
                return news_result
        
        # LED control commands
        if self._is_led_control_command(query_lower):
            return self._handle_led_command(query)
            
        # LCD display commands
        if self.lcd_service and self._is_lcd_command(query_lower):
            return self.custom_responses["lcd"](query)
            
        # Music/media control commands
        if self.multimedia_service and self._is_media_command(query_lower):
            return self.custom_responses["media"](query)
            
        # No special handling found
        return None
    
    def _is_identity_query(self, query_lower):
        """Check if query is asking about the assistant's identity."""
        identity_patterns = [
            "tên gì",
            "tên là gì",
            "tên bạn là gì",
            "bạn tên là gì",
            "bạn là ai",
            "cho tôi biết tên",
            "ai vậy",
            "your name",
            "who are you"
        ]
        
        for pattern in identity_patterns:
            if pattern in query_lower:
                return True
                
        return False
    
    def _is_greeting_query(self, query_lower):
        """Check if query is a greeting to Mis."""
        greeting_patterns = [
            "hey mis",
            "hey mít",
            "hây mis",
            "hây mít",
            "hey mís",
            "hây mís",
            "chào mis",
            "mis ơi",
            "mít ơi",
            "mís ơi",
            "ê mis",
            "ê mít",
            "ê mís",
            "xin chào mis",
            "xin chào mít"
        ]
        
        for pattern in greeting_patterns:
            if pattern in query_lower:
                return True
                
        return False
        
    def _is_date_query(self, query_lower):
        """Check if query is asking about date information."""
        date_patterns = [
            "ngày mấy",
            "ngày bao nhiêu",
            "hôm nay là ngày",
            "ngày tháng",
            "ngày hôm nay",
            "tháng mấy",
            "năm bao nhiêu",
            "ngày mai",
            "hôm qua",
            "ngày kia",
            "ngày mốt",
            "ngày kìa",
            "hôm kia",
            "tuần tới",
            "tuần sau",
            "tuần trước",
            "tuần này",
            "tháng sau",
            "tháng tới",
            "tháng trước",
            "tháng này",
            "năm sau",
            "năm tới",
            "năm trước",
            "năm này",
            "thứ mấy",
            "hôm nào",
            "mấy hôm nữa"
        ]
        
        for pattern in date_patterns:
            if pattern in query_lower:
                return True
                
        return False
    
    def _is_alarm_command(self, query_lower):
        """
        Check if a query is related to alarm commands.
        
        Args:
            query_lower (str): Lowercase query string
            
        Returns:
            bool: True if this is an alarm command
        """
        alarm_patterns = [
            "tắt báo thức",
            "tắt âm thanh báo thức", 
            "dừng báo thức",
            "tắt chuông",
            "đặt báo thức",
            "hẹn giờ",
            "báo thức",
            "đánh thức",
            "gọi tôi dậy"
        ]
        
        for pattern in alarm_patterns:
            if pattern in query_lower:
                return True
                
        return False
    
    def _handle_alarm_command(self, query):
        """
        Handle alarm-related commands.
        
        Args:
            query (str): The user's query
            
        Returns:
            str: Response to the alarm command
        """
        if not self.time_service:
            return "Xin lỗi, dịch vụ báo thức không khả dụng."
        
        query_lower = query.lower()
        
        # Stop alarm commands - process via TimeService
        if any(phrase in query_lower for phrase in ["tắt báo thức", "tắt âm thanh báo thức", "dừng báo thức", "tắt chuông"]):
            alarm_response = self.time_service.process_alarm_voice_command(query)
            if alarm_response:
                return alarm_response
        
        # Set alarm commands
        elif any(phrase in query_lower for phrase in ["đặt báo thức", "hẹn giờ", "báo thức", "đánh thức", "gọi tôi dậy"]):
            # Process the set alarm command
            return self.time_service.parse_and_set_alarm(query)
            
        # If the command wasn't recognized or handled
        return "Tôi không hiểu yêu cầu về báo thức. Bạn có thể nói \"đặt báo thức cho tôi [giờ] [phút]\" để tạo báo thức mới, hoặc \"tắt báo thức\" để dừng báo thức đang kêu."
    
    def _date_response(self, query):
        """
        Generate a response with date information based on the query.
        Handles relative dates like "tomorrow", "yesterday", "next week", etc.
        Supports Vietnamese date terminology.
        """
        import datetime
        from dateutil.relativedelta import relativedelta
        
        query_lower = query.lower()
        today = datetime.datetime.now()
        
        # Vietnamese weekday mapping
        weekday_map = {
            0: "Thứ Hai",
            1: "Thứ Ba",
            2: "Thứ Tư",
            3: "Thứ Năm",
            4: "Thứ Sáu", 
            5: "Thứ Bảy",
            6: "Chủ Nhật"
        }
        
        # Format date function to standardize responses
        def format_date_response(date_obj, prefix=""):
            weekday = weekday_map.get(date_obj.weekday(), "không xác định")
            return f"{prefix}{weekday}, ngày {date_obj.day} tháng {date_obj.month} năm {date_obj.year}"
        
        # Basic relative dates
        if "hôm nay" in query_lower or "ngày hôm nay" in query_lower:
            return format_date_response(today, "Hôm nay là ")
            
        elif "ngày mai" in query_lower or "tomorrow" in query_lower:
            tomorrow = today + datetime.timedelta(days=1)
            return format_date_response(tomorrow, "Ngày mai là ")
            
        elif "hôm qua" in query_lower or "yesterday" in query_lower:
            yesterday = today - datetime.timedelta(days=1)
            return format_date_response(yesterday, "Hôm qua là ")
            
        elif "ngày kia" in query_lower or "ngày mốt" in query_lower:
            # "Ngày kia" or "ngày mốt" in Vietnamese is 2 days from today
            day_after_tomorrow = today + datetime.timedelta(days=2)
            return format_date_response(day_after_tomorrow, "Ngày kia là ")
            
        elif "hôm kia" in query_lower:
            # "Hôm kia" in Vietnamese is 2 days before today
            day_before_yesterday = today - datetime.timedelta(days=2)
            return format_date_response(day_before_yesterday, "Hôm kia là ")
            
        # Week-based queries
        elif "tuần này" in query_lower:
            start_of_week = today - datetime.timedelta(days=today.weekday())
            end_of_week = start_of_week + datetime.timedelta(days=6)
            return f"Tuần này bắt đầu từ {start_of_week.day}/{start_of_week.month} đến {end_of_week.day}/{end_of_week.month}/{end_of_week.year}"
            
        elif "tuần sau" in query_lower or "tuần tới" in query_lower or "next week" in query_lower:
            next_week = today + datetime.timedelta(weeks=1)
            return format_date_response(next_week, "Ngày này tuần sau là ")
            
        elif "tuần trước" in query_lower or "last week" in query_lower:
            last_week = today - datetime.timedelta(weeks=1)
            return format_date_response(last_week, "Ngày này tuần trước là ")
            
        # Month-based queries    
        elif "tháng này" in query_lower:
            days_in_month = (today.replace(month=today.month % 12 + 1, day=1) - datetime.timedelta(days=1)).day
            return f"Tháng này là tháng {today.month} năm {today.year}, có {days_in_month} ngày"
            
        elif "tháng sau" in query_lower or "tháng tới" in query_lower or "next month" in query_lower:
            next_month = today + relativedelta(months=1)
            return format_date_response(next_month, "Ngày này tháng sau là ")
            
        elif "tháng trước" in query_lower or "last month" in query_lower:
            last_month = today - relativedelta(months=1)
            return format_date_response(last_month, "Ngày này tháng trước là ")
            
        # Year-based queries    
        elif "năm này" in query_lower:
            return f"Năm này là năm {today.year}" + (", năm nhuận" if (today.year % 4 == 0 and today.year % 100 != 0) or (today.year % 400 == 0) else "")
            
        elif "năm sau" in query_lower or "năm tới" in query_lower or "next year" in query_lower:
            next_year = today + relativedelta(years=1)
            return format_date_response(next_year, "Ngày này năm sau là ")
            
        elif "năm trước" in query_lower or "last year" in query_lower:
            last_year = today - relativedelta(years=1)
            return format_date_response(last_year, "Ngày này năm trước là ")
            
        # Handle specific "day of week" questions    
        elif "thứ mấy" in query_lower:
            # First, check for specific relative days
            if "ngày mai" in query_lower:
                tomorrow = today + datetime.timedelta(days=1)
                return f"Ngày mai là {weekday_map.get(tomorrow.weekday())}"
                
            elif "hôm qua" in query_lower:
                yesterday = today - datetime.timedelta(days=1)
                return f"Hôm qua là {weekday_map.get(yesterday.weekday())}"
                
            elif "ngày kia" in query_lower or "ngày mốt" in query_lower:
                day_after_tomorrow = today + datetime.timedelta(days=2)
                return f"Ngày kia là {weekday_map.get(day_after_tomorrow.weekday())}"
                
            elif "hôm kia" in query_lower:
                day_before_yesterday = today - datetime.timedelta(days=2)
                return f"Hôm kia là {weekday_map.get(day_before_yesterday.weekday())}"
            
            # Default to today
            return f"Hôm nay là {weekday_map.get(today.weekday())}"
        
        # Process custom day requests like "3 ngày nữa" or "5 ngày trước"
        elif any(s in query_lower for s in ["ngày nữa", "hôm nữa", "ngày tới"]):
            # Try to extract the number of days
            import re
            day_match = re.search(r'(\d+)\s*(ngày|hôm)\s*(nữa|tới)', query_lower)
            if day_match:
                try:
                    days_ahead = int(day_match.group(1))
                    future_date = today + datetime.timedelta(days=days_ahead)
                    return format_date_response(future_date, f"{days_ahead} ngày nữa là ")
                except (ValueError, IndexError):
                    pass  # Fall through to default
        
        elif any(s in query_lower for s in ["ngày trước", "hôm trước"]):
            # Try to extract the number of days
            import re
            day_match = re.search(r'(\d+)\s*(ngày|hôm)\s*trước', query_lower)
            if day_match:
                try:
                    days_ago = int(day_match.group(1))
                    past_date = today - datetime.timedelta(days=days_ago)
                    return format_date_response(past_date, f"{days_ago} ngày trước là ")
                except (ValueError, IndexError):
                    pass  # Fall through to default
        
        # Handle general date questions
        elif "ngày mấy" in query_lower or "ngày bao nhiêu" in query_lower:
            return f"Hôm nay là ngày {today.day} tháng {today.month} năm {today.year}"
        
        elif "tháng mấy" in query_lower:
            return f"Bây giờ là tháng {today.month} năm {today.year}"
            
        elif "năm bao nhiêu" in query_lower:
            return f"Năm hiện tại là năm {today.year}"
            
        # Default response about today's date
        return format_date_response(today, "Hôm nay là ")
    
    def _identity_response(self, query):
        """Generate a response about the assistant's identity."""
        return "Tôi là Mis, trợ lý thông minh của bạn. Tôi có thể giúp trả lời câu hỏi, cung cấp thông tin thời tiết, thời gian và nhiều điều khác."
    
    def _greeting_response(self, query):
        """Generate a response to 'Hey Mis' greeting."""
        responses = [
            "Dạ có Mis đây ạ, bạn cần giúp gì?",
            "Dạ, Mis đang nghe. Có điều gì tôi có thể giúp bạn?",
            "Dạ, Mis đang lắng nghe. Bạn cần Mis hỗ trợ gì ạ?",
            "Dạ, Mis có thể giúp gì cho bạn?",
            "Dạ vâng, Mis đang nghe bạn đây!",
            "Dạ có Mis đây, bạn cần hỏi gì ạ?"
        ]
        import random
        return random.choice(responses)
    
    def _time_response(self, query):
        """
        Handle time queries only (KHÔNG còn LED Matrix).
        """
        if not self.time_service:
            import datetime
            now = datetime.datetime.now()
            return f"Bây giờ là {now.strftime('%H:%M:%S')}."
        location = self.time_service.get_location_from_query(query)
        return self.time_service.format_time_response(location)
    
    def _weather_response(self, query):
        """
        Handle weather queries using the WeatherService.
        
        Args:
            query (str): The user's query
            
        Returns:
            str: Formatted weather information
        """
        if not self.weather_service:
            return "Xin lỗi, dịch vụ thời tiết không khả dụng lúc này."
        
        # Try to extract a location from the query
        location = self.weather_service.extract_location_from_query(query)
              # Get the weather data for the specified location or default location
        formatted_weather = self.weather_service.get_formatted_weather(location)
        
        # If no data is available
        if not formatted_weather or formatted_weather == "Thông tin thời tiết không khả dụng.":
            return "Xin lỗi, không thể lấy thông tin thời tiết vào lúc này. Vui lòng thử lại sau."
            
        return formatted_weather
    def _news_response(self, query):
        """
        Handle news queries using the NewsService.
        
        Args:
            query (str): The user's query
            
        Returns:
            tuple: (display_text, voice_text) - formatted news for display and voice
        """
        if not self.news_service:
            error_msg = "Xin lỗi, dịch vụ tin tức không khả dụng lúc này."
            return (error_msg, error_msg)
        
        try:
            # Get formatted news response for display
            formatted_news = self.news_service.get_formatted_news(query)
            
            # Get formatted news for voice reading
            voice_news = self.news_service.format_news_for_voice(query)
            
            # If no data is available
            if not formatted_news:
                error_msg = "Xin lỗi, không thể lấy tin tức vào lúc này. Vui lòng thử lại sau."
                return (error_msg, error_msg)
                
            return (formatted_news, voice_news)
        except Exception as e:
            logger.error(f"Error in _news_response: {str(e)}")
            error_msg = f"Xin lỗi, có lỗi khi lấy tin tức: {str(e)}"
            return (error_msg, error_msg)
        
    def _is_time_query(self, query_lower):
        """
        Check if a query is asking about the current time.
        
        Args:
            query_lower (str): Lowercase query string
            
        Returns:
            bool: True if this is a time query
        """
        time_patterns = [
            "mấy giờ",
            "thời gian hiện tại",
            "giờ hiện tại",
            "giờ bây giờ",
            "giờ giấc",
            "mấy giờ rồi",
            "hiện giờ là mấy giờ",
            "bây giờ là",
            "thời gian ở",
            "giờ ở"
            # Removed display clock commands as they're handled separately now
        ]
        
        for pattern in time_patterns:
            if pattern in query_lower:
                return True
                
        return False
    
    def _is_weather_query(self, query_lower):
        """
        Check if a query is asking about weather.
        
        Args:
            query_lower (str): Lowercase query string
            
        Returns:
            bool: True if this is a weather query
        """
        weather_patterns = [
            "thời tiết",
            "lượng mưa",
            "nắng",
            "nhiệt độ",
            "độ ẩm",
            "gió",
            "dự báo",
            "trời",
            "thời tiết hôm nay",
            "thời tiết ngày mai",
            "nóng",
            "lạnh",
            "thời tiết như thế nào",
            "nhiệt độ là bao nhiêu",
            "trời có mưa không"        ]
        for pattern in weather_patterns:
            if pattern in query_lower:
                return True
                
        return False
    
    def _is_news_query(self, query_lower):
        """
        Check if a query is asking for news.
        
        Args:
            query_lower (str): Lowercase query string
            
        Returns:
            bool: True if this is a news query
        """
        if not self.news_service:
            return False
            
        return self.news_service.is_news_query(query_lower)
    
    def _is_launch_command(self, query_lower):
        """
        Check if a query is asking to open a website or application.
        
        Args:
            query_lower (str): Lowercase query string
            
        Returns:
            bool: True if this is a launch command
        """
        # If launcher service isn't available, always return False
        if not self.launcher_service:
            return False
            
        # Đảm bảo lệnh âm nhạc không được phân loại nhầm thành launch command
        if self.multimedia_service and self._is_media_command(query_lower):
            return False
            
        return self.launcher_service.is_launch_command(query_lower)
    
    def _launch_response(self, query):
        """
        Handle commands to open websites or applications.
        
        Args:
            query (str): The user's query
            
        Returns:
            str: Response to the launch command
        """
        # If launcher service isn't available, return a helpful message
        if not self.launcher_service:
            return "Xin lỗi, dịch vụ mở trang web và ứng dụng không khả dụng."
            
        try:
            # Process the launch command using the launcher service
            logger.info(f"Sending launch command to launcher service: {query}")
            result = self.launcher_service.process_launch_command(query)
            logger.info(f"Launch command result: {result}")
            return result
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error in _launch_response: {str(e)}")
            return f"Xin lỗi, không thể mở ứng dụng hoặc trang web. Lỗi: {str(e)}"
    
    def _is_media_command(self, query_lower):
        """
        Check if a query is a multimedia command.
        
        Args:
            query_lower (str): Lowercase query string
            
        Returns:
            bool: True if this is a multimedia command
        """
        # If multimedia service isn't available, always return False
        if not self.multimedia_service:
            return False
            
        # Check for direct multimedia commands
        media_commands = [
            "play", "pause", "stop", "next", "prev", "previous", "volume",
            "phát", "bắt đầu", "tạm dừng", "dừng", "tiếp theo", "trước"
        ]
        
        for command in media_commands:
            if command in query_lower:
                return True
        
        # Check for music-related queries that should be handled by multimedia service
        music_keywords = [
            "bài hát", "nhạc", "ca khúc", "bản nhạc", "nghe bài", 
            "mở bài", "phát bài", "mở nhạc", "nghe nhạc", "song", 
            "music", "youtube music", "postcast", "story", "album",
            "playlist", "phát", "nghe nhạc", "nghe bài hát", "postcard", "nghe postcast",
            "nghe podcast", "mở video", "video", "nghe video","kể chuyện", "đọc truyện"
        ]
        
        for keyword in music_keywords:
            if keyword in query_lower:
                return True
        
        # Use multimedia service's own detection if available
        if hasattr(self.multimedia_service, 'is_media_command'):
            return self.multimedia_service.is_media_command(query_lower)
            
        return False
    
    def _media_response(self, query):
        """
        Handle multimedia commands for playing music, stories, podcasts, etc.
        
        Args:
            query (str): The user's query
            
        Returns:
            str: Response to the multimedia command
        """
        # If multimedia service isn't available, return a helpful message
        if not self.multimedia_service:
            return "Xin lỗi, dịch vụ phát nhạc và nội dung đa phương tiện không khả dụng."
        
        query_lower = query.lower()
        
        # Handle music search and playback requests
        music_or_video_keywords = [
            "bài hát", "nhạc", "ca khúc", "bản nhạc", "mở bài", "phát bài", "nghe bài",
            "mở video", "nghe video", "video podcast", "podcast", "thư giãn", "video thư giãn", "kể chuyện",
            "đọc truyện", "nghe truyện", "nghe chuyện", "nghe postcast", "nghe podcast",
        ]
        is_media_request = any(keyword in query_lower for keyword in music_or_video_keywords)

        if is_media_request:
            if hasattr(self.multimedia_service, 'process_music_request'):
                return self.multimedia_service.process_music_request(query)
        
        # Process regular media commands
        try:
            result = self.multimedia_service.process_media_command(query)
            
            # Handle the result based on its type
            if isinstance(result, tuple) and len(result) == 2:
                # Expected case: (success, message)
                success, message = result
                return message
            elif isinstance(result, str):
                # In case only a message string is returned
                return result
            else:
                # Fallback for unexpected return type
                logger.warning(f"Unexpected return type from process_media_command: {type(result)}")
                return "Đang xử lý yêu cầu phát nội dung đa phương tiện của bạn."
        except Exception as e:
            logger.error(f"Error processing media command: {str(e)}")
            return f"Xin lỗi, có lỗi khi xử lý yêu cầu đa phương tiện: {str(e)}"
    
    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []
        self.chat = self.model.start_chat(history=[])
        logger.info("Conversation history reset")
        return "Cuộc trò chuyện đã được làm mới."
    
    def get_conversation_history(self):
        """Return the current conversation history."""
        return self.conversation_history

    def analyze_image(self, image_base64, prompt):
        """
        Analyze an image using Gemini Vision capabilities.
        
        Args:
            image_base64 (bytes): Base64-encoded image data
            prompt (str): Text prompt to guide the image analysis
            
        Returns:
            str: The analysis result from Gemini
        """
        return self.generate_response_with_image(prompt, image_base64)
        
    def generate_response_with_image(self, query, image_base64, image_name=None):
        """
        Generate a response that includes analysis of the provided image.
        
        Args:
            query (str): The user's question or prompt
            image_base64 (bytes): Base64-encoded image data
            image_name (str, optional): Name of the image file
            
        Returns:
            str: The AI-generated response analyzing the image
        """
        if not query or not image_base64:
            return "Tôi không thể xử lý yêu cầu này. Vui lòng thử lại với hình ảnh rõ ràng hơn."
        
        # Set flag to indicate we're generating a response
        self.is_generating = True
        self.stop_generation = False
        
        try:
            # Log the query
            logger.info(f"Sending image analysis query to Gemini: {query}")
            
            # Get vision-capable model if available
            vision_models = [
                "gemini-1.5-flash",
                "gemini-1.0-pro-vision", 
                "gemini-1.5-pro-vision",
                "gemini-pro-vision"
            ]
            
            vision_model = None
            
            # Try to find an available vision model
            try:
                available_models = list(genai.list_models())
                for model_name in vision_models:
                    for model in available_models:
                        if model_name in model.name.lower():
                            vision_model = genai.GenerativeModel(
                                model.name,
                                generation_config={
                                    "temperature": 0.3,
                                    "max_output_tokens": 1024,
                                    "top_p": 0.95,
                                }
                            )
                            logger.info(f"Using vision model: {model.name}")
                            break
                    if vision_model:
                        break
            except Exception as e:
                logger.error(f"Error finding vision model: {str(e)}")
            
            # If no vision model available, return an error message
            if not vision_model:
                error_msg = "Xin lỗi, không tìm thấy mô hình hỗ trợ phân tích hình ảnh."
                logger.error("No vision model available")
                self.is_generating = False
                return error_msg
                
            # Create a vision-friendly prompt
            system_prompt = "Hãy phân tích hình ảnh này và trả lời bằng tiếng Việt. Hãy mô tả chi tiết những gì bạn thấy trong hình."
            full_prompt = f"{system_prompt}\n\n{query}"
            
            # Process the image - need to convert from bytes to proper format
            start_time = time.time()
            
            try:
                # Decode base64 to get binary data
                import base64
                from io import BytesIO
                from PIL import Image
                
                # Convert base64 string to bytes
                if isinstance(image_base64, bytes):
                    # If it's already bytes data, decode to string first
                    image_base64_str = image_base64.decode('utf-8')
                else:
                    # If it's already a string
                    image_base64_str = image_base64
                    
                # Remove potential headers from base64 string if present
                if "base64," in image_base64_str:
                    image_base64_str = image_base64_str.split("base64,")[1]
                    
                # Decode base64 to binary
                image_data = base64.b64decode(image_base64_str)
                
                # Create image object
                image = Image.open(BytesIO(image_data))
                
                # Send multipart content to the model
                response = vision_model.generate_content([full_prompt, image])
                
                # Extract the text from the response
                response_text = response.text
                
                # Process the response to fix formatting issues
                response_text = self._format_response(response_text)
                
            except ImportError:
                logger.error("PIL library not installed, using fallback method")
                # Fallback method if PIL is not available
                try:
                    # Try to use native Google AI methods
                    response = vision_model.generate_content([
                        full_prompt,
                        {"mime_type": "image/jpeg", "data": image_base64}
                    ])
                    response_text = response.text
                    response_text = self._format_response(response_text)
                except Exception as inner_e:
                    logger.error(f"Error in fallback image processing: {str(inner_e)}")
                    response_text = "Xin lỗi, tôi gặp khó khăn khi xử lý hình ảnh này. Vui lòng thử lại hoặc mô tả hình ảnh."
            
            # Calculate response time
            end_time = time.time()
            response_time = end_time - start_time
            logger.info(f"Gemini image analysis response received in {response_time:.2f} seconds")
            
            # Check if we were asked to stop
            if self.stop_generation:
                self.is_generating = False
                return "Phân tích hình ảnh bị dừng lại."
            
            # Update conversation history with image context
            image_context = f"[Đã gửi hình ảnh{': ' + image_name if image_name else ''}]"
            self.conversation_history.append({"role": "user", "content": f"{image_context} {query}"})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Trim history if needed
            if len(self.conversation_history) > self.max_history_length * 2:
                self.conversation_history = self.conversation_history[-self.max_history_length*2:]
            
            # Log the conversation
            logger.log_conversation(f"{image_context} {query}", response_text)
            
            # Reset generating flag
            self.is_generating = False
            return response_text
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            self.is_generating = False
            return f"Xin lỗi, có lỗi khi phân tích hình ảnh: {str(e)}"
    
    def _is_led_control_command(self, query_lower):
        """
        Check if a query is related to LED control.
        
        Args:
            query_lower (str): Lowercase query string
            
        Returns:
            bool: True if this is an LED control command
        """
        led_patterns = [
            "bật đèn", "tắt đèn", 
            "bật led", "tắt led",
            "bật đèn đỏ", "tắt đèn đỏ",
            "bật đèn vàng", "tắt đèn vàng", 
            "bật đèn xanh", "tắt đèn xanh",
            "bật tất cả đèn", "tắt tất cả đèn",
            "bật cả ba đèn", "tắt cả ba đèn",
            "bật 3 đèn", "tắt 3 đèn",
            "bật hai đèn", "tắt hai đèn",
            "bật 2 đèn", "tắt 2 đèn",
            "bật đèn đỏ và vàng",
            "bật đèn đỏ và xanh",
            "bật đèn vàng và xanh"
        ]
        
        for pattern in led_patterns:
            if pattern in query_lower:
                return True
                
        return False
    def _handle_led_command(self, query):
        """
        Handle LED control commands.
        """
        try:
            if not self.hardware_interface:
                return "Xin lỗi, tôi không thể kết nối với phần cứng để điều khiển đèn LED."

            query_lower = query.lower()
            
            # Handle turn off commands first
            if "tắt tất cả" in query_lower or "tắt cả ba" in query_lower or "tắt 3" in query_lower:
                self.hardware_interface.turn_off_all_leds()
                return "Đã tắt tất cả đèn LED."
            
            # Handle turn on commands
            if "bật tất cả" in query_lower or "bật cả ba" in query_lower or "bật 3" in query_lower:
                self.hardware_interface.turn_on_all_leds()
                return "Đã bật tất cả đèn LED."
            
            # Handle specific LED combinations
            if "đỏ và vàng" in query_lower:
                if "tắt" in query_lower:
                    self.hardware_interface.set_led_state(red=False, yellow=False, green=None)
                    return "Đã tắt đèn LED đỏ và vàng."
                else:
                    self.hardware_interface.turn_on_red_yellow_leds()
                    return "Đã bật đèn LED đỏ và vàng."
            
            elif "đỏ và xanh" in query_lower:
                if "tắt" in query_lower:
                    self.hardware_interface.set_led_state(red=False, yellow=None, green=False)
                    return "Đã tắt đèn LED đỏ và xanh."
                else:
                    self.hardware_interface.turn_on_red_green_leds()
                    return "Đã bật đèn LED đỏ và xanh."
            
            elif "vàng và xanh" in query_lower:
                if "tắt" in query_lower:
                    self.hardware_interface.set_led_state(red=None, yellow=False, green=False)
                    return "Đã tắt đèn LED vàng và xanh."
                else:
                    self.hardware_interface.turn_on_yellow_green_leds()
                    return "Đã bật đèn LED vàng và xanh."
            
            # Handle individual LED commands
            elif "đỏ" in query_lower:
                if "tắt" in query_lower:
                    self.hardware_interface.set_led_state(red=False, yellow=None, green=None)
                    return "Đã tắt đèn LED đỏ."
                else:
                    self.hardware_interface.turn_on_red_led()
                    return "Đã bật đèn LED đỏ."
            
            elif "vàng" in query_lower:
                if "tắt" in query_lower:
                    self.hardware_interface.set_led_state(red=None, yellow=False, green=None)
                    return "Đã tắt đèn LED vàng."
                else:
                    self.hardware_interface.turn_on_yellow_led()
                    return "Đã bật đèn LED vàng."
            
            elif "xanh" in query_lower:
                if "tắt" in query_lower:
                    self.hardware_interface.set_led_state(red=None, yellow=None, green=False)
                    return "Đã tắt đèn LED xanh."
                else:
                    self.hardware_interface.turn_on_green_led()
                    return "Đã bật đèn LED xanh."
            
            # Handle simple on/off commands
            elif "bật đèn" in query_lower or "bật led" in query_lower:
                self.hardware_interface.turn_on_all_leds()
                return "Đã bật tất cả đèn LED."
            
            elif "tắt đèn" in query_lower or "tắt led" in query_lower:
                self.hardware_interface.turn_off_all_leds()
                return "Đã tắt tất cả đèn LED."
            
            return "Tôi không hiểu lệnh điều khiển đèn LED. Vui lòng thử lại với câu lệnh rõ ràng hơn."
        
        except Exception as e:
            logger.error(f"Error handling LED command: {str(e)}")
            return "Xin lỗi, đã xảy ra lỗi khi điều khiển đèn LED."

    def _handle_time_queries(self, text):
        """Handle time queries."""
        # Check for time-related queries
        if "mấy giờ" in text.lower():
            current_time = datetime.now().strftime("%H:%M")
            return f"Bây giờ là {current_time}"
        
        return None
    
    def _is_lcd_command(self, query_lower):
        """Check if query is an LCD display command."""
        lcd_keywords = [
            "hiển thị lcd", "hiển thị màn hình", "lcd hiển thị", "lcd display",
            "ghi lên lcd", "ghi lên màn hình", "hiển thị lên lcd", "hiển thị lên màn hình",
            "lcd ghi", "màn hình ghi", "lcd show", "màn hình hiển thị",
            "xuất ra lcd", "xuất ra màn hình", "đưa lên lcd", "đưa lên màn hình",
            "lcd text", "lcd message", "thông điệp lcd", "tin nhắn lcd",
            "clear lcd", "xóa lcd", "xóa màn hình", "dọn màn hình",
            "tắt lcd", "stop lcd", "dừng lcd", "dừng màn hình"
        ]
        
        return any(keyword in query_lower for keyword in lcd_keywords)
    
    def _lcd_response(self, query):
        """
        Handle LCD display commands.
        
        Args:
            query (str): The user's query
            
        Returns:
            str: Response to the LCD command
        """
        if not self.lcd_service:
            return "Xin lỗi, dịch vụ màn hình LCD không khả dụng."
            
        try:
            result = self.lcd_service.process_voice_command(query)
            if result:
                return "Đã xử lý lệnh màn hình LCD thành công."
            else:
                return "Tôi không hiểu lệnh LCD. Bạn có thể nói 'hiển thị lên LCD [nội dung]' hoặc 'xóa màn hình LCD'."
        except Exception as e:
            logger.error(f"Error processing LCD command: {str(e)}")
            return f"Xin lỗi, có lỗi khi xử lý lệnh LCD: {str(e)}"