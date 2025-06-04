def _update_analysis_result(self, result):
    """Cập nhật kết quả phân tích trên UI (được gọi từ thread chính)."""
    
    if result.startswith('<') and '>' in result:
        # Nếu là HTML, hiển thị trực tiếp
        self.result_label.setHtml(result)
    else:
        # Kiểm tra chế độ hiện tại
        if hasattr(self, 'current_mode') and self.current_mode == "qr":
            # Nếu đang ở chế độ QR, hiển thị văn bản đơn giản
            self.result_label.setText(result)
        else:
            # Đối với chế độ khác, tìm và chuyển URLs thành link có thể nhấp
            import re
            url_pattern = r'(https?://[^\s]+)'
            html_result = re.sub(url_pattern, r'<a href="\1">\1</a>', result)
            
            # Chỉ chuyển sang HTML nếu thực sự tìm thấy link
            if html_result != result:
                # Thêm thông báo về chế độ QR ở đầu kết quả
                notice = """<div style="background-color: #f8f9fa; padding: 8px; margin-bottom: 10px; border-left: 4px solid #ffc107; border-radius: 4px;">
                <b>Lưu ý:</b> Đã phát hiện liên kết trong kết quả. Trong chế độ thường, bạn chỉ có thể sao chép liên kết, không thể mở trực tiếp.
                Để mở liên kết trực tiếp, vui lòng chuyển sang <b>chế độ quét mã QR</b>.
                </div>"""
                
                html_result = notice + html_result
                self.result_label.setHtml(html_result)
                self.status_label.setText("Phân tích hoàn tất - Nhấp vào liên kết để sao chép")
                return
            else:
                self.result_label.setText(result)
    
    self.status_label.setText("Phân tích hoàn tất")
