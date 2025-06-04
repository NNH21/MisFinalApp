import logging
import os
import datetime
import sys
from . import config

# Tạo thư mục nhật ký nếu nó không tồn tại
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
os.makedirs(log_dir, exist_ok=True)

def setup_logger():

    logger = logging.getLogger('mis_assistant')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(console_handler)
    
    if config.ENABLE_TEXT_LOG:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f'mis_assistant_{today}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

def debug(message):
    try:
        logger.debug(message)
    except UnicodeEncodeError:
        logger.debug("Tin nhắn ghi nhật ký với các ký tự unicode (không thể hiển thị trong bảng điều khiển)")

def info(message):
    try:
        logger.info(message)
    except UnicodeEncodeError:
        logger.info("Tin nhắn ghi nhật ký với các ký tự unicode (không thể hiển thị trong bảng điều khiển)")

def warning(message):
    try:
        logger.warning(message)
    except UnicodeEncodeError:
        logger.warning("Tin nhắn ghi nhật ký với các ký tự unicode (không thể hiển thị trong bảng điều khiển)")

def error(message):
    try:
        logger.error(message)
    except UnicodeEncodeError:
        logger.error("Tin nhắn ghi nhật ký với các ký tự unicode (không thể hiển thị trong bảng điều khiển)")

def critical(message):
    try:
        logger.critical(message)
    except UnicodeEncodeError:
        logger.critical("Tin nhắn ghi nhật ký với các ký tự unicode (không thể hiển thị trong bảng điều khiển)")

def log_conversation(query, response):
    if config.ENABLE_TEXT_LOG:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        conversation_log_file = os.path.join(log_dir, f'conversation_{today}.txt')
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(conversation_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] User: {query}\n")
            f.write(f"[{timestamp}] Assistant: {response}\n\n")