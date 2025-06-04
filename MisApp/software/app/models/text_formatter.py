"""
Module xử lý và định dạng văn bản cho MIS Assistant
Cung cấp các tiện ích để định dạng văn bản, xử lý ký tự đặc biệt và chuẩn hóa nội dung
"""

import re
import html
from datetime import datetime
from ..utils import logger

class TextFormatter:
    """
    Lớp tiện ích để định dạng văn bản và xử lý ký tự đặc biệt
    """
    
    # CSS styles for news formatting
    NEWS_STYLES = """
    <style>
        .news-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 100%;
            margin: 0;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }
        
        .news-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 25px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .news-header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }        .news-title-main {
            font-size: 24px;
            font-weight: 700;
            margin: 0;
            position: relative;
            z-index: 1;
            /* Fallback color cho trình duyệt không hỗ trợ background-clip */
            color: #ffffff;
            /* Rainbow gradient background */
            background: linear-gradient(
                90deg,
                #ff0000 0%,
                #ff7f00 14.28%,
                #ffff00 28.57%,
                #00ff00 42.86%,
                #0000ff 57.14%,
                #4b0082 71.43%,
                #8b00ff 85.71%,
                #ff0000 100%
            );
            background-size: 300% 100%;
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            /* Text shadow cho fallback */
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            animation: rainbow-move 4s linear infinite;
        }
        
        /* Fallback cho các trình duyệt không hỗ trợ background-clip: text */
        @supports not (-webkit-background-clip: text) {
            .news-title-main {
                color: #ffffff !important;
                background: none !important;
                text-shadow: 
                    0 2px 4px rgba(0, 0, 0, 0.5),
                    0 0 20px rgba(255, 255, 255, 0.3),
                    0 0 30px rgba(102, 126, 234, 0.4) !important;
            }
        }@keyframes rainbow-move {
            0% {
                background-position: 0% 50%;
            }
            100% {
                background-position: 300% 50%;
            }
        }
          .news-subtitle {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.95);
            margin: 8px 0 0 0;
            position: relative;
            z-index: 1;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        }
        
        .news-content {
            padding: 0;
            background: #ffffff;
        }
        
        .news-item {
            background: #ffffff;
            margin: 0;
            padding: 25px;
            border-bottom: 1px solid #e8ecf0;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .news-item::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transform: scaleY(0);
            transition: transform 0.3s ease;
        }
        
        .news-item:hover {
            background: #f8f9ff;
            transform: translateX(5px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.1);
        }
        
        .news-item:hover::before {
            transform: scaleY(1);
        }
        
        .news-item:last-child {
            border-bottom: none;
        }
        
        .news-item-title {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
            margin: 0 0 12px 0;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .news-item-description {
            color: #5a6c7d;
            line-height: 1.6;
            margin: 0 0 16px 0;
            font-size: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .news-item-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #e8ecf0;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .news-date {
            font-size: 13px;
            color: #8b95a1;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .news-source {
            font-size: 13px;
            background: #e3f2fd;
            color: #1565c0;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .news-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border: 2px solid #667eea;
            border-radius: 25px;
            transition: all 0.3s ease;
            background: transparent;
        }
        
        .news-link:hover {
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        .news-stats {
            background: #f8f9fa;
            padding: 15px 25px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
            border-top: 1px solid #e8ecf0;
        }
        
        .no-news {
            text-align: center;
            padding: 40px 25px;
            color: #6c757d;
        }
        
        .no-news-icon {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }
        
        @media (max-width: 768px) {
            .news-item {
                padding: 20px;
            }
            
            .news-item-meta {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .news-header {
                padding: 16px 20px;
            }
            
            .news-title-main {
                font-size: 20px;
            }
        }
        
        .loading-shimmer {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: shimmer-loading 2s infinite;
        }
        
        @keyframes shimmer-loading {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
    </style>
    """
    
    @staticmethod
    def format_message_text(text):
        """
        Định dạng văn bản tin nhắn cho hiển thị trong UI
        - Chuyển đổi URLs thành liên kết
        - Xử lý dấu xuống dòng
        - Mã hóa ký tự đặc biệt
        - Định dạng văn bản trích dẫn
        - Định dạng tin tức theo format đặc biệt
        """
        try:
            # Kiểm tra xem có phải là tin tức không
            if "Tin tức mới nhất từ Việt Nam" in text and "tin):" in text:
                return TextFormatter.format_news_text(text)
            
            # Kiểm tra xem có phải là văn bản HTML không (nội dung thực sự)
            if (text.startswith('<!DOCTYPE html>') or 
                (text.startswith('<') and text.strip().endswith('>') and '<body' in text)):
                # HTML thực sự, trả về trực tiếp
                return text, "html"
                
            # Tìm và chuyển URLs thành link có thể nhấp
            url_pattern = r'(https?://[^\s]+)'
            text_with_links = re.sub(url_pattern, r'<a href="\1" target="_blank" rel="noopener">\1</a>', text)
                
            # Đầu tiên, mã hóa ký tự đặc biệt như <, >, &, "
            clean_text = html.escape(text)
            
            # Xử lý các dòng có '>' ở đầu (thường là để hiển thị trích dẫn)
            lines = clean_text.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('&gt;'):
                    # Định dạng dòng trích dẫn đẹp hơn
                    formatted_line = f'<div style="padding: 12px 16px; border-left: 4px solid #667eea; background: linear-gradient(135deg, #f8f9ff 0%, #e3f2fd 100%); color: #2c3e50; margin: 8px 0; border-radius: 0 8px 8px 0; font-style: italic;">{line[4:]}</div>'
                    lines[i] = formatted_line
            
            # Thay thế xuống dòng bằng thẻ <br>
            formatted_text = '<br>'.join(lines)
            
            # Nếu có URLs, sử dụng phiên bản có link
            if text_with_links != text:
                # Thêm các liên kết vào văn bản đã được định dạng
                pattern = r'&lt;a href=&quot;(.*?)&quot; target=&quot;_blank&quot; rel=&quot;noopener&quot;&gt;(.*?)&lt;/a&gt;'
                replacer = r'<a href="\1" target="_blank" rel="noopener" style="color: #667eea; text-decoration: none; border-bottom: 1px solid #667eea; transition: all 0.3s ease;">\2</a>'
                formatted_text = re.sub(pattern, replacer, html.escape(text_with_links).replace('\n', '<br>'))
                
            return formatted_text, "rich"
            
        except Exception as e:
            logger.error(f"Lỗi khi định dạng tin nhắn: {str(e)}")
            return text, "plain"
    
    @staticmethod
    def format_quote_text(text):
        """Định dạng văn bản trích dẫn với kiểu dáng đẹp hơn"""
        try:
            # Bắt đầu với một div chứa toàn bộ trích dẫn
            formatted = '''
            <div style="
                border-left: 4px solid #667eea; 
                padding: 16px 20px; 
                background: linear-gradient(135deg, #f8f9ff 0%, #e3f2fd 100%); 
                margin: 12px 0; 
                border-radius: 0 12px 12px 0;
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
                position: relative;
                overflow: hidden;
            ">
                <div style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 2px;
                    background: linear-gradient(90deg, #667eea, #764ba2);
                "></div>
            '''
            
            # Tách thành từng dòng và định dạng
            lines = text.strip().split('\n')
            for line in lines:
                if line.strip():
                    formatted += f'<p style="margin: 6px 0; color: #2c3e50; font-style: italic; line-height: 1.5;">{html.escape(line)}</p>'
            
            # Đóng div
            formatted += '</div>'
            return formatted
        except Exception as e:
            logger.error(f"Lỗi khi định dạng văn bản trích dẫn: {str(e)}")
            return text
    
    @staticmethod
    def normalize_vietnamese_text(text):
        """
        Chuẩn hóa văn bản tiếng Việt, loại bỏ các dấu không cần thiết
        và đảm bảo hiển thị đúng
        """
        try:
            # Giữ nguyên văn bản, chỉ thực hiện những thay thế cụ thể nếu cần
            # Loại bỏ các ký tự điều khiển không cần thiết
            normalized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
            return normalized.strip()
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn hóa văn bản tiếng Việt: {str(e)}")
            return text
    
    @staticmethod
    def is_html_content(text):
        """Kiểm tra xem một chuỗi văn bản có phải là nội dung HTML hay không"""
        if not text:
            return False
            
        # Kiểm tra các dấu hiệu HTML rõ ràng
        return (text.strip().startswith('<') and text.strip().endswith('>') and
                ('</div>' in text or '</p>' in text or '</a>' in text or '</h' in text or 
                 '</span>' in text or '</table>' in text or '</ul>' in text or '<br>' in text))
                 
    @staticmethod
    def format_poem_text(poem_text):
        """Định dạng văn bản thơ với kiểu dáng đặc biệt"""
        try:
            # Loại bỏ dấu '>' thường được sử dụng để trích dẫn thơ
            lines = poem_text.strip().split('\n')
            clean_lines = []
            for line in lines:
                if line.strip().startswith('>'):
                    clean_lines.append(line.strip()[1:].strip())
                else:
                    clean_lines.append(line.strip())
            
            # Tạo HTML với định dạng đẹp
            formatted = '''
            <div style="
                font-family: 'Georgia', serif;
                font-style: italic; 
                color: #2c3e50; 
                background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%); 
                padding: 20px 25px; 
                border-radius: 12px;
                margin: 15px 0;
                box-shadow: 0 4px 15px rgba(250, 177, 160, 0.2);
                position: relative;
                overflow: hidden;
            ">
                <div style="
                    position: absolute;
                    top: 10px;
                    right: 15px;
                    font-size: 40px;
                    opacity: 0.2;
                ">📜</div>
            '''
            
            for line in clean_lines:
                if line:
                    formatted += f'<p style="margin: 8px 0; font-size: 16px; line-height: 1.6; position: relative; z-index: 1;">{html.escape(line)}</p>'
                else:
                    # Dòng trống tạo khoảng cách giữa các đoạn thơ
                    formatted += '<div style="height: 16px;"></div>'
            formatted += '</div>'
            
            return formatted
        except Exception as e:
            logger.error(f"Lỗi khi định dạng văn bản thơ: {str(e)}")
            return poem_text
    
    @staticmethod
    def format_news_text(text):
        """
        Định dạng văn bản tin tức theo format đặc biệt với thiết kế chuyên nghiệp
        Format: Tiêu đề + Mô tả + Thời gian + Link đọc thêm
        """
        try:
            # Kiểm tra xem có phải là tin tức không
            if "Tin tức mới nhất từ Việt Nam" in text and "tin):" in text:
                lines = text.split('\n')
                  # Đếm số lượng tin tức - limit to 5
                news_count = min(text.count('📅') if '📅' in text else len([l for l in lines if l.strip() and not l.startswith('Tin tức')]), 5)
                
                # Bắt đầu HTML với CSS và container
                formatted_html = TextFormatter.NEWS_STYLES
                formatted_html += '<div class="news-container">'
                  # Header section
                header_line = next((line for line in lines if "Tin tức mới nhất từ Việt Nam" in line), "Tin tức mới nhất từ Việt Nam")
                current_time = datetime.now().strftime("%d/%m/%Y - %H:%M")
                
                formatted_html += f'''
                <div class="news-header">
                    <h1 class="news-title-main">📰 {header_line}</h1>
                    <p class="news-subtitle">Cập nhật lúc {current_time} • {news_count} tin tức</p>
                </div>
                '''
                
                # Content section
                formatted_html += '<div class="news-content">'
                  # Process news items - limit to first 5 items
                news_items = TextFormatter._parse_news_items(lines)
                if news_items:
                    # Limit to first 5 news items
                    news_items = news_items[:5]
                
                if news_items:
                    for i, item in enumerate(news_items):
                        formatted_html += TextFormatter._format_single_news_item(item, i + 1)
                else:
                    formatted_html += '''
                    <div class="no-news">
                        <div class="no-news-icon">📰</div>
                        <p>Không có tin tức nào được tìm thấy.</p>
                    </div>
                    '''
                
                # Footer với thống kê
                if news_items:
                    formatted_html += f'''
                    <div class="news-stats">
                        Hiển thị {len(news_items)} tin tức mới nhất • Dữ liệu được cập nhật tự động
                    </div>
                    '''
                
                formatted_html += '</div></div>' 
                
                return formatted_html, "html"
            
            return text, "plain"
            
        except Exception as e:
            logger.error(f"Lỗi khi định dạng tin tức: {str(e)}")
            return text, "plain"
    
    @staticmethod
    def _parse_news_items(lines):
        """Parse news items from text lines"""
        news_items = []
        current_item = {}
        
        for line in lines[2:]:  # Skip header and empty line
            line = line.strip()
            if not line:
                # Empty line might indicate end of current news item
                if current_item.get('title') and current_item.get('description'):
                    news_items.append(current_item.copy())
                    current_item = {}
                continue
            
            if line.startswith('📅'):
                current_item['date'] = line.replace('📅', '').strip()
            elif line.startswith('<a href=') or 'href=' in line:
                # Extract link information
                link_match = re.search(r'<a href="([^"]*)"[^>]*>([^<]*)</a>', line)
                if link_match:
                    current_item['link_url'] = link_match.group(1)
                    current_item['link_text'] = link_match.group(2)
                else:
                    current_item['link_text'] = line
                
                # End of current item, add to list
                if current_item.get('title') and current_item.get('description'):
                    news_items.append(current_item.copy())
                    current_item = {}
            elif not current_item.get('title'):
                current_item['title'] = line
            elif not current_item.get('description'):
                current_item['description'] = line
        
        # Handle last item if exists
        if current_item.get('title') and current_item.get('description'):
            news_items.append(current_item)
        
        return news_items
    
    @staticmethod
    def _format_single_news_item(item, index):
        """Format a single news item with professional styling"""
        title = html.escape(item.get('title', 'Không có tiêu đề'))
        description = html.escape(item.get('description', 'Không có mô tả'))
        date = item.get('date', 'Không rõ thời gian')
        link_url = item.get('link_url', '')
        link_text = item.get('link_text', 'Đọc thêm')
        
        # Format date nicely
        date_formatted = date
        if '📅' not in date and date != 'Không rõ thời gian':
            date_formatted = f"📅 {date}"
        
        # Extract source from URL if available
        source = "Nguồn tin"
        if link_url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(link_url)
                domain = parsed_url.netloc
                if domain:
                    source = domain.replace('www.', '').title()
            except:
                pass
        
        # Create read more link
        read_more_link = ""
        if link_url:
            read_more_link = f'''
            <a href="{link_url}" class="news-link" target="_blank" rel="noopener">
                {html.escape(link_text)} <span>→</span>
            </a>
            '''
        
        return f'''
        <div class="news-item" data-index="{index}">
            <h3 class="news-item-title">{title}</h3>
            <p class="news-item-description">{description}</p>
            <div class="news-item-meta">
                <div style="display: flex; gap: 15px; align-items: center;">
                    <span class="news-date">{date_formatted}</span>
                    <span class="news-source">{source}</span>
                </div>
                {read_more_link}
            </div>
        </div>
        '''
    
    @staticmethod
    def format_error_message(error_msg, context=""):
        """Format error messages with professional styling"""
        try:
            formatted = f'''
            <div style="
                background: linear-gradient(135deg, #ff7675 0%, #fd79a8 100%);
                color: white;
                padding: 16px 20px;
                border-radius: 12px;
                margin: 12px 0;
                box-shadow: 0 4px 15px rgba(255, 118, 117, 0.2);
                border-left: 4px solid #d63031;
            ">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <span style="font-size: 20px;">⚠️</span>
                    <strong>Có lỗi xảy ra</strong>
                </div>
                <p style="margin: 0; opacity: 0.9;">{html.escape(error_msg)}</p>
                {f'<small style="opacity: 0.7; margin-top: 8px; display: block;">Ngữ cảnh: {html.escape(context)}</small>' if context else ''}
            </div>
            '''
            return formatted
        except Exception as e:
            logger.error(f"Lỗi khi định dạng thông báo lỗi: {str(e)}")
            return f"<p style='color: red;'>Lỗi: {error_msg}</p>"
    
    @staticmethod
    def format_loading_placeholder():
        """Create loading placeholder for news content"""
        return '''
        <div class="news-container">
            <div class="news-header">
                <h1 class="news-title-main">📰 Đang tải tin tức...</h1>
                <p class="news-subtitle">Vui lòng chờ trong giây lát</p>
            </div>
            <div class="news-content">
                <div class="news-item loading-shimmer" style="height: 120px;"></div>
                <div class="news-item loading-shimmer" style="height: 120px;"></div>
                <div class="news-item loading-shimmer" style="height: 120px;"></div>
            </div>
        </div>
        '''