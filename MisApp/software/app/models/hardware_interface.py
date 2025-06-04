import serial
import serial.tools.list_ports
import threading
import time
import re
from ..utils import config, logger
from .notification_sound_service import notification_service

class HardwareInterface:
    """
    Interface for communication with MIS Assistant hardware (ESP32).
    Handles serial communication with the microcontroller.
    """
    
    def __init__(self):
        self.serial_port = config.SERIAL_PORT
        self.baud_rate = config.SERIAL_BAUD_RATE
        self.serial = None
        self.connected = False
        self.reader_thread = None
        self.connection_monitor_thread = None
        self.stop_thread = False
        self.stop_monitor = False
        self.auto_reconnect = True 
        self.reconnect_interval = 5  
        self.connection_check_interval = 2  
        self.last_successful_port = None  
        self.callbacks = {
            'LISTENING': [],
            'CONNECTED': [],
            'DISCONNECTED': [],
            'ACTIVATE_MICROPHONE': [],  
            'LED_STATUS': [],  
            'BLUETOOTH_CONNECTED': [],  
            'BLUETOOTH_DISCONNECTED': [], 
            'BLUETOOTH_AUDIO_STARTED': [],  
            'BLUETOOTH_AUDIO_STOPPED': []  
        }
        self.esp_ip = None
        
        self._start_connection_monitor()
        
        self.connect()
        
    def _start_connection_monitor(self):
        """Start the connection monitoring thread."""
        self.stop_monitor = False
        self.connection_monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.connection_monitor_thread.start()
        logger.info("Connection monitoring thread started")
        
    def _monitor_connection(self):
        """Background thread to monitor and maintain connection."""
        while not self.stop_monitor:
            try:
                if not self.connected and self.auto_reconnect:
                    logger.info("Connection lost - attempting to reconnect...")
                    self._attempt_reconnection()
                elif self.connected:
                    # Check if connection is still alive
                    if not self._is_connection_alive():
                        logger.warning("Connection appears to be dead - marking as disconnected")
                        self.connected = False
                        if self.serial:
                            try:
                                self.serial.close()
                            except:
                                pass
                            self.serial = None
                        self._trigger_callbacks('DISCONNECTED', {})
                        
                time.sleep(self.connection_check_interval)
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
                time.sleep(5)
                
    def _is_connection_alive(self):
        """Check if the current serial connection is still alive."""
        if not self.serial or not self.connected:
            return False
            
        try:
            self.serial.in_waiting
            return True
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False
            
    def _find_esp32_port(self):
        """Automatically find ESP32 device port."""
        logger.info("Scanning for ESP32 device...")
        ports = serial.tools.list_ports.comports()
        
        esp32_identifiers = [
            'CH340',  
            'CH341',  
            'CH9102',
            'CP210',  
            'FT232', 
            'USB-SERIAL', 
            'Silicon Labs',
            'UART'    
        ]
        
        candidate_ports = []
        
        for port in ports:
            port_info = f"{port.device} - {port.description} - {port.manufacturer or 'Unknown'}"
            logger.debug(f"Found port: {port_info}")
            
            # Check if this looks like an ESP32 port
            description_upper = (port.description or '').upper()
            manufacturer_upper = (port.manufacturer or '').upper()
            
            for identifier in esp32_identifiers:
                if identifier in description_upper or identifier in manufacturer_upper:
                    candidate_ports.append(port.device)
                    logger.info(f"Found potential ESP32 port: {port_info}")
                    break
        
        if self.last_successful_port and self.last_successful_port in [p.device for p in ports]:
            if self.last_successful_port in candidate_ports:
                candidate_ports.remove(self.last_successful_port)
                candidate_ports.insert(0, self.last_successful_port)
                logger.info(f"Prioritized last successful port: {self.last_successful_port}")
            else:
                candidate_ports.insert(0, self.last_successful_port)
        
        # If configured port is available, try it first
        if self.serial_port in [p.device for p in ports]:
            if self.serial_port not in candidate_ports:
                candidate_ports.insert(0, self.serial_port)
        
        return candidate_ports
        
    def _attempt_reconnection(self):
        """Attempt to reconnect to ESP32."""
        if self.connected:
            return True
            
        candidate_ports = self._find_esp32_port()
        
        if not candidate_ports:
            logger.warning("No potential ESP32 ports found")
            return False
            
        # Try each candidate port
        for port in candidate_ports:
            logger.info(f"Attempting connection to port: {port}")
            if self._try_connect_to_port(port):
                logger.info(f"Successfully connected to ESP32 on port: {port}")
                self.last_successful_port = port
                self.serial_port = port  # Update current port
                return True
            else:
                logger.debug(f"Failed to connect to port: {port}")
                
        logger.warning("Failed to reconnect to any available port")
        return False
        
    def _try_connect_to_port(self, port):
        """Try to connect to a specific port."""
        try:
            # Close existing connection if any
            if self.serial:
                try:
                    self.serial.close()
                except:
                    pass
                self.serial = None
                
            # Try to open the port
            test_serial = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                timeout=2,
                writeTimeout=2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Flush buffers
            test_serial.flushInput()
            test_serial.flushOutput()
            
            # Wait a moment for ESP32 to initialize
            time.sleep(1)
            
            # Send a test command
            test_serial.write(b"PING\n")
            test_serial.flush()
            
            time.sleep(1)
            
            self.serial = test_serial
            self.connected = True
            
            # Start/restart reader thread
            self._restart_reader_thread()
            
            # Trigger connected callbacks
            self._trigger_callbacks('CONNECTED', {'port': port})
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to connect to {port}: {e}")
            try:
                if 'test_serial' in locals():
                    test_serial.close()
            except:
                pass
            return False
        
    def connect(self):
        """
        Connect to the ESP32 via serial port with auto-detection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.connected:
            logger.debug("Already connected to hardware")
            return True
            
        logger.info(f"Attempting to connect to hardware...")
        
        if self._attempt_reconnection():
            return True
            
        logger.error("Failed to connect to hardware on any available port")
        return False
        
    def _restart_reader_thread(self):
        """Restart the serial reader thread."""
        self.stop_thread = True
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2)
            
        # Start new reader thread
        self.stop_thread = False
        self.reader_thread = threading.Thread(target=self._read_serial, daemon=True)
        self.reader_thread.start()
        logger.debug("Serial reader thread restarted")
            
    def disconnect(self):
        """Disconnect from the ESP32."""
        logger.info("Disconnecting from hardware...")
        
        try:
            # Cancel any pending Bluetooth disconnect timer
            if hasattr(self, '_bluetooth_disconnect_timer'):
                self._bluetooth_disconnect_timer.cancel()
                logger.debug("Cancelled pending Bluetooth disconnect timer during hardware disconnect")
            
            # Stop connection monitoring
            self.stop_monitor = True
            if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
                self.connection_monitor_thread.join(timeout=2)
            
            # Stop reader thread
            self.stop_thread = True
            if self.reader_thread and self.reader_thread.is_alive():
                self.reader_thread.join(timeout=2)
                
            # Close serial connection
            if self.serial:
                self.serial.close()
                self.serial = None
                
            # Update state
            self.connected = False
            self.esp_ip = None
            
            logger.info("Disconnected from hardware")
            
            # Trigger callbacks
            self._trigger_callbacks('DISCONNECTED', {})
            
        except Exception as e:
            logger.error(f"Error disconnecting from hardware: {str(e)}")
            
    def set_auto_reconnect(self, enabled):
        """Enable or disable automatic reconnection."""
        self.auto_reconnect = enabled
        logger.info(f"Auto-reconnect {'enabled' if enabled else 'disabled'}")
        
    def force_reconnect(self):
        """Force an immediate reconnection attempt."""
        logger.info("Forcing reconnection...")
        self.connected = False
        if self.serial:
            try:
                self.serial.close()
            except:
                pass
            self.serial = None
        return self._attempt_reconnection()
            
    def _read_serial(self):
        """Background thread for reading serial data from ESP32."""
        logger.debug("Serial reader thread started")
        
        while not self.stop_thread:
            if not self.connected or not self.serial:
                time.sleep(0.5)
                continue
                
            try:
                if self.serial.in_waiting > 0:
                    # Use errors='replace' to handle invalid UTF-8 sequences
                    line = self.serial.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        # Log and process the message
                        self._process_message(line)
            except Exception as e:
                logger.error(f"Error reading from serial: {str(e)}")
                self.connected = False
                
                # Trigger disconnect callbacks (reconnection will be handled by monitor thread)
                self._trigger_callbacks('DISCONNECTED', {})
                break  # Exit the reader thread, monitor will restart it when reconnected
                
        logger.debug("Serial reader thread stopped")
                
    def _process_message(self, message):
        """
        Process messages received from ESP32.
        
        Args:
            message (str): Message received from ESP32
        """
        logger.debug(f"Received from hardware: {message}")
        
        # Process connection status message
        if message.startswith("CONNECTED:"):
            # Extract ESP IP address
            self.esp_ip = message.replace("CONNECTED:", "").strip()
            logger.info(f"ESP32 connected with IP: {self.esp_ip}")
            
            # Trigger connected callbacks
            self._trigger_callbacks('CONNECTED', {'ip': self.esp_ip})
            
        # Process button press for microphone activation with debouncing
        elif message.strip() in ["ACTIVATE_MICROPHONE", "MICROPHONE_ACTIVATED", "BUTTON_PRESSED"]:
            # Improved debouncing for button presses on software side
            current_time = time.time()
            
            # Initialize debouncing variables if they don't exist
            if not hasattr(self, '_last_button_time'):
                self._last_button_time = 0
            if not hasattr(self, '_last_processed_event'):
                self._last_processed_event = ""
            
            time_since_last = current_time - self._last_button_time
            
            if time_since_last > 0.8 and self._last_processed_event != message.strip():
                self._last_button_time = current_time
                self._last_processed_event = message.strip()
                
                logger.info(f"Hardware button event processed: {message} (time since last: {time_since_last:.3f}s)")
                
                self._trigger_callbacks('ACTIVATE_MICROPHONE', {
                    'source': 'hardware_button',
                    'event': message.strip(),
                    'timestamp': current_time
                })
            else:
                logger.debug(f"Button event ignored (debouncing/duplicate): {message} (time since last: {time_since_last:.3f}s, last event: {self._last_processed_event})")
                
        # Process additional button debug messages
        elif "Button press processed successfully" in message:
            logger.debug(f"Button processing confirmation: {message}")
            # Reset the last processed event when button processing is complete
            if hasattr(self, '_last_processed_event'):
                self._last_processed_event = ""
            
        elif "Button released - ready for next press" in message:
            logger.debug(f"Button release confirmation: {message}")
            
        elif "BUTTON_COOLDOWN_ACTIVE" in message:
            logger.debug("Button cooldown active - ignoring rapid press")
            
        elif "BUTTON_FEEDBACK_COMPLETE" in message:
            logger.debug("Button feedback cycle completed")
            
        # Process listening events
        elif message.startswith("LISTENING"):
            self._trigger_callbacks('LISTENING', {})
            
        # Process LED status updates
        elif message.startswith("LED_STATUS:"):
            # Extract LED status (format from ESP32: LED_STATUS:RED_ON, ALL_OFF, etc.)
            led_status = message.replace("LED_STATUS:", "").strip()
            
            # Parse LED status from ESP32 format
            red_status = False
            yellow_status = False  
            green_status = False
            
            # Map ESP32 LED status messages to individual LED states
            if led_status == "ALL_ON":
                red_status = yellow_status = green_status = True
            elif led_status == "ALL_OFF":
                red_status = yellow_status = green_status = False
            elif led_status == "RED_ON":
                red_status = True
            elif led_status == "YELLOW_ON":
                yellow_status = True
            elif led_status == "GREEN_ON":
                green_status = True
            elif led_status == "RED_YELLOW_ON":
                red_status = yellow_status = True
            elif led_status == "RED_GREEN_ON":
                red_status = green_status = True
            elif led_status == "YELLOW_GREEN_ON":
                yellow_status = green_status = True
            else:
                # Try to parse old comma-separated format for backward compatibility
                status_parts = led_status.split(',')
                if len(status_parts) == 3:
                    try:
                        red_status = int(status_parts[0]) == 1
                        yellow_status = int(status_parts[1]) == 1
                        green_status = int(status_parts[2]) == 1
                    except ValueError:
                        logger.error(f"Invalid LED status format: {led_status}")
                        return
                else:
                    logger.error(f"Unknown LED status format: {led_status}")
                    return
            
            # Trigger LED status callbacks
            self._trigger_callbacks('LED_STATUS', {
                'red': red_status,
                'yellow': yellow_status,
                'green': green_status
            })
            
            logger.debug(f"LED status updated - Red: {red_status}, Yellow: {yellow_status}, Green: {green_status}")
        
        # Process error messages
        elif message.startswith("ERROR:"):
            logger.warning(f"Received error from hardware: {message[6:]}")
            return False
        
        # Process Bluetooth connection/disconnection messages
        elif message.startswith("BLUETOOTH:"):
            bluetooth_event = message.replace("BLUETOOTH:", "").strip()
            logger.info(f"Bluetooth event received: {bluetooth_event}")
            
            if bluetooth_event == "CONNECTED":
                # Cancel any pending disconnection sound if reconnecting quickly
                if hasattr(self, '_bluetooth_disconnect_timer'):
                    self._bluetooth_disconnect_timer.cancel()
                    logger.debug("Cancelled pending disconnection sound due to quick reconnection")
                
                # Play Bluetooth connection sound immediately
                try:
                    notification_service.play_bluetooth_connected()
                    logger.info("Played Bluetooth connection notification sound")
                except Exception as e:
                    logger.error(f"Error playing Bluetooth connection sound: {e}")
                
                # Trigger Bluetooth connected callbacks
                self._trigger_callbacks('BLUETOOTH_CONNECTED', {
                    'status': 'connected',
                    'timestamp': time.time()
                })
                
            elif bluetooth_event == "DISCONNECTED":
                # Delay disconnection sound to avoid playing it during quick reconnection
                def play_disconnect_sound_delayed():
                    try:
                        notification_service.play_bluetooth_disconnected()
                        logger.info("Played Bluetooth disconnection notification sound")
                    except Exception as e:
                        logger.error(f"Error playing Bluetooth disconnection sound: {e}")
                
                import threading
                self._bluetooth_disconnect_timer = threading.Timer(0.5, play_disconnect_sound_delayed)
                self._bluetooth_disconnect_timer.start()
                
                # Trigger Bluetooth disconnected callbacks immediately (for UI updates)
                self._trigger_callbacks('BLUETOOTH_DISCONNECTED', {
                    'status': 'disconnected',
                    'timestamp': time.time()
                })
                
            elif bluetooth_event == "AUDIO_STARTED":
                # Trigger Bluetooth audio started callbacks
                self._trigger_callbacks('BLUETOOTH_AUDIO_STARTED', {
                    'status': 'audio_started',
                    'timestamp': time.time()
                })
                
            elif bluetooth_event == "AUDIO_STOPPED":
                # Trigger Bluetooth audio stopped callbacks
                self._trigger_callbacks('BLUETOOTH_AUDIO_STOPPED', {
                    'status': 'audio_stopped',
                    'timestamp': time.time()
                })
        
        # Add other message processing as needed

    def _trigger_callbacks(self, event_type, data):
        """
        Trigger callbacks for a specific event.
        
        Args:
            event_type (str): Event type
            data (dict): Event data
        """
        if event_type in self.callbacks:
            callbacks_count = len(self.callbacks[event_type])
            logger.info(f"Triggering {callbacks_count} callbacks for event: {event_type}")
            
            if callbacks_count == 0:
                logger.warning(f"No callbacks registered for event: {event_type}")
                return
                
            for callback in self.callbacks[event_type]:
                try:
                    callback_name = callback.__name__ if hasattr(callback, '__name__') else str(callback)
                    logger.info(f"Calling callback: {callback_name} for event {event_type}")
                    callback(data)
                    logger.info(f"Successfully executed callback: {callback_name}")
                except Exception as e:
                    logger.error(f"Error in callback {callback_name} for {event_type}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    
    def send_command(self, command):
        """
        Send a command to the ESP32.
        
        Args:
            command (str): Command to send
            
        Returns:
            bool: True if command was sent, False otherwise
        """
        if not self.connected or not self.serial:
            logger.warning("Cannot send command: Not connected to hardware")
            return False
            
        try:            # Ensure command ends with newline
            if not command.endswith('\n'):
                command += '\n'
                
            # Send command
            self.serial.write(command.encode('utf-8'))
            self.serial.flush()
            
            logger.debug(f"Sent command to ESP32: {command.strip()}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending command to hardware: {str(e)}")
            return False
            
    def set_listening_mode(self):
        """Tell ESP32 that we're in listening mode."""
        return self.send_command("LISTENING")
    
    def set_responding_mode(self, response_text=""):
        """
        Tell ESP32 that we're responding to a command.
        Shows 'Processing...' on the LCD.
        
        Args:
            response_text (str): Optional brief text (not shown on LCD)
        """
        return self.send_command("RESPONDING")
    
    def set_finished_mode(self):
        """Tell ESP32 that we've finished processing a command."""
        return self.send_command("FINISHED")
    
    def display_message(self, message):
        """
        Display a message on the ESP32 LCD.
        
        Args:
            message (str): Message to display, can include \\n for line break
        """
        return self.send_command(f"DISPLAY:{message}")
    
    def start_matrix_clock(self):
        """Start displaying clock on the LED Matrix - Not supported."""
        logger.warning("LED Matrix functionality is not supported")
        return False
    
    def stop_matrix_clock(self):
        """Stop displaying clock on the LED Matrix - Not supported."""
        logger.warning("LED Matrix functionality is not supported")
        return False
    
    def update_matrix_time(self, time_string):
        """Update the time displayed on the LED Matrix - Not supported."""
        logger.warning("LED Matrix functionality is not supported")
        return False
    
    def display_scrolling_text(self, text):
        """Display scrolling text on the LED Matrix - Not supported."""
        logger.warning("LED Matrix functionality is not supported")
        return False
    
    def clear_display(self):
        """Clear the LED Matrix display - Not supported."""
        logger.warning("LED Matrix functionality is not supported")
        return False
    
    def register_callback(self, event_type, callback):
        """
        Register a callback for a specific event.
        
        Args:
            event_type (str): Event type ('LISTENING', 'CONNECTED', 'DISCONNECTED')
            callback (function): Function to call when event occurs
        """
        if event_type in self.callbacks:
            if callback not in self.callbacks[event_type]:
                self.callbacks[event_type].append(callback)
                
    def is_connected(self):
        """Check if connected to ESP32."""
        return self.connected and self._is_connection_alive()
    
    def get_esp_ip(self):
        """Get ESP32 IP address."""
        return self.esp_ip
        
    def get_connection_info(self):
        """Get detailed connection information."""
        return {
            'connected': self.connected,
            'port': self.serial_port if self.connected else None,
            'last_successful_port': self.last_successful_port,
            'esp_ip': self.esp_ip,
            'auto_reconnect': self.auto_reconnect,
            'available_ports': [port.device for port in serial.tools.list_ports.comports()]
        }
    
    # =========== LED Control Methods ===========
    
    def set_led_state(self, red=False, yellow=False, green=False):
        """
        Set the state of all three LEDs.
        
        Args:
            red (bool or None): True to turn on the red LED, False to turn off, None to leave unchanged
            yellow (bool or None): True to turn on the yellow LED, False to turn off, None to leave unchanged
            green (bool or None): True to turn on the green LED, False to turn off, None to leave unchanged
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        if red is None or yellow is None or green is None:
            if red is not None:
                if red:
                    self.send_command("RED_ON")
                else:
                    pass  
            if yellow is not None:
                if yellow:
                    self.send_command("YELLOW_ON")
                else:
                    pass  
            if green is not None:
                if green:
                    self.send_command("GREEN_ON")
                else:
                    pass  
            return True
        else:           
            if red and yellow and green:
                return self.send_command("ALL_ON")
            elif not red and not yellow and not green:
                return self.send_command("ALL_OFF")
            elif red and not yellow and not green:
                return self.send_command("RED_ON")
            elif not red and yellow and not green:
                return self.send_command("YELLOW_ON")
            elif not red and not yellow and green:
                return self.send_command("GREEN_ON")
            elif red and yellow and not green:
                return self.send_command("RED_YELLOW_ON")
            elif red and not yellow and green:
                return self.send_command("RED_GREEN_ON")
            elif not red and yellow and green:
                return self.send_command("YELLOW_GREEN_ON")
            else:
                # Fallback case
                return self.send_command("ALL_OFF")
    
    def turn_on_all_leds(self):
        """Turn on all LEDs."""
        return self.send_command("ALL_ON")
        
    def turn_off_all_leds(self):
        """Turn off all LEDs."""
        return self.send_command("ALL_OFF")
    
    def turn_on_red_led(self):
        """Turn on only the red LED."""
        return self.send_command("RED_ON")
    
    def turn_on_yellow_led(self):
        """Turn on only the yellow LED."""
        return self.send_command("YELLOW_ON")
    
    def turn_on_green_led(self):
        """Turn on only the green LED."""
        return self.send_command("GREEN_ON")
    
    def turn_on_red_yellow_leds(self):
        """Turn on red and yellow LEDs, turn off green LED."""
        return self.send_command("RED_YELLOW_ON")
    
    def turn_on_red_green_leds(self):
        """Turn on red and green LEDs, turn off yellow LED."""
        return self.send_command("RED_GREEN_ON")
    
    def turn_on_yellow_green_leds(self):
        """Turn on yellow and green LEDs, turn off red LED."""
        return self.send_command("YELLOW_GREEN_ON")
    
    def toggle_red_led(self):
        """Toggle the state of the red LED."""
        return self.send_command("TOGGLE_RED")
    
    def toggle_yellow_led(self):
        """Toggle the state of the yellow LED."""
        return self.send_command("TOGGLE_YELLOW")
    
    def toggle_green_led(self):
        """Toggle the state of the green LED."""
        return self.send_command("TOGGLE_GREEN")
    
    # Smart device management methods
    def get_device_state(self, device_id):
        """
        Get the state of a smart device.
        
        Args:
            device_id (str): Device ID
            
        Returns:
            dict: Device state information or None if device not found
        """
        logger.debug(f"Getting state for device: {device_id}")
        devices = {
            "device1": {"name": "Living Room Light", "type": "light", "state": True, "value": 100},
            "device2": {"name": "Bedroom Light", "type": "dimmer", "state": False, "value": 50},
            "device3": {"name": "Kitchen Sensor", "type": "sensor", "state": True, "value": 25}
        }
        
        if device_id in devices:
            return devices[device_id]
        else:
            logger.warning(f"HardwareInterface does not have device with ID: {device_id}")
            return None
    
    def set_device_state(self, device_id, state):
        """
        Set the state of a smart device.
        
        Args:
            device_id (str): Device ID
            state (bool): New state
            
        Returns:
            bool: True if command sent successfully
        """
        logger.info(f"Setting state for device {device_id} to {state}")
        # Send command to ESP32 - format: DEVICE:<device_id>:STATE:<state>
        return self.send_command(f"DEVICE:{device_id}:STATE:{1 if state else 0}")
    
    def set_device_value(self, device_id, value):
        """
        Set the value of a smart device (e.g., dimmer level).
        
        Args:
            device_id (str): Device ID
            value (int): New value
            
        Returns:
            bool: True if command sent successfully
        """
        logger.info(f"Setting value for device {device_id} to {value}")
        # Send command to ESP32 - format: DEVICE:<device_id>:VALUE:<value>
        return self.send_command(f"DEVICE:{device_id}:VALUE:{value}")
    
    def get_all_devices(self):
        """
        Get information about all smart devices.
        
        Returns:
            dict: Dictionary of device information
        """
        # For now, return simulated devices
        return {
            "device1": {"name": "Living Room Light", "type": "light", "state": True, "value": 100},
            "device2": {"name": "Bedroom Light", "type": "dimmer", "state": False, "value": 50},
            "device3": {"name": "Kitchen Sensor", "type": "sensor", "state": True, "value": 25}
        }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            # Cancel any pending Bluetooth disconnect timer
            if hasattr(self, '_bluetooth_disconnect_timer'):
                self._bluetooth_disconnect_timer.cancel()
            
            # Stop all threads
            self.stop_monitor = True
            self.stop_thread = True
            
            # Close serial connection
            if hasattr(self, 'serial') and self.serial:
                self.serial.close()
                
        except:
            pass  # Ignore any errors during cleanup