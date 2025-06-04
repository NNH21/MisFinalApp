import requests
import datetime
import pytz
import time
import threading
import uuid
import os
import pygame
from PyQt5.QtCore import QTime, QDate
from ..utils import config, logger

class TimeService:
    """
    Service for retrieving and managing time information from various timezones.
    Uses TimezoneDB API to get current time for different locations around the world.
    Also manages alarms with sound notification.
    """
    
    def __init__(self, hardware_interface=None):
        self.api_key = config.TIMEZONE_API_KEY
        self.base_url = "http://api.timezonedb.com/v2.1/get-time-zone"
        self.default_location = "Việt Nam"
        self.default_timezone = "Asia/Ho_Chi_Minh"
        self.update_interval = 3600 
        self.cache = {}  
        self.last_update_time = {}  
        
        # Hardware interface reference
        self.hardware_interface = hardware_interface
        
        # Clock display state
        self.is_showing_clock = False
        self.clock_update_thread = None
        self.stop_clock_thread = False
        
        # Alarm functionality
        self.alarms = {}  
        self.is_alarm_ringing = False
        self.current_ringing_alarm = None
        self.snooze_timer = None
        self.snooze_count = 0
        self.max_snooze_count = 3  
        
        # Initialize pygame for alarm sound
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init()
                logger.info("Pygame mixer initialized for alarms")
            except Exception as e:
                logger.error(f"Failed to initialize pygame mixer for alarms: {str(e)}")
                
        # Load alarm sounds
        self.alarm_sounds = {
            "Báo thức thông thường": "alarm.mp3",
            "Báo thức dần dần": "gradual_alarm.mp3",
            "Báo thức rung": "vibration_alarm.mp3",
            "Báo thức nhạc": "music_alarm.mp3"
        }
        
        # Initialize volume control
        self.volume = 0.7  
        self.volume_step = 0.1  
        
        self.locations = {
            "Việt Nam": {"lat": 21.0278, "lng": 105.8342},  # Hanoi
            "New York": {"lat": 40.7128, "lng": -74.0060},
            "London": {"lat": 51.5074, "lng": -0.1278},
            "Tokyo": {"lat": 35.6762, "lng": 139.6503},
            "Sydney": {"lat": -33.8688, "lng": 151.2093},
            "Paris": {"lat": 48.8566, "lng": 2.3522},
            "Berlin": {"lat": 52.5200, "lng": 13.4050},
            "Moscow": {"lat": 55.7558, "lng": 37.6173},
            "Dubai": {"lat": 25.2048, "lng": 55.2708},
            "Los Angeles": {"lat": 34.0522, "lng": -118.2437},
            "Bangkok": {"lat": 13.7563, "lng": 100.5018},
            "Singapore": {"lat": 1.3521, "lng": 103.8198},
            "Beijing": {"lat": 39.9042, "lng": 116.4074},
            "Cairo": {"lat": 30.0444, "lng": 31.2357}
        }
        
        # Timezone mappings (from common names to IANA timezone identifiers)
        self.timezone_mappings = {
            "việt nam": "Asia/Ho_Chi_Minh",
            "vietnam": "Asia/Ho_Chi_Minh",
            "hanoi": "Asia/Ho_Chi_Minh",
            "hà nội": "Asia/Ho_Chi_Minh",
            "ho chi minh": "Asia/Ho_Chi_Minh",
            "hồ chí minh": "Asia/Ho_Chi_Minh",
            "saigon": "Asia/Ho_Chi_Minh",
            "sài gòn": "Asia/Ho_Chi_Minh",
            "new york": "America/New_York",
            "london": "Europe/London",
            "tokyo": "Asia/Tokyo",
            "sydney": "Australia/Sydney",
            "paris": "Europe/Paris",
            "berlin": "Europe/Berlin",
            "moscow": "Europe/Moscow",
            "dubai": "Asia/Dubai",
            "los angeles": "America/Los_Angeles",
            "bangkok": "Asia/Bangkok",
            "singapore": "Asia/Singapore",
            "beijing": "Asia/Shanghai",
            "cairo": "Africa/Cairo"
        }
        
    def get_current_time(self, location=None):
        """
        Get the current time for a specific location.
        
        Args:
            location (str, optional): Location name. Defaults to None (uses default location).
            
        Returns:
            dict: Time information including formatted time, timezone, etc.
        """
        # If no location specified, use default
        if not location:
            location = self.default_location
            
        # Standardize location name (lowercase for matching)
        location_lower = location.lower()
        
        # Try to find the timezone from our mappings
        timezone_id = None
        for loc_name, tz_id in self.timezone_mappings.items():
            if loc_name in location_lower:
                timezone_id = tz_id
                break
                
        # If we found a direct timezone mapping, use pytz to get the time
        if timezone_id:
            try:
                now = datetime.datetime.now(pytz.timezone(timezone_id))
                return {
                    "success": True,
                    "location": location,
                    "formatted": now.strftime("%H:%M:%S"),
                    "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "timezone": timezone_id,
                    "timezone_offset": int(now.utcoffset().total_seconds() / 3600),
                    "source": "local"
                }
            except Exception as e:
                logger.error(f"Error getting time for {location} using pytz: {str(e)}")
        
        # If we couldn't match to a known timezone, try the API
        return self._get_time_from_api(location)
    
    def _get_time_from_api(self, location):
        """
        Get time information from TimezoneDB API for a location.
        
        Args:
            location (str): Location name
            
        Returns:
            dict: Time information or error message
        """
        if not self.api_key or self.api_key == "YOUR_TIMEZONE_API_KEY":
            logger.error("TimezoneDB API key not configured. Please set it in config.py")
            return {"success": False, "error": "API key not configured"}
            
        # Check if we have coordinates for this location
        location_lower = location.lower()
        coordinates = None
        
        for loc_name, coords in self.locations.items():
            if loc_name.lower() in location_lower:
                coordinates = coords
                break
                
        # If we don't have coordinates, return an error
        if not coordinates:
            return {
                "success": False, 
                "error": f"Unknown location: {location}"
            }
            
        # Check if we have a recent cache entry
        cache_key = f"{coordinates['lat']},{coordinates['lng']}"
        current_time = time.time()
        
        if (cache_key in self.cache and 
            cache_key in self.last_update_time and 
            current_time - self.last_update_time[cache_key] < self.update_interval):
            # Return cached data
            return self.cache[cache_key]
            
        try:
            # Build API request
            params = {
                "key": self.api_key,
                "format": "json",
                "by": "position",
                "lat": coordinates["lat"],
                "lng": coordinates["lng"]
            }
            
            # Make API request
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Process the response
            if data["status"] == "OK":
                result = {
                    "success": True,
                    "location": location,
                    "formatted": datetime.datetime.fromtimestamp(data["timestamp"]).strftime("%H:%M:%S"),
                    "datetime": datetime.datetime.fromtimestamp(data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"),
                    "timezone": data["zoneName"],
                    "timezone_offset": data["gmtOffset"] / 3600,
                    "source": "api"
                }
                
                # Cache the result
                self.cache[cache_key] = result
                self.last_update_time[cache_key] = current_time
                
                return result
            else:
                logger.error(f"API error for {location}: {data.get('message', 'Unknown error')}")
                return {"success": False, "error": data.get("message", "Unknown error")}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {location}: {str(e)}")
            return {"success": False, "error": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error for {location}: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def get_location_from_query(self, query):
        """
        Extract location information from a query string.
        
        Args:
            query (str): Query text (e.g., "What time is it in London?")
            
        Returns:
            str or None: Extracted location or None if not found
        """
        query_lower = query.lower()
        
        # Check for "in {location}" pattern
        if "in " in query_lower:
            location_part = query_lower.split("in ", 1)[1]
            # Remove question marks and other punctuation
            location_part = location_part.strip("?!.,;: ")
            return location_part
            
        # Check for direct mentions of locations
        for location in self.timezone_mappings.keys():
            if location.lower() in query_lower:
                return location
                
        # If no location mentioned, return None (to use default)
        return None
        
    def format_time_response(self, location=None):
        """
        Generate a formatted response about current time for a location.
        
        Args:
            location (str, optional): Location to get time for. Defaults to None.
            
        Returns:
            str: Formatted time response
        """
        # Get the time data
        time_data = self.get_current_time(location)
        
        if not time_data["success"]:
            return f"Xin lỗi, tôi không thể lấy thông tin thời gian cho {location}: {time_data['error']}"
        
        # Format the response based on the location
        if not location or location.lower() in ["việt nam", "vietnam"]:
            return f"Bây giờ là {time_data['formatted']}"
        else:
            return f"Bây giờ là {time_data['formatted']} tại {time_data['location']} (Múi giờ {time_data['timezone']})."
    
    def set_hardware_interface(self, hardware_interface):
        """
        Set the hardware interface reference.
        
        Args:
            hardware_interface: HardwareInterface instance
        """
        self.hardware_interface = hardware_interface
        logger.info("Hardware interface set for TimeService")
        
    # =========== Alarm functionality ===========
    
    def add_alarm(self, alarm_time, alarm_date=None, repeat_days=None, name="Báo thức", alarm_type="Báo thức thông thường", snooze_enabled=True, snooze_time=5):
        """
        Add a new alarm.
        
        Args:
            alarm_time (QTime): Time of the alarm
            alarm_date (QDate, optional): Date for one-time alarm. Defaults to None.
            repeat_days (list, optional): List of weekdays (1-7) to repeat. Defaults to None.
            name (str, optional): Alarm name. Defaults to "Báo thức".
            alarm_type (str, optional): Type of alarm. Defaults to "Báo thức thông thường".
            snooze_enabled (bool, optional): Whether snooze is enabled. Defaults to True.
            snooze_time (int, optional): Snooze time in minutes. Defaults to 5.
            
        Returns:
            str: Alarm ID if successful, None otherwise
        """
        try:
            # Generate a unique ID for this alarm
            alarm_id = str(uuid.uuid4())
            
            # Create alarm data structure
            self.alarms[alarm_id] = {
                "time": alarm_time,
                "date": alarm_date,
                "repeat_days": repeat_days or [],
                "name": name,
                "type": alarm_type,
                "snooze_enabled": snooze_enabled,
                "snooze_time": snooze_time,
                "active": True,
                "last_triggered": None,
                "snooze_count": 0
            }
            
            logger.info(f"Added new alarm '{name}' at {alarm_time.toString('HH:mm')}")
            return alarm_id
        except Exception as e:
            logger.error(f"Error adding alarm: {str(e)}")
            return None
    
    def update_alarm(self, alarm_id, alarm_time, alarm_date=None, repeat_days=None, name=None, alarm_type=None, snooze_enabled=None, snooze_time=None, active=True):
        """
        Update an existing alarm.
        
        Args:
            alarm_id (str): ID of the alarm to update
            alarm_time (QTime): New time for the alarm
            alarm_date (QDate, optional): New date for one-time alarm. Defaults to None.
            repeat_days (list, optional): New repeat days. Defaults to None.
            name (str, optional): New alarm name. Defaults to None.
            alarm_type (str, optional): New alarm type. Defaults to None.
            snooze_enabled (bool, optional): New snooze state. Defaults to None.
            snooze_time (int, optional): New snooze time. Defaults to None.
            active (bool, optional): Alarm active state. Defaults to True.
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if alarm_id not in self.alarms:
            logger.error(f"Cannot update alarm: ID {alarm_id} not found")
            return False
            
        try:
            # Update alarm data
            if alarm_time:
                self.alarms[alarm_id]["time"] = alarm_time
                
            self.alarms[alarm_id]["date"] = alarm_date
            self.alarms[alarm_id]["repeat_days"] = repeat_days or []
            
            if name:
                self.alarms[alarm_id]["name"] = name
                
            if alarm_type:
                self.alarms[alarm_id]["type"] = alarm_type
                
            if snooze_enabled is not None:
                self.alarms[alarm_id]["snooze_enabled"] = snooze_enabled
                
            if snooze_time is not None:
                self.alarms[alarm_id]["snooze_time"] = snooze_time
                
            self.alarms[alarm_id]["active"] = active
            
            logger.info(f"Updated alarm {alarm_id}: {self.alarms[alarm_id]['name']}")
            return True
        except Exception as e:
            logger.error(f"Error updating alarm {alarm_id}: {str(e)}")
            return False
    
    def delete_alarm(self, alarm_id):
        """
        Delete an alarm.
        
        Args:
            alarm_id (str): ID of the alarm to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if alarm_id not in self.alarms:
            logger.error(f"Cannot delete alarm: ID {alarm_id} not found")
            return False
            
        try:
            # If this is the currently ringing alarm, stop it
            if self.is_alarm_ringing and self.current_ringing_alarm == alarm_id:
                self.stop_alarm()
                
            # Delete the alarm
            alarm_name = self.alarms[alarm_id]["name"]
            del self.alarms[alarm_id]
            
            logger.info(f"Deleted alarm {alarm_id}: {alarm_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting alarm {alarm_id}: {str(e)}")
            return False
    
    def get_alarm(self, alarm_id):
        """
        Get information about a specific alarm.
        
        Args:
            alarm_id (str): ID of the alarm
            
        Returns:
            dict: Alarm data if found, None otherwise
        """
        return self.alarms.get(alarm_id)
    
    def get_all_alarms(self):
        """
        Get all alarms.
        
        Returns:
            dict: Dictionary of all alarms with IDs as keys
        """
        return self.alarms
    
    def check_alarms(self):
        """
        Check if any alarms should be triggered based on current time.
        Called regularly from timer.
        """
        # If alarm is already ringing, don't check new alarms
        if self.is_alarm_ringing:
            return
            
        # Get current time and date
        now = datetime.datetime.now()
        current_time = QTime(now.hour, now.minute)
        current_date = QDate(now.year, now.month, now.day)
        current_weekday = now.weekday() + 1  # Convert to 1-7 (Monday=1)
        
        # Check each alarm
        for alarm_id, alarm_data in self.alarms.items():
            # Skip inactive alarms
            if not alarm_data["active"]:
                continue
                
            # Get alarm time
            alarm_time = alarm_data["time"]
            
            # Check if the alarm time exactly matches current time
            if current_time.hour() == alarm_time.hour() and current_time.minute() == alarm_time.minute():
                # For one-time alarms, check the date
                if alarm_data["date"]:
                    if current_date == alarm_data["date"]:
                        # Check if already triggered today
                        if not self._already_triggered_today(alarm_id):
                            self._trigger_alarm(alarm_id)
                            return
                
                # For repeating alarms, check the weekday
                elif alarm_data["repeat_days"]:
                    if current_weekday in alarm_data["repeat_days"]:
                        # Check if already triggered today
                        if not self._already_triggered_today(alarm_id):
                            self._trigger_alarm(alarm_id)
                            return
                
                # For daily alarms (no date, no repeat days)
                elif not alarm_data["date"] and not alarm_data["repeat_days"]:
                    # Check if already triggered today
                    if not self._already_triggered_today(alarm_id):
                        self._trigger_alarm(alarm_id)
                        return
    
    def _already_triggered_today(self, alarm_id):
        """
        Check if alarm was already triggered today.
        
        Args:
            alarm_id (str): Alarm ID to check
            
        Returns:
            bool: True if already triggered today
        """
        alarm_data = self.alarms[alarm_id]
        last_triggered = alarm_data["last_triggered"]
        
        if not last_triggered:
            return False
            
        # Check if the last trigger was today
        today = datetime.date.today()
        return last_triggered.date() == today
    
    def _trigger_alarm(self, alarm_id):
        """
        Trigger an alarm with sound and notifications.
        
        Args:
            alarm_id (str): ID of the alarm to trigger
        """
        logger.info(f"Triggering alarm {alarm_id}: {self.alarms[alarm_id]['name']}")
        
        # Update alarm last triggered time
        self.alarms[alarm_id]["last_triggered"] = datetime.datetime.now()
        
        # Set alarm state
        self.is_alarm_ringing = True
        self.current_ringing_alarm = alarm_id
          # Display on hardware if connected
        if self.hardware_interface and self.hardware_interface.is_connected():
            alarm_name = self.alarms[alarm_id]["name"]
            self.hardware_interface.display_message(f"BÁO THỨC\n{alarm_name}")
        
        # Play alarm sound in a separate thread
        threading.Thread(target=self._play_alarm_sound, daemon=True).start()
        
    def _play_alarm_sound(self):
        """Play the alarm sound in a loop until stopped."""
        try:
            # Get current alarm data
            alarm_data = self.alarms[self.current_ringing_alarm]
            alarm_type = alarm_data["type"]
            
            # Get sound file based on alarm type using helper method
            sound_filename = self.alarm_sounds.get(alarm_type, "alarm.mp3")
            sound_file = self._get_sound_file_path(sound_filename)
            
            # If the specific file doesn't exist, try default alarm sound
            if not os.path.exists(sound_file):
                logger.warning(f"Alarm sound file not found at: {sound_file}, trying default alarm sound")
                sound_file = self._get_sound_file_path("alarm.mp3")
                # If even the default sound doesn't exist, give up
                if not os.path.exists(sound_file):
                    logger.error(f"Default alarm sound file not found at: {sound_file}")
                    return
                    
            logger.info(f"Playing alarm sound from: {sound_file}")
            
            # Initialize pygame mixer if not already initialized
            if pygame.mixer.get_init() is None:
                try:
                    pygame.mixer.init()
                    logger.info("Pygame mixer initialized for alarm playback")
                except Exception as e:
                    logger.error(f"Failed to initialize pygame mixer for alarm: {str(e)}")
                    return
                
            # Load and play the sound in a loop
            try:
                pygame.mixer.music.load(sound_file)
                pygame.mixer.music.set_volume(self.volume)
                logger.info(f"Alarm sound loaded successfully, volume set to {self.volume}")
            except Exception as e:
                logger.error(f"Failed to load alarm sound file {sound_file}: {str(e)}")
                return
                
            # Handle different alarm types
            if alarm_type == "Báo thức dần dần":
                # Start with low volume and gradually increase
                pygame.mixer.music.set_volume(0.1)
                pygame.mixer.music.play(-1)
                logger.info("Playing gradual alarm with increasing volume")
                
                # Gradually increase volume
                for vol in range(1, 8):
                    if not self.is_alarm_ringing:  # Check if alarm was stopped
                        break
                    time.sleep(2)  # Wait 2 seconds between volume increases
                    new_volume = min(vol * 0.1, self.volume)  # Don't exceed max volume
                    pygame.mixer.music.set_volume(new_volume)
                    logger.debug(f"Gradual alarm volume increased to {new_volume}")
            else:
                # Play normally for other types
                pygame.mixer.music.play(-1)
                logger.info(f"Playing {alarm_type} alarm at volume {self.volume}")
            
            # Continue playing until alarm is stopped
            while self.is_alarm_ringing:
                # Check if music is still playing, restart if it stopped unexpectedly
                if not pygame.mixer.music.get_busy():
                    logger.warning("Alarm music stopped unexpectedly, restarting...")
                    try:
                        pygame.mixer.music.play(-1)
                    except Exception as e:
                        logger.error(f"Failed to restart alarm music: {str(e)}")
                        break
                time.sleep(0.5)
                
            # Stop sound when alarm is cleared
            pygame.mixer.music.stop()
            logger.info("Alarm sound stopped")
            
        except Exception as e:
            logger.error(f"Error playing alarm sound: {str(e)}")
            
    def stop_alarm(self):
        """
        Stop the currently ringing alarm.
        
        Returns:
            bool: True if successful, False if no alarm was ringing
        """
        if not self.is_alarm_ringing:
            return False
            
        try:
            # Reset alarm state
            self.is_alarm_ringing = False
            self.current_ringing_alarm = None
            
            # Stop sound
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                
            # Update hardware display if connected
            if self.hardware_interface and self.hardware_interface.is_connected():
                self.hardware_interface.display_message("MIS Assistant\nReady")
                
            logger.info("Alarm stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping alarm: {str(e)}")
            return False
    
    def process_alarm_voice_command(self, query):
        """
        Process a voice command related to alarms.
        
        Args:
            query (str): Voice command text
            
        Returns:
            str: Response to the command
        """
        query_lower = query.lower()
        
        # Check for stop alarm commands
        if ("tắt báo thức" in query_lower or 
            "tắt âm thanh báo thức" in query_lower or 
            "dừng báo thức" in query_lower or 
            "tắt chuông" in query_lower):
            
            if self.stop_alarm():
                return "Đã tắt báo thức."
            else:
                return "Không có báo thức nào đang kêu."
        
        return None  # Not an alarm command
    
    def parse_and_set_alarm(self, query):
        """
        Parse a natural language alarm request and set an alarm.
        
        Args:
            query (str): Natural language alarm request
            
        Returns:
            str: Response message confirming the alarm or explaining an error
        """
        try:
            query_lower = query.lower()
            
            # Extract time information using regex
            import re
            
            # Pattern for hours and minutes with various formats
            # Examples: "9 giờ 30", "9:30", "21 giờ", "21:00", etc.
            time_pattern = r'(\d{1,2})\s*(?::|giờ|h)\s*(\d{1,2})?'
            am_pm_pattern = r'(sáng|chiều|tối)'
            
            # Try to extract time
            time_match = re.search(time_pattern, query_lower)
            am_pm_match = re.search(am_pm_pattern, query_lower)
            
            if not time_match:
                return "Tôi không thể hiểu thời gian bạn muốn đặt báo thức. Vui lòng xác định giờ cụ thể, ví dụ: đặt báo thức lúc 7 giờ 30 sáng."
            
            # Extract hours and minutes
            hours = int(time_match.group(1))
            
            # If minutes are specified, use them; otherwise, set to 0
            if time_match.group(2):
                minutes = int(time_match.group(2))
            else:
                minutes = 0
            
            # Handle AM/PM if specified
            if am_pm_match:
                period = am_pm_match.group(1)
                if period == "chiều" or period == "tối":
                    # For "chiều" (afternoon) or "tối" (evening), convert to 24-hour format if needed
                    if hours < 12:
                        hours += 12
                elif period == "sáng" and hours == 12:
                    # For "12 giờ sáng" (12 AM), convert to 0
                    hours = 0
            
            # Ensure valid hour
            if hours < 0 or hours > 23:
                return f"Giờ không hợp lệ: {hours}. Vui lòng sử dụng giờ từ 0-23."
            
            # Ensure valid minutes
            if minutes < 0 or minutes > 59:
                return f"Phút không hợp lệ: {minutes}. Vui lòng sử dụng phút từ 0-59."
            
            # Create QTime object for alarm
            from PyQt5.QtCore import QTime
            alarm_time = QTime(hours, minutes)
            
            # Find out if this is for today, tomorrow, specific date
            from PyQt5.QtCore import QDate
            alarm_date = None
            
            # Check for specific date patterns
            today = QDate.currentDate()
            
            if "ngày mai" in query_lower or "tomorrow" in query_lower:
                alarm_date = today.addDays(1)
            elif "hôm nay" in query_lower or "today" in query_lower:
                alarm_date = today
            else:
                # Try to extract specific date
                date_pattern = r'ngày\s+(\d{1,2})(?:\s+tháng\s+(\d{1,2}))?(?:\s+năm\s+(\d{4}))?'
                date_match = re.search(date_pattern, query_lower)
                
                if date_match:
                    day = int(date_match.group(1))
                    
                    # If month is specified, use it; otherwise, use current month
                    if date_match.group(2):
                        month = int(date_match.group(2))
                    else:
                        month = today.month()
                    
                    # If year is specified, use it; otherwise, use current year
                    if date_match.group(3):
                        year = int(date_match.group(3))
                    else:
                        year = today.year()
                    
                    # Create date if valid
                    if QDate.isValid(year, month, day):
                        alarm_date = QDate(year, month, day)
                    else:
                        return f"Ngày không hợp lệ: {day}/{month}/{year}."
            
            # Find the next available alarm number
            next_alarm_number = 1
            existing_names = set()
            
            for alarm_id, alarm_data in self.alarms.items():
                existing_names.add(alarm_data["name"])
                if alarm_data["name"].startswith("Báo thức "):
                    try:
                        num = int(alarm_data["name"].replace("Báo thức ", ""))
                        if num >= next_alarm_number:
                            next_alarm_number = num + 1
                    except ValueError:
                        continue
            
            # Create a unique name for the alarm
            alarm_name = f"Báo thức {next_alarm_number}"
            
            # Ensure the name is unique
            while alarm_name in existing_names:
                next_alarm_number += 1
                alarm_name = f"Báo thức {next_alarm_number}"
            
            # Set up the alarm
            alarm_id = self.add_alarm(
                alarm_time=alarm_time,
                alarm_date=alarm_date,
                name=alarm_name
            )
            
            if not alarm_id:
                return "Xin lỗi, không thể tạo báo thức. Vui lòng thử lại sau."
            
            # Prepare response message
            if alarm_date:
                date_str = alarm_date.toString("dd/MM/yyyy")
                response = f"Đã tạo {alarm_name} cho lúc {alarm_time.toString('HH:mm')} ngày {date_str}."
            else:
                response = f"Đã tạo {alarm_name} hàng ngày lúc {alarm_time.toString('HH:mm')}."
            
            return response
            
        except Exception as e:
            logger.error(f"Error parsing alarm request: {str(e)}")
            return "Xin lỗi, có lỗi khi đặt báo thức. Vui lòng thử lại và xác định thời gian cụ thể."
    
    def snooze_alarm(self, alarm_id):
        """
        Snooze the currently ringing alarm.
        
        Args:
            alarm_id (str): ID of the alarm to snooze
            
        Returns:
            bool: True if snooze successful, False otherwise
        """
        if not self.is_alarm_ringing or self.current_ringing_alarm != alarm_id:
            return False
            
        alarm_data = self.alarms[alarm_id]
        
        # Check if snooze is enabled and not exceeded max count
        if not alarm_data["snooze_enabled"] or alarm_data["snooze_count"] >= self.max_snooze_count:
            return False
            
        try:
            # Stop current alarm
            self.stop_alarm()
            
            # Increment snooze count
            alarm_data["snooze_count"] += 1
            
            # Calculate snooze time
            snooze_minutes = alarm_data["snooze_time"]
            snooze_time = datetime.datetime.now() + datetime.timedelta(minutes=snooze_minutes)
            
            # Create temporary alarm for snooze
            snooze_alarm_id = str(uuid.uuid4())
            self.alarms[snooze_alarm_id] = {
                "time": QTime(snooze_time.hour, snooze_time.minute),
                "date": QDate(snooze_time.year, snooze_time.month, snooze_time.day),
                "repeat_days": [],
                "name": f"{alarm_data['name']} (Báo lại)",
                "type": alarm_data["type"],
                "snooze_enabled": False,  # Disable further snoozes
                "snooze_time": alarm_data["snooze_time"],
                "active": True,
                "last_triggered": None,
                "snooze_count": alarm_data["snooze_count"]
            }
            
            logger.info(f"Snoozed alarm {alarm_id} for {snooze_minutes} minutes")
            return True
            
        except Exception as e:
            logger.error(f"Error snoozing alarm {alarm_id}: {str(e)}")
            return False
    
    def adjust_volume(self, increase=True):
        """
        Adjust the alarm volume.
        
        Args:
            increase (bool): True to increase volume, False to decrease
            
        Returns:
            float: New volume level
        """
        if increase:
            self.volume = min(1.0, self.volume + self.volume_step)
        else:
            self.volume = max(0.0, self.volume - self.volume_step)
            
        # Update current volume if alarm is ringing
        if self.is_alarm_ringing and pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self.volume)
            
        return self.volume
    
    def start_clock_display(self):
        """Start displaying current time on LCD."""
        if self.is_showing_clock:
            return  # Already showing clock
            
        self.is_showing_clock = True
        self.stop_clock_thread = False
        
        # Start a thread to continuously update the LCD with time
        self.clock_update_thread = threading.Thread(target=self._clock_display_loop)
        self.clock_update_thread.daemon = True
        self.clock_update_thread.start()
        
        logger.info("Clock display started on LCD")
    
    def stop_clock_display(self):
        """Stop displaying time on LCD."""
        if not self.is_showing_clock:
            return  # Not showing clock
            
        self.is_showing_clock = False
        self.stop_clock_thread = True
        
        # Wait for thread to finish
        if self.clock_update_thread and self.clock_update_thread.is_alive():
            self.clock_update_thread.join(timeout=2.0)
        
        # Clear LCD display and reset to initial state
        if self.hardware_interface and hasattr(self.hardware_interface, 'get_lcd_service'):
            lcd_service = self.hardware_interface.get_lcd_service()
            if lcd_service:
                lcd_service.clear_and_reset()
        
        logger.info("Clock display stopped on LCD")
    
    def _clock_display_loop(self):
        """Background thread loop for updating LCD clock display."""
        while not self.stop_clock_thread and self.is_showing_clock:
            try:
                # Get current Vietnam time
                now = datetime.datetime.now(pytz.timezone(self.default_timezone))
                
                # Format as requested: Date: DD/MM/YYYY \n Time: HH:MM:SS
                date_str = now.strftime("%d/%m/%Y")
                time_str = now.strftime("%H:%M:%S")
                display_text = f"Time: {time_str}\nDate: {date_str}"
                
                # Send to LCD via hardware interface
                if self.hardware_interface:
                    if hasattr(self.hardware_interface, 'get_lcd_service'):
                        lcd_service = self.hardware_interface.get_lcd_service()
                        if lcd_service:
                            lcd_service.set_display_text(display_text)
                    elif hasattr(self.hardware_interface, 'display_message'):
                        # Direct hardware interface method
                        self.hardware_interface.display_message(display_text)
                
                # Wait 1 second before next update
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in clock display loop: {str(e)}")
                time.sleep(1.0)  # Continue even if there's an error
        
        logger.info("Clock display loop ended")
    
    def is_clock_displaying(self):
        """Check if clock is currently being displayed on LCD."""
        return self.is_showing_clock
    
    def _get_sound_file_path(self, sound_filename):
        """
        Get the correct path to a sound file in the resources/sounds directory.
        
        Args:
            sound_filename (str): Name of the sound file
            
        Returns:
            str: Full path to the sound file
        """
        # Try multiple possible paths to find the sound file
        possible_paths = [
            # From models/ directory: models -> app -> software -> resources/sounds/
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                'resources', 'sounds', sound_filename
            ),
            # Alternative path calculation
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'resources', 'sounds', sound_filename
            ),
            # Direct relative path from software directory
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                '..', 'resources', 'sounds', sound_filename
            )
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.debug(f"Found sound file at: {path}")
                return path
                
        # If no path found, return the first one for error reporting
        logger.warning(f"Sound file {sound_filename} not found in any expected location")
        return possible_paths[0]