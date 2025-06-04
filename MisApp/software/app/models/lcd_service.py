from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from ..utils import config, logger

class LCDService(QObject):
    """
    Service for managing LCD display messages with scrolling functionality.
    Handles sending messages to hardware LCD display and manages scrolling behavior.
    """
    
    # Signals for UI updates
    display_updated = pyqtSignal(str)
    scroll_position_changed = pyqtSignal(int)
    scrolling_started = pyqtSignal()
    scrolling_stopped = pyqtSignal()
    
    def __init__(self, hardware_interface=None):
        super().__init__()
        self.hardware_interface = hardware_interface
        self.current_text = ""
        self.is_scrolling = False
        self.scroll_position = 0
        self.scroll_speed = 500  
        self.lcd_width = 16
        
        # Timer for scrolling
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self._scroll_step)
        
        logger.info("LCD Service initialized")
    
    def set_hardware_interface(self, hardware_interface):
        """Set the hardware interface reference."""
        self.hardware_interface = hardware_interface
        logger.info("Hardware interface set for LCD Service")
    
    def set_display_text(self, text):
        """
        Set text to be displayed on LCD.
        
        Args:
            text (str): Text to display (can contain \n for multiple lines)
        """
        self.current_text = text.strip()
        self.scroll_position = 0
        
        # Check if text contains newline (multiline display for LCD 16x2)
        if '\n' in self.current_text:
            # Handle multiline display for LCD 16x2
            self._display_multiline_text(self.current_text)
        elif len(self.current_text) <= self.lcd_width:
            # Text fits on one line, display directly
            self._display_static_text(self.current_text)
        else:
            # Text needs scrolling
            self._display_scrolling_text()
        
        self.display_updated.emit(self.current_text)
        logger.info(f"LCD text set: {self.current_text[:20]}...")
    
    def _display_static_text(self, text):
        """Display static text that fits on LCD width."""
        if self.hardware_interface:
            # Center the text if shorter than LCD width
            centered_text = text.center(self.lcd_width)
            self.hardware_interface.display_message(centered_text)
    
    def _display_multiline_text(self, text):
        """
        Display multiline text on LCD 16x2.
        
        Args:
            text (str): Text with \n separating lines
        """
        if self.hardware_interface:
            # Send the multiline text directly to hardware
            # The ESP32 will handle \n as line separator for LCD 16x2
            self.hardware_interface.display_message(text)
            logger.info(f"Multiline LCD text sent: {text.replace(chr(10), ' | ')}")
    
    def _display_scrolling_text(self):
        """Display the current portion of scrolling text."""
        if not self.current_text:
            return
            
        # Create a scrolling window
        extended_text = self.current_text + "    "  # Add spacing between loops
        display_length = min(self.lcd_width, len(extended_text))
        
        if self.scroll_position >= len(extended_text):
            self.scroll_position = 0
        
        # Get the text segment to display
        if self.scroll_position + display_length <= len(extended_text):
            display_text = extended_text[self.scroll_position:self.scroll_position + display_length]
        else:
            # Handle wrap-around
            part1 = extended_text[self.scroll_position:]
            part2 = extended_text[:display_length - len(part1)]
            display_text = part1 + part2
        
        # Send to hardware
        if self.hardware_interface:
            self.hardware_interface.display_message(display_text)
          # Update UI
        self.scroll_position_changed.emit(self.scroll_position)
        
    def start_scroll(self):
        """Start scrolling the text."""
        if len(self.current_text) > self.lcd_width and not self.is_scrolling:
            self.is_scrolling = True
            self.scroll_timer.start(self.scroll_speed)
            self.scrolling_started.emit()
            logger.info("LCD scrolling started")
    
    def stop_scroll(self):
        """Stop scrolling the text."""
        if self.is_scrolling:
            self.is_scrolling = False
            self.scroll_timer.stop()
            self.scroll_position = 0
            self.scrolling_stopped.emit()
            # Display the beginning of the text
            if self.current_text:
                if len(self.current_text) <= self.lcd_width:
                    self._display_static_text(self.current_text)
                else:
                    display_text = self.current_text[:self.lcd_width]
                    if self.hardware_interface:
                        self.hardware_interface.display_message(display_text)
            
            logger.info("LCD scrolling stopped")
    
    def _scroll_step(self):
        """Perform one step of scrolling."""
        if self.is_scrolling and self.current_text:
            self.scroll_position += 1
            self._display_scrolling_text()
    
    def set_scroll_speed(self, speed):
        """
        Set scrolling speed.
        
        Args:
            speed (int): Speed in milliseconds between scroll steps (lower = faster)
        """
        self.scroll_speed = max(100, min(2000, speed))  # Clamp between 100ms and 2000ms
        if self.is_scrolling:
            self.scroll_timer.setInterval(self.scroll_speed)
        logger.info(f"LCD scroll speed set to {self.scroll_speed}ms")
    
    def get_scroll_speed(self):
        """Get current scroll speed."""
        return self.scroll_speed
    
    def clear_display(self):
        """Clear the LCD display."""
        self.stop_scroll()
        self.current_text = ""
        if self.hardware_interface:
            self.hardware_interface.display_message("")
        self.display_updated.emit("")
        logger.info("LCD display cleared")
    
    def clear_and_reset(self):
        """Clear the LCD display and reset to initial state (turn off LCD functionality)."""
        self.stop_scroll()
        self.current_text = ""
        if self.hardware_interface:
            # Send empty message to turn off LCD
            self.hardware_interface.display_message("")
        self.display_updated.emit("MIS Assistant\nReady")
        logger.info("LCD display cleared and reset to initial state")
    
    def process_voice_command(self, command):
        """
        Process voice commands for LCD display.
        
        Args:
            command (str): Voice command text
            
        Returns:
            bool: True if command was handled, False otherwise
        """
        command_lower = command.lower().strip()
        
        # Check for LCD display commands
        if any(phrase in command_lower for phrase in ["hiển thị", "hiện thị", "lcd", "màn hình"]):
            if "dừng" in command_lower or "tắt" in command_lower:
                self.stop_scroll()
                return True
            elif "xóa" in command_lower or "clear" in command_lower:
                self.clear_display()
                return True
            else:
                # Extract text after display command
                for trigger in ["hiển thị", "hiện thị"]:
                    if trigger in command_lower:
                        text_start = command_lower.find(trigger) + len(trigger)
                        display_text = command[text_start:].strip()
                        if display_text:
                            self.set_display_text(display_text)
                            if len(display_text) > self.lcd_width:
                                self.start_scroll()
                            return True
                        break
        
        return False
    
    def is_text_scrolling(self):
        """Check if text is currently scrolling."""
        return self.is_scrolling
    
    def get_current_text(self):
        """Get the current display text."""
        return self.current_text
