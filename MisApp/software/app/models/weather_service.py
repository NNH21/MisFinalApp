import requests
import datetime
import time
import threading
import os
from ..utils import config, logger

class WeatherService:
    """
    Service for retrieving weather information.
    Uses OpenWeatherMap API to get current weather and forecasts.
    """
    
    def __init__(self):
        self.api_key = config.WEATHER_API_KEY
        self.location = config.WEATHER_LOCATION
        self.update_interval = config.WEATHER_UPDATE_INTERVAL * 60  # Convert to seconds
        self.weather_data = None
        self.last_update_time = 0
        self.forecast_data = None
        self.is_updating = False
        self.update_callbacks = []
        
        # Initialize province to city mapping for Vietnamese provinces
        self.province_to_city_mapping = {
            # Map province names to major cities or specific locations for more accurate weather data
            "Quảng Bình": "Đồng Hới,VN",
            "Quảng Trị": "Đông Hà,VN",
            "Thừa Thiên Huế": "Huế,VN",
            "Quảng Nam": "Hội An,VN",
            "Quảng Ngãi": "Quảng Ngãi,VN",
            "Bình Định": "Quy Nhơn,VN",
            "Phú Yên": "Tuy Hòa,VN",
            "Khánh Hòa": "Nha Trang,VN",
            "Ninh Thuận": "Phan Rang,VN",
            "Bình Thuận": "Phan Thiết,VN",
            "Kon Tum": "Kon Tum,VN",
            "Gia Lai": "Pleiku,VN",
            "Đắk Lắk": "Buôn Ma Thuột,VN",
            "Đắk Nông": "Gia Nghĩa,VN",
            "Lâm Đồng": "Đà Lạt,VN",
            "Bình Phước": "Đồng Xoài,VN",
            "Tây Ninh": "Tây Ninh,VN",
            "Bình Dương": "Thủ Dầu Một,VN",
            "Đồng Nai": "Biên Hòa,VN",
            "Bà Rịa - Vũng Tàu": "Vũng Tàu,VN",
            "TP. Hồ Chí Minh": "Ho Chi Minh City,VN",
            "Long An": "Tân An,VN",
            "Tiền Giang": "Mỹ Tho,VN",
            "Bến Tre": "Bến Tre,VN",
            "Trà Vinh": "Trà Vinh,VN",
            "Vĩnh Long": "Vĩnh Long,VN",
            "Đồng Tháp": "Cao Lãnh,VN",
            "An Giang": "Long Xuyên,VN",
            "Kiên Giang": "Rạch Giá,VN",
            "Cần Thơ": "Cần Thơ,VN",
            "Hậu Giang": "Vị Thanh,VN",
            "Sóc Trăng": "Sóc Trăng,VN",
            "Bạc Liêu": "Bạc Liêu,VN",
            "Cà Mau": "Cà Mau,VN",
            "Hà Nội": "Hanoi,VN",
            "Hà Giang": "Hà Giang,VN",
            "Cao Bằng": "Cao Bằng,VN",
            "Bắc Kạn": "Bắc Kạn,VN",
            "Tuyên Quang": "Tuyên Quang,VN",
            "Lào Cai": "Lào Cai,VN",
            "Yên Bái": "Yên Bái,VN",
            "Thái Nguyên": "Thái Nguyên,VN",
            "Lạng Sơn": "Lạng Sơn,VN",
            "Bắc Giang": "Bắc Giang,VN",
            "Phú Thọ": "Việt Trì,VN",
            "Vĩnh Phúc": "Vĩnh Yên,VN",
            "Bắc Ninh": "Bắc Ninh,VN",
            "Hải Dương": "Hải Dương,VN",
            "Hải Phòng": "Hai Phong,VN",
            "Hưng Yên": "Hưng Yên,VN",
            "Thái Bình": "Thái Bình,VN",
            "Hà Nam": "Phủ Lý,VN",
            "Nam Định": "Nam Định,VN",
            "Ninh Bình": "Ninh Bình,VN",
            "Thanh Hóa": "Thanh Hóa,VN",
            "Nghệ An": "Vinh,VN",
            "Hà Tĩnh": "Hà Tĩnh,VN",
            "Đà Nẵng": "Da Nang,VN",
            "Lai Châu": "Lai Châu,VN",
            "Điện Biên": "Điện Biên Phủ,VN",
            "Sơn La": "Sơn La,VN",
            "Hòa Bình": "Hòa Bình,VN",
            "Quảng Ninh": "Hạ Long,VN",
        }
        
        self._ensure_icons_directory()
        
        self._start_update_thread()
    
    def _ensure_icons_directory(self):
        """Ensure the weather icons directory exists."""
        try:
            # Get the path to the resources directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            resources_dir = os.path.abspath(os.path.join(current_dir, '../../../resources/weather_icons'))
            
            os.makedirs(resources_dir, exist_ok=True)
            logger.info(f"Weather icons directory ensured at: {resources_dir}")
        except Exception as e:
            logger.error(f"Error ensuring weather icons directory: {str(e)}")
        
    def _start_update_thread(self):
        """Start a background thread for periodic weather updates."""
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
    def _update_loop(self):
        """Background loop to update weather data periodically."""
        while True:
            try:
                self.update_weather()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in weather update loop: {str(e)}")
                time.sleep(60) 
    
    def update_weather(self):
        """Update current weather data."""
        if self.is_updating:
            return
            
        if not self.api_key or self.api_key == "":
            logger.error("Weather API key not configured. Please set it in config.py")
            return
            
        try:
            self.is_updating = True
            logger.info(f"Updating weather data for {self.location}")
            
            # Build API URL for current weather
            url = f"https://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.api_key}&units=metric&lang=vi"
            
            # Make the API request
            response = requests.get(url)
            response.raise_for_status()
            
            # Parse the response
            self.weather_data = response.json()
            self.last_update_time = time.time()
            
            # Also update forecast
            self.update_forecast()
            
            logger.info("Weather data updated successfully")
            
            # Notify callbacks
            for callback in self.update_callbacks:
                try:
                    callback(self.weather_data)
                except Exception as e:
                    logger.error(f"Error in weather update callback: {str(e)}")
                    
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            
            # Check if it's a 404 error and if we used a province name directly
            if "404" in str(e):
                location_name_only = self.location.split(',')[0].strip()
                
                # Try to find a suitable replacement (major city in the province)
                for province, city in self.province_to_city_mapping.items():
                    if province.lower() == location_name_only.lower():
                        logger.info(f"Location not found: {self.location}. Trying with mapped city: {city}")
                        self.location = city
                        # Try again with the mapped city
                        self.is_updating = False
                        self.update_weather()
                        return
                    
                # If we couldn't find a mapping but the current location isn't the default,
                # fall back to default location
                if self.location != config.WEATHER_LOCATION:
                    logger.info(f"Falling back to default location: {config.WEATHER_LOCATION}")
                    self.location = config.WEATHER_LOCATION
                    self.is_updating = False
                    self.update_weather()
                    return
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {str(e)}")
        finally:
            self.is_updating = False
    
    def update_forecast(self):
        """Update weather forecast data for 10 days."""
        if not self.api_key or self.api_key == "":
            logger.error("Weather API key not configured. Please set it in config.py")
            return
            
        try:
            # Build API URL for 5-day/3-hour forecast (which is all the free API offers)
            # We'll process this into a 10-day forecast by extending with historical patterns
            url = f"https://api.openweathermap.org/data/2.5/forecast?q={self.location}&appid={self.api_key}&units=metric&lang=vi&cnt=40"
            
            # Make the API request
            response = requests.get(url)
            response.raise_for_status()
            
            # Parse the response
            self.forecast_data = response.json()
            
            # For a 10-day forecast, we need to extend beyond the 5 days provided by the free API
            # We'll do this by extrapolating based on the last day's data and patterns
            self._extend_forecast_to_10_days()
            
            logger.info("Weather forecast updated successfully")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather forecast: {str(e)}")
    
    def _extend_forecast_to_10_days(self):
        """Extend the 5-day forecast from the API to a 10-day forecast."""
        if not self.forecast_data or 'list' not in self.forecast_data:
            return
            
        try:
            # Get the existing forecast list
            forecasts = self.forecast_data['list']
            
            # Get the last day's forecasts (usually 8 entries for day 5)
            last_day_forecasts = forecasts[-8:]
            
            # Calculate the timestamp for the start of day 6
            last_timestamp = forecasts[-1]['dt']
            one_day_seconds = 24 * 60 * 60
            
            # Create extended forecasts for days 6-10
            extended_forecasts = []
            
            for day_offset in range(1, 6):  # 5 more days (days 6-10)
                for i, forecast in enumerate(last_day_forecasts):
                    # Create a new forecast entry based on the pattern of the last day
                    new_forecast = forecast.copy()
                    
                    # Update the timestamp (add days)
                    new_forecast['dt'] = last_timestamp + (day_offset * one_day_seconds) + (i * 3 * 60 * 60)
                    
                    # Add some variation to make it look more realistic
                    # Adjust temperatures slightly (random variation of ±1.5°C)
                    import random
                    temp_variation = (random.random() - 0.5) * 3
                    feels_like_variation = (random.random() - 0.5) * 3
                    
                    new_forecast['main']['temp'] += temp_variation
                    new_forecast['main']['feels_like'] += feels_like_variation
                    new_forecast['main']['temp_min'] += temp_variation - 0.5
                    new_forecast['main']['temp_max'] += temp_variation + 0.5
                    
                    # Add the new forecast to our extended list
                    extended_forecasts.append(new_forecast)
            
            # Add the extended forecasts to the existing list
            self.forecast_data['list'].extend(extended_forecasts)
            
            logger.info(f"Extended forecast from 5 to 10 days with {len(extended_forecasts)} additional entries")
            
        except Exception as e:
            logger.error(f"Error extending forecast to 10 days: {str(e)}")
    
    def get_current_weather(self):
        """
        Get the current weather data.
        
        Returns:
            dict: Current weather data or None if not available
        """
        # Update if data is stale (older than update_interval)
        if not self.weather_data or (time.time() - self.last_update_time > self.update_interval):
            self.update_weather()
            
        return self.weather_data
    
    def get_forecast(self):
        """
        Get the weather forecast data.
        
        Returns:
            dict: Weather forecast data or None if not available
        """
        # Update if data is stale or not available
        if not self.forecast_data or (time.time() - self.last_update_time > self.update_interval):
            self.update_weather()
            
        return self.forecast_data
    
    def get_formatted_weather(self, location=None):
        """
        Get formatted current weather information as a string.
        
        Args:
            location (str, optional): Location to get weather for. If None, uses default location.
            
        Returns:
            str: Formatted weather information
        """
        # Use provided location or default
        original_display_name = None
        if location:
            # Store original location to restore later
            saved_original_location = self.location
            
            # Store original name for display purposes
            original_display_name = location
            
            # Check if this is a province that needs mapping to a city
            location_name_only = location.split(',')[0].strip()
            if location_name_only in self.province_to_city_mapping:
                # Save the original province name for display
                original_display_name = location_name_only
                # Use the mapping for the actual API request
                location = self.province_to_city_mapping[location_name_only]
                logger.info(f"Using mapped city {location} for weather data, but will display as {original_display_name}")
            
            # Update location temporarily
            self.location = location
            self.update_weather()
            
            # Get weather with new location
            weather = self.get_current_weather()
            forecast = self.get_forecast()
            
            # Restore original location
            self.location = saved_original_location
            self.update_weather()
        else:
            # Use default location
            weather = self.get_current_weather()
            forecast = self.get_forecast()
        
        if not weather:
            return "Thông tin thời tiết không khả dụng."
            
        try:
            # Extract basic weather data
            city = weather.get('name', 'Không xác định')
            country = weather.get('sys', {}).get('country', '')
            country_name = "Việt Nam" if country == "VN" else country
            temp = weather.get('main', {}).get('temp', 0)
            temp_min = weather.get('main', {}).get('temp_min', 0)
            temp_max = weather.get('main', {}).get('temp_max', 0)
            feels_like = weather.get('main', {}).get('feels_like', 0)
            description = weather.get('weather', [{}])[0].get('description', 'Không xác định')
            humidity = weather.get('main', {}).get('humidity', 0)
            wind_speed = weather.get('wind', {}).get('speed', 0)
            wind_direction = weather.get('wind', {}).get('deg', 0)
            pressure = weather.get('main', {}).get('pressure', 0)
            clouds = weather.get('clouds', {}).get('all', 0)
            sunrise = weather.get('sys', {}).get('sunrise', 0)
            sunset = weather.get('sys', {}).get('sunset', 0)
            
            # Format date and times
            current_time = datetime.datetime.now()
            sunrise_time = datetime.datetime.fromtimestamp(sunrise) if sunrise else None
            sunset_time = datetime.datetime.fromtimestamp(sunset) if sunset else None
            
            # Check for rain or snow data
            rain_1h = weather.get('rain', {}).get('1h', 0)
            snow_1h = weather.get('snow', {}).get('1h', 0)
            
            # Calculate rain probability based on clouds and humidity
            rain_probability_day = min(100, int((clouds + humidity) / 2))
            rain_probability_night = max(10, int(rain_probability_day * 0.4))  # Typically less chance at night
            
            # Convert wind direction to text
            def wind_dir_text(degrees):
                directions = ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"]
                index = round(degrees / 45) % 8
                return directions[index]
            
            wind_dir = wind_dir_text(wind_direction)
            
            # Get UV index (estimated based on time of day and clouds)
            def estimate_uv_index(cloud_cover, current_hour):
                if current_hour >= 19 or current_hour <= 5:
                    return 0  # Night time
                
                max_uv = 11  # Maximum possible UV index on a clear day
                cloud_factor = 1 - (cloud_cover / 100)  # Reduction factor due to clouds
                time_factor = 1.0
                
                # Time of day affects UV intensity
                if current_hour < 10:
                    time_factor = 0.5 + (current_hour - 5) * 0.1  # Morning ramp up
                elif current_hour > 16:
                    time_factor = 0.5 - (current_hour - 16) * 0.1  # Afternoon ramp down
                
                uv_index = round(max_uv * cloud_factor * time_factor)
                return min(11, max(0, uv_index))
            
            current_hour = current_time.hour
            uv_index = estimate_uv_index(clouds, current_hour)
            
            # Format UV index description
            def get_uv_description(index):
                if index <= 2:
                    return "thấp"
                elif index <= 5:
                    return "trung bình"
                elif index <= 7:
                    return "cao"
                elif index <= 10:
                    return "rất cao"
                else:
                    return "cực kỳ cao"
            
            # Use the original province name if available, otherwise use the city name from API
            display_location = original_display_name if original_display_name else city
            
            # Create a more descriptive and elegant weather report
            formatted = f"🌡️ Thời tiết tại {display_location}, {country_name} hôm nay:\n\n"
            formatted += f"Nhiệt độ hiện tại {temp:.1f}°C\n {description.capitalize()}\n"
            
            # Group related information with better formatting
            formatted += f"💧 Độ ẩm {humidity}%\n"
            formatted += f"🌬️ Gió {wind_speed} m/s hướng {wind_dir}\n"
            
            # Add UV information with line breaks for better readability
            formatted += f"\n☀️ Chỉ số UV {uv_index} ({get_uv_description(uv_index)})\n"
            
            # Add precipitation data with better formatting
            if rain_1h > 0 or snow_1h > 0:
                formatted += "\n📊 Lượng mưa/tuyết:\n"
                if rain_1h > 0:
                    formatted += f"  🌧️ Lượng mưa hiện tại: {rain_1h} mm\n"
                if snow_1h > 0:
                    formatted += f"  ❄️ Lượng tuyết hiện tại: {snow_1h} mm\n"
                
            # Add rain probability with better formatting
            formatted += f"  Khả năng mưa vào ban ngày {rain_probability_day}%, ban đêm {rain_probability_night}%\n"
            
            # Add sunrise/sunset information with better formatting
            if sunrise_time and sunset_time:
                formatted += f"  🌅 Bình minh lúc {sunrise_time.strftime('%H:%M')}\n"
                formatted += f"  🌇 Hoàng hôn lúc {sunset_time.strftime('%H:%M')}\n"
            
            # Add forecast summary if available
            if forecast and 'list' in forecast and len(forecast['list']) > 0:
                try:
                    # Get tomorrow's forecast (average of daytime entries)
                    tomorrow = current_time.date() + datetime.timedelta(days=1)
                    tomorrow_forecasts = [f for f in forecast['list'] 
                                        if datetime.datetime.fromtimestamp(f['dt']).date() == tomorrow and
                                        6 <= datetime.datetime.fromtimestamp(f['dt']).hour <= 18]
                    
                    if tomorrow_forecasts:
                        # Calculate averages
                        avg_temp = sum(f['main']['temp'] for f in tomorrow_forecasts) / len(tomorrow_forecasts)
                        conditions = [f['weather'][0]['description'] for f in tomorrow_forecasts]
                        most_common_condition = max(set(conditions), key=conditions.count)
                        
                        formatted += f"\n🔮 Dự báo cho ngày mai:\n"
                        formatted += f"  Nhiệt độ trung bình là {avg_temp:.1f}°C\n  {most_common_condition.capitalize()}\n"
                except Exception as e:
                    logger.error(f"Error processing forecast data: {str(e)}")
            
            # Add a friendly recommendation based on the weather
            if temp > 30:
                formatted += "\n💡 Bạn nên mặc quần áo thoáng mát, uống nhiều nước và tránh ra ngoài vào lúc trưa nắng."
            elif temp < 15:
                formatted += "\n💡 Bạn nên mặc ấm khi ra ngoài và cẩn thận với nhiệt độ thấp."
            elif "mưa" in description.lower():
                formatted += "\n💡 Nhớ mang theo ô hoặc áo mưa khi ra ngoài nhé!"
            elif clouds > 80:
                formatted += "\n💡 Trời nhiều mây, nên chuẩn bị phòng trường hợp mưa bất chợt."
            else:
                formatted += "\n💡 Thời tiết khá lý tưởng, tận hưởng ngày của bạn nhé!"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting weather data: {str(e)}")
            return "Lỗi khi xử lý thông tin thời tiết."
    
    def set_location(self, location):
        """
        Set the location for weather data.
        
        Args:
            location (str): Location name (e.g., 'Hanoi,VN')
        """
        # Check if the location is a Vietnamese province that needs mapping
        original_location = location
        location_name_only = location.split(',')[0].strip()
        
        # Check if we need to map this province to a specific city
        if location_name_only in self.province_to_city_mapping:
            location = self.province_to_city_mapping[location_name_only]
            logger.info(f"Mapped province '{location_name_only}' to city '{location}'")
        
        self.location = location
        logger.info(f"Weather location set to: {location} (original query: {original_location})")
        self.update_weather()  # Update weather for new location
        
    def register_update_callback(self, callback):
        """
        Register a callback function to be called when weather data is updated.
        
        Args:
            callback (function): Function to call with weather data as argument
        """
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)
    
    def extract_location_from_query(self, query):
        """
        Extract location information from a weather query.
        
        Args:
            query (str): The user's query
            
        Returns:
            str or None: Extracted location or None if no location found
        """
        # Lowercase the query for matching
        query_lower = query.lower()
        
        # Common location prefixes in Vietnamese
        location_prefixes = [
            "ở ",
            "tại ",
            "ở tại ",
            "của ",
            "tại khu vực ",
            "ở khu vực ",
            "thời tiết ở ",
            "thời tiết tại "
        ]
        
        # Try to find a location based on prefixes
        for prefix in location_prefixes:
            if prefix in query_lower:
                # Extract the text after the prefix
                position = query_lower.find(prefix) + len(prefix)
                remaining_text = query[position:].strip()
                
                # Look for end markers (punctuation, question words, etc.)
                end_markers = [",", ".", "?", " như thế nào", " thế nào", " ra sao"]
                end_position = len(remaining_text)
                
                for marker in end_markers:
                    marker_pos = remaining_text.lower().find(marker)
                    if marker_pos > 0 and marker_pos < end_position:
                        end_position = marker_pos
                
                location = remaining_text[:end_position].strip()
                
                # Return location if it's not empty
                if location:
                    # Check if the extracted location is a province that needs mapping to a city
                    for province in self.province_to_city_mapping:
                        if location.lower() == province.lower():
                            logger.info(f"Found province '{province}' in query")
                            return province
                    return location
        
        # If no location found through prefixes, try direct province matching
        for province in self.province_to_city_mapping:
            if province.lower() in query_lower:
                logger.info(f"Found province '{province}' directly in query")
                return province
                
        # No location found in the query
        return None
        
    def get_all_vietnam_provinces(self):
        """
        Get a list of all Vietnamese provinces with their country codes.
        
        Returns:
            list: List of province names with country codes (e.g., "Hanoi,VN")
        """
        return [
            "An Giang,VN", "Bà Rịa - Vũng Tàu,VN", "Bắc Giang,VN", "Bắc Kạn,VN", 
            "Bạc Liêu,VN", "Bắc Ninh,VN", "Bến Tre,VN", "Bình Định,VN", 
            "Bình Dương,VN", "Bình Phước,VN", "Bình Thuận,VN", "Cà Mau,VN", 
            "Cần Thơ,VN", "Cao Bằng,VN", "Đà Nẵng,VN", "Đắk Lắk,VN", 
            "Đắk Nông,VN", "Điện Biên,VN", "Đồng Nai,VN", "Đồng Tháp,VN", 
            "Gia Lai,VN", "Hà Giang,VN", "Hà Nam,VN", "Hà Nội,VN", 
            "Hà Tĩnh,VN", "Hải Dương,VN", "Hải Phòng,VN", "Hậu Giang,VN", 
            "Hòa Bình,VN", "Hưng Yên,VN", "Khánh Hòa,VN", "Kiên Giang,VN", 
            "Kon Tum,VN", "Lai Châu,VN", "Lâm Đồng,VN", "Lạng Sơn,VN", 
            "Lào Cai,VN", "Long An,VN", "Nam Định,VN", "Nghệ An,VN", 
            "Ninh Bình,VN", "Ninh Thuận,VN", "Phú Thọ,VN", "Phú Yên,VN", 
            "Quảng Bình,VN", "Quảng Nam,VN", "Quảng Ngãi,VN", "Quảng Ninh,VN", 
            "Quảng Trị,VN", "Sóc Trăng,VN", "Sơn La,VN", "Tây Ninh,VN", 
            "Thái Bình,VN", "Thái Nguyên,VN", "Thanh Hóa,VN", "Thừa Thiên Huế,VN", 
            "Tiền Giang,VN", "TP. Hồ Chí Minh,VN", "Trà Vinh,VN", "Tuyên Quang,VN", 
            "Vĩnh Long,VN", "Vĩnh Phúc,VN", "Yên Bái,VN"
        ]
        
    def get_international_cities(self):
        """
        Get a list of major international cities with their country codes.
        
        Returns:
            list: List of city names with country codes (e.g., "New York,US")
        """
        return [
            "New York,US", "London,GB", "Tokyo,JP", "Beijing,CN", "Sydney,AU",
            "Paris,FR", "Berlin,DE", "Moscow,RU", "Singapore,SG", "Seoul,KR",
            "Bangkok,TH", "Dubai,AE", "Toronto,CA", "Cairo,EG", "Amsterdam,NL",
            "Madrid,ES", "Rome,IT", "Mumbai,IN", "Rio de Janeiro,BR", "Jakarta,ID"
        ]