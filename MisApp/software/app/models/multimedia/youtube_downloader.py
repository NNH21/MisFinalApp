# File: software/app/models/multimedia/youtube_downloader.py
from typing import Dict, List, Optional, Any
import os
import re
import tempfile
import shutil
import requests
import logging
import random
import urllib.parse
import time
import threading
import json
import html  

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

try:
    from pytube import YouTube, Search
    PYTUBE_AVAILABLE = True
except ImportError:
    PYTUBE_AVAILABLE = False

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

try:
    import pafy
    PAFY_AVAILABLE = True
    pafy.g.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')]
except ImportError:
    PAFY_AVAILABLE = False

from ...utils import logger, config

class YouTubeDownloader:
    """
    Component for searching YouTube and downloading audio from videos.
    """
    
    def __init__(self, media_converter=None):
        """Initialize the YouTube downloader."""
        self.media_converter = media_converter
        
        self.cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            'resources', 'media_cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'mis_youtube_temp')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.download_methods = []
        if PYTUBE_AVAILABLE:
            self.download_methods.append(self._download_with_pytube)
        if YT_DLP_AVAILABLE:
            self.download_methods.append(self._download_with_ytdlp)
        if PAFY_AVAILABLE:
            self.download_methods.append(self._download_with_pafy)
        
        self.download_methods.append(self._download_direct_stream)
    
    def search_youtube(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube based on a query.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of video information dictionaries
        """
        # Method 1: Use YouTube Data API if available
        if YOUTUBE_API_AVAILABLE and config.YOUTUBE_API_KEY:
            try:
                logger.info(f"Searching for '{query}' using YouTube Data API")
                youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY)
                
                search_response = youtube.search().list(
                    q=query,
                    part='id,snippet',
                    maxResults=max_results,
                    type='video'
                ).execute()
                
                videos = []
                for item in search_response.get('items', []):
                    if item['id']['kind'] == 'youtube#video':
                        video_info = {
                            'id': item['id']['videoId'],
                            'title': html.unescape(item['snippet']['title']),
                            'description': html.unescape(item['snippet']['description']),
                            'thumbnail': item['snippet']['thumbnails']['default']['url'],
                            'channel': html.unescape(item['snippet']['channelTitle']),
                            'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                        }
                        videos.append(video_info)
                
                logger.info(f"Found {len(videos)} videos for: {query}")
                return videos
            except HttpError as e:
                logger.error(f"YouTube API error: {str(e)}")
            except Exception as e:
                logger.error(f"Error searching with YouTube API: {str(e)}")
        
        if PYTUBE_AVAILABLE:
            try:
                logger.info(f"Searching for '{query}' using pytube Search")
                search = Search(query)
                videos = []
                
                results = search.results
                if len(results) > max_results:
                    results = results[:max_results]
                
                for video in results:
                    video_info = {
                        'id': video.video_id,
                        'title': html.unescape(video.title),
                        'description': '',  
                        'thumbnail': f"https://i.ytimg.com/vi/{video.video_id}/default.jpg",
                        'channel': html.unescape(video.author),
                        'url': f"https://www.youtube.com/watch?v={video.video_id}"
                    }
                    videos.append(video_info)
                
                logger.info(f"Found {len(videos)} videos for: {query}")
                return videos
            except Exception as e:
                logger.error(f"Error searching with pytube: {str(e)}")
        
        try:
            logger.info(f"Searching for '{query}' using direct web request")
            search_query = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={search_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error fetching search results: HTTP {response.status_code}")
                return []
            
            video_ids = re.findall(r"watch\?v=(\S{11})", response.text)
            unique_ids = []
            
            for vid in video_ids:
                if vid not in unique_ids:
                    unique_ids.append(vid)
                if len(unique_ids) >= max_results:
                    break
            
            videos = []
            for video_id in unique_ids:
                video_info = {
                    'id': video_id,
                    'title': f"YouTube Video {video_id}",  
                    'description': '',
                    'thumbnail': f"https://i.ytimg.com/vi/{video_id}/default.jpg",
                    'channel': 'YouTube',
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                }
                videos.append(video_info)
            
            self._fetch_video_titles(videos)
            
            logger.info(f"Found {len(videos)} videos for: {query}")
            return videos
        except Exception as e:
            logger.error(f"Error searching with direct method: {str(e)}")
        return []
    
    def _fetch_video_titles(self, videos: List[Dict[str, Any]]) -> None:
        """
        Try to fetch video titles for videos found via direct search.
        
        Args:
            videos: List of video info dictionaries to update with titles
        """
        for video in videos:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                }
                response = requests.get(video['url'], headers=headers)
                
                if response.status_code == 200:
                    # Try to extract title
                    title_match = re.search(r'<title>(.*?)</title>', response.text)
                    if title_match:
                        title = title_match.group(1)
                        
                        if " - YouTube" in title:
                            title = title.replace(" - YouTube", "")
                       
                        title = html.unescape(title)
                        video['title'] = title
                    
                    channel_match = re.search(r'"ownerChannelName":"(.*?)"', response.text)
                    if channel_match:
                        channel = channel_match.group(1)
                        channel = html.unescape(channel)
                        video['channel'] = channel
            except Exception as e:
                logger.warning(f"Error fetching title for video {video['id']}: {str(e)}")
    
    def download_audio(self, video_url: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Download audio from a YouTube video using multiple methods, ordered by preference.
        
        Args:
            video_url: YouTube video URL
            output_dir: Directory to save the file (defaults to cache dir)
            
        Returns:
            Path to the downloaded audio file, or None if all methods failed
        """
        # Setup output directory
        if not output_dir:
            output_dir = self.cache_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the video ID for unique filename
        video_id = None
        id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
        if id_match:
            video_id = id_match.group(1)
        else:
            video_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=11))
        
        output_file = os.path.join(output_dir, f"{video_id}.mp3")
        
        # Kiểm tra tệp đã tải xuống trước đó có hợp lệ hay không
        if os.path.exists(output_file):
            # Kiểm tra kích thước tệp (tối thiểu 10 KB)
            file_size = os.path.getsize(output_file)
            if file_size > 10 * 1024:  # Lớn hơn 10KB
                try:
                    # Thử đọc header của tệp MP3 để xác minh nó là MP3 hợp lệ
                    with open(output_file, 'rb') as f:
                        header = f.read(4)
                        if header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xfa'):
                            logger.info(f"Using cached YouTube audio at {output_file}")
                            return output_file
                        else:
                            logger.warning(f"Cached file exists but has invalid header: {output_file}")
                            # Xóa tệp không hợp lệ
                            os.remove(output_file)
                except Exception as e:
                    logger.warning(f"Error checking cached file: {str(e)}")
                    # Xóa tệp có thể bị hỏng
                    try:
                        os.remove(output_file)
                        logger.info(f"Removed potentially corrupt file: {output_file}")
                    except Exception:
                        pass
            else:
                logger.warning(f"Cached file exists but is too small ({file_size} bytes): {output_file}")
                # Xóa tệp quá nhỏ
                try:
                    os.remove(output_file)
                    logger.info(f"Removed small file: {output_file}")
                except Exception:
                    pass
        
        # Thử từng phương thức tải xuống, ưu tiên trong thứ tự
        for method in self.download_methods:
            try:
                logger.info(f"Trying download method: {method.__name__}")
                if method(video_url, output_file):
                    # Xác minh lại tệp tải xuống
                    if os.path.exists(output_file):
                        file_size = os.path.getsize(output_file)
                        if file_size < 10 * 1024:  # Nhỏ hơn 10KB
                            logger.warning(f"Downloaded file seems too small ({file_size} bytes), trying next method")
                            continue
                        
                        logger.info(f"Successfully downloaded audio to {output_file} ({file_size} bytes)")
                        return output_file
                    else:
                        logger.warning("Download method claimed success but file doesn't exist")
            except Exception as e:
                logger.error(f"{method.__name__} error: {str(e)}")
        
        # Tất cả phương thức đều thất bại
        logger.error("All download methods failed")
        return None
    
    def _download_with_pytube(self, video_url: str, output_file: str) -> bool:
        """
        Download YouTube audio using pytube.
        
        Args:
            video_url: YouTube video URL
            output_file: Target output file path
            
        Returns:
            True if successful, False otherwise
        """
        if not PYTUBE_AVAILABLE:
            return False
        
        try:
            logger.info(f"Downloading with pytube: {video_url}")
            yt = YouTube(video_url)
            
            # Get audio stream (prioritize higher quality)
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not audio_stream:
                logger.error(f"No audio stream found for {video_url}")
                return False
            
            # Download to temporary file first
            temp_file = audio_stream.download(output_path=os.path.dirname(output_file), 
                                             filename=os.path.splitext(os.path.basename(output_file))[0])
          
            if not temp_file.lower().endswith('.mp3'):
                os.rename(temp_file, output_file)
            
            return os.path.exists(output_file)
            
        except Exception as e:
            logger.error(f"Pytube download error: {str(e)}")
            return False
    
    def _download_with_ytdlp(self, video_url: str, output_file: str) -> bool:
        """
        Download YouTube audio using yt-dlp.
        
        Args:
            video_url: YouTube video URL
            output_file: Target output file path
            
        Returns:
            True if successful, False otherwise
        """
        if not YT_DLP_AVAILABLE:
            return False
        
        try:
            logger.info(f"Downloading with yt-dlp: {video_url}")
            
            output_path = output_file.replace('.mp3', '')
            
            ydl_opts = {
                # Select best audio format to ensure we get complete audio
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'quiet': False,  
                'no_warnings': False, 
                'extract_audio': True,
                'audio_format': 'mp3',
                'fragment_retries': 10,
                'skip_unavailable_fragments': False,
                'retries': 10,
                'socket_timeout': 30,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'prefer_ffmpeg': True,
            }
            
            if config.FFMPEG_PATH:
                import platform
                import shutil
                
                ffmpeg_exe = None
                if platform.system() == 'Windows':
                    potential_paths = [
                        os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg.exe'),
                        os.path.join(config.FFMPEG_PATH, 'ffmpeg.exe'),
                        config.FFMPEG_PATH if config.FFMPEG_PATH.endswith('.exe') else None
                    ]
                else:
                    potential_paths = [
                        os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg'),
                        os.path.join(config.FFMPEG_PATH, 'ffmpeg'),
                        config.FFMPEG_PATH
                    ]
                
                # Filter out None values
                potential_paths = [p for p in potential_paths if p]
                
                # Try each path
                for path in potential_paths:
                    if os.path.exists(path):
                        ffmpeg_exe = path
                        break
                
                if not ffmpeg_exe:
                    # Try using system FFmpeg
                    ffmpeg_exe = shutil.which('ffmpeg')
                
                if ffmpeg_exe:
                    logger.info(f"Using FFmpeg at {ffmpeg_exe} for yt-dlp")
                    ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_exe)
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Check if the file exists - the output format might be different
            if os.path.exists(output_file):
                # Verify file size to ensure it's not empty or truncated
                file_size = os.path.getsize(output_file)
                logger.info(f"Downloaded file size: {file_size} bytes")
                if file_size < 10000:  # Less than 10KB is probably incomplete
                    logger.warning(f"Downloaded file seems too small: {file_size} bytes")
                
                return True
                
            # Check for other possible filenames that yt-dlp might have created
            potential_files = [
                output_path + '.mp3',
                output_path + '.m4a',
                output_path + '.webm',
                output_path + '.opus',
                output_path + '.ogg'
            ]
            
            for potential in potential_files:
                if os.path.exists(potential):
                    # Verify file size
                    file_size = os.path.getsize(potential)
                    logger.info(f"Downloaded file size: {file_size} bytes")
                    
                    # If not .mp3, rename to .mp3
                    if potential != output_file:
                        os.rename(potential, output_file)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"YT-DLP download error: {str(e)}")
            return False
    
    def _download_with_pafy(self, video_url: str, output_file: str) -> bool:
        """
        Download YouTube audio using pafy.
        
        Args:
            video_url: YouTube video URL
            output_file: Target output file path
            
        Returns:
            True if successful, False otherwise
        """
        if not PAFY_AVAILABLE:
            return False
        
        try:
            logger.info(f"Downloading with pafy: {video_url}")
            video = pafy.new(video_url)
            
            # Get best audio stream
            audio = video.getbestaudio()
            if not audio:
                logger.error("No audio stream found with pafy")
                return False
            
            # Download the audio stream
            temp_file = audio.download(filepath=output_file)
            
            # If download succeeded but with a different extension, rename to .mp3
            if temp_file and os.path.exists(temp_file) and temp_file != output_file:
                os.rename(temp_file, output_file)
            
            return os.path.exists(output_file)
            
        except Exception as e:
            logger.error(f"Pafy download error: {str(e)}")
            return False
    
    def _download_direct_stream(self, video_url: str, output_file: str) -> bool:
        """
        Fallback method to download YouTube audio by direct streaming.
        This method doesn't require ffmpeg or any external libraries.
        
        Args:
            video_url: YouTube video URL
            output_file: Target output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Using direct streaming method for: {video_url}")
            
            # Get video ID
            video_id = None
            id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
            if id_match:
                video_id = id_match.group(1)
            else:
                logger.error("Could not extract video ID for direct streaming")
                return False
            
            # Step 1: Cập nhật headers với format mới để giống như một request thông thường
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'https://www.youtube.com/',
                'Cookie': 'CONSENT=YES+cb; YSC=something; VISITOR_INFO1_LIVE=something',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Upgrade-Insecure-Requests': '1',
                'Priority': 'high',
                'Cache-Control': 'max-age=0'
            }
            
            # Sử dụng cả /embed/ và /watch để có nhiều cách để lấy dữ liệu
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            
            # Thử lấy trang web bằng cả hai phương pháp
            response = None
            
            # Phương pháp 1: Thử lấy từ trang watch
            try:
                session = requests.Session()  # Sử dụng session để giữ cookies
                response = session.get(watch_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    logger.warning(f"Failed to get watch page: HTTP {response.status_code}")
                    # Thử phương pháp khác
                    response = session.get(embed_url, headers=headers, timeout=15)
                    if response.status_code != 200:
                        logger.warning(f"Failed to get embed page: HTTP {response.status_code}")
                        # Thử truy cập cả youtube mobile
                        response = session.get(f"https://m.youtube.com/watch?v={video_id}", headers=headers, timeout=15)
            except Exception as e:
                logger.warning(f"Error making request: {str(e)}")
                return False
                
            if not response or response.status_code != 200:
                logger.error("Failed to retrieve YouTube page content")
                return False
            
            # Step 2: Tìm kiếm URL audio bằng nhiều phương pháp khác nhau
            audio_url = None
            content_length = None
            
            # Phương pháp 1: Trích xuất từ JSON trong initPlayerResponse
            json_patterns = [
                r'var ytInitialPlayerResponse\s*=\s*(\{.+?\});</script>',
                r'var ytInitialPlayerResponse\s*=\s*(\{.+?\});',
                r'ytInitialPlayerResponse\s*=\s*({.+?});',
                r'"streamingData":({.+?}),"playbackTracking"',
                r'"adaptiveFormats":(\[.+?\]),"',
                r'"\\"streamingData\\"":({.+?}),"\\"playbackTracking\\""'
            ]
            
            for pattern in json_patterns:
                player_match = re.search(pattern, response.text, re.DOTALL)
                if player_match:
                    try:
                        import json
                        # Try to extract player data
                        json_text = player_match.group(1)
                        # Thay thế một số ký tự JSON không hợp lệ có thể có
                        json_text = json_text.replace('\\"', '"').replace('\\\\\"', '"').replace('\\\\"', '"')
                        
                        if json_text.startswith('{') or json_text.startswith('['):
                            try:
                                player_data = json.loads(json_text)
                                
                                # Xử lý dựa vào cấu trúc dữ liệu
                                if isinstance(player_data, dict):
                                    if 'streamingData' in player_data:
                                        streaming_data = player_data['streamingData']
                                        formats = streaming_data.get('adaptiveFormats', [])
                                        audio_formats = [f for f in formats if f.get('mimeType', '').startswith('audio/')]
                                        audio_formats.sort(key=lambda x: int(x.get('bitrate', 0)), reverse=True)
                                        
                                        for format in audio_formats:
                                            if 'url' in format:
                                                audio_url = format['url']
                                                if 'contentLength' in format:
                                                    content_length = int(format['contentLength'])
                                                logger.info(f"Found direct audio URL with bitrate: {format.get('bitrate', 'unknown')}")
                                                break
                                            elif 'signatureCipher' in format:
                                                # Trích xuất URL từ signatureCipher
                                                cipher_text = format['signatureCipher']
                                                cipher_parts = urllib.parse.parse_qs(cipher_text)
                                                if 's' in cipher_parts and 'url' in cipher_parts:
                                                    url_component = cipher_parts['url'][0]
                                                    signature = cipher_parts['s'][0]
                                                    # Giải mã signature - cần triển khai nếu cần thiết
                                                    # Thường thì signature sẽ được xử lý bởi các thư viện chuyên biệt
                                                    # Nhưng đôi khi URL đã có đủ thông tin để phát
                                                    audio_url = url_component
                                                    logger.info("Found audio URL via signatureCipher")
                                                    break
                                
                                if audio_url:
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON: {json_text[:50]}...")
                        else:
                            logger.warning(f"Extracted text is not valid JSON: {json_text[:50]}...")
                    except Exception as e:
                        logger.warning(f"Error processing player data: {str(e)}")
            
            # Phương pháp 2: Trích xuất từ thẻ <script> chứa YTCFG
            if not audio_url:
                try:
                    config_pattern = r'ytcfg\.set\s*\(\s*({.+?})\s*\);'
                    config_match = re.search(config_pattern, response.text, re.DOTALL)
                    if config_match:
                        import json
                        cfg_text = config_match.group(1)
                        try:
                            cfg_data = json.loads(cfg_text)
                            player_path = cfg_data.get('PLAYER_JS_URL')
                            if player_path:
                                player_url = f"https://www.youtube.com{player_path}" if player_path.startswith('/') else player_path
                                logger.info(f"Found player URL: {player_url}")
                                # Load player code to tìm hàm decoder
                                player_resp = requests.get(player_url, headers=headers)
                                if player_resp.status_code == 200:
                                    logger.info("Successfully retrieved player JS")
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse YTCFG JSON")
                except Exception as e:
                    logger.warning(f"Error extracting from YTCFG: {str(e)}")
            
            # Phương pháp 3: Sử dụng YouTube-DL core functionalities nếu yt-dlp có sẵn
            if not audio_url and YT_DLP_AVAILABLE:
                try:
                    # Load phiên bản downsized của yt-dlp để chỉ lấy direct URL
                    from yt_dlp import YoutubeDL
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': True,
                        'skip_download': True,
                    }
                    
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(video_url, download=False)
                        formats = info.get('formats', [])
                        audio_formats = [f for f in formats if 
                                        f.get('acodec', 'none') != 'none' and 
                                        f.get('vcodec', 'none') == 'none']
                        
                        if audio_formats:
                            audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
                            best_audio = audio_formats[0]
                            audio_url = best_audio.get('url')
                            if audio_url:
                                logger.info(f"Found audio URL using yt-dlp: bitrate={best_audio.get('abr', 'unknown')}")
                except Exception as e:
                    logger.warning(f"Error extracting with yt-dlp core: {str(e)}")
            
            # Nếu đã tìm thấy audio URL, tải xuống
            if audio_url:
                logger.info("Downloading audio directly from extracted URL")
                download_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity;q=1, *;q=0',
                    'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
                    'Referer': 'https://www.youtube.com/',
                    'Origin': 'https://www.youtube.com',
                    'Range': 'bytes=0-',
                    'Connection': 'keep-alive'
                }
                
                # Sử dụng session để duy trì cookies và headers
                if not hasattr(self, 'download_session'):
                    self.download_session = requests.Session()
                
                max_retries = 5  # Tăng số lần thử lại
                
                for attempt in range(max_retries):
                    try:
                        # Kiểm tra URL có validity trước khi tải xuống
                        head_response = self.download_session.head(audio_url, headers=download_headers, timeout=10)
                        if head_response.status_code >= 400:
                            logger.warning(f"Audio URL is not valid (status {head_response.status_code}), trying next method")
                            break
                            
                        server_content_length = None
                        if 'Content-Length' in head_response.headers:
                            server_content_length = int(head_response.headers['Content-Length'])
                            logger.info(f"Expected content length: {server_content_length} bytes")
                        
                        # Tải xuống tệp audio
                        response = self.download_session.get(audio_url, headers=download_headers, stream=True, timeout=60)
                        
                        # Kiểm tra phản hồi
                        if response.status_code in (200, 206):
                            # Tải xuống theo từng phần
                            total_size = 0
                            expected_size = int(response.headers.get('Content-Length', 0)) if 'Content-Length' in response.headers else None
                            
                            with open(output_file, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        total_size += len(chunk)
                            
                            logger.info(f"Downloaded {total_size} bytes")
                            
                            # Xác minh tệp tải xuống
                            if os.path.exists(output_file):
                                file_size = os.path.getsize(output_file)
                                logger.info(f"File size on disk: {file_size} bytes")
                                
                                # Kiểm tra tính toàn vẹn của tệp
                                if expected_size and abs(file_size - expected_size) > 1024:
                                    logger.warning(f"Download incomplete: got {file_size}, expected {expected_size}")
                                    if attempt < max_retries - 1:
                                        logger.info(f"Retrying download (attempt {attempt + 2}/{max_retries})")
                                        continue
                                elif file_size < 10000:  # Nhỏ hơn 10KB
                                    logger.error(f"Downloaded file is too small: {file_size} bytes")
                                    if attempt < max_retries - 1:
                                        logger.info(f"Retrying download (attempt {attempt + 2}/{max_retries})")
                                        continue
                                else:
                                    # Kiểm tra xem tệp có phải là MP3 hợp lệ hay không
                                    try:
                                        with open(output_file, 'rb') as f:
                                            header = f.read(4)
                                            if header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xfa'):
                                                logger.info(f"Successfully downloaded valid audio file: {output_file}")
                                                
                                                # Lưu metdata vào tệp JSON
                                                try:
                                                    metadata_file = os.path.join(os.path.dirname(output_file), f"{video_id}.json")
                                                    metadata = {
                                                        "id": video_id,
                                                        "title": f"YouTube Audio {video_id}",
                                                        "url": video_url,
                                                        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/default.jpg"
                                                    }
                                                    with open(metadata_file, 'w', encoding='utf-8') as f:
                                                        json.dump(metadata, f)
                                                except:
                                                    pass
                                                
                                                return True
                                            else:
                                                # Không phải là MP3 hợp lệ
                                                logger.warning("Downloaded file is not a valid audio file")
                                                if attempt < max_retries - 1:
                                                    logger.info(f"Retrying download (attempt {attempt + 2}/{max_retries})")
                                                    continue
                                    except Exception as e:
                                        logger.error(f"Error verifying audio file: {str(e)}")
                            else:
                                logger.error("File was not created")
                        else:
                            logger.error(f"Download failed with status {response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"Download attempt {attempt + 1} failed: {str(e)}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in 2 seconds...")
                            time.sleep(2)
                
                # Nếu tất cả các lần thử đều thất bại
                logger.error("All download attempts failed")
                return False
            else:
                logger.error("Could not extract any audio URL using multiple methods")
            
            return False
            
        except Exception as e:
            logger.error(f"Direct streaming error: {str(e)}")
            return False
    
    def search_and_download(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a video and download its audio.
        
        Args:
            query: Search query for the song
            
        Returns:
            Dictionary with audio information or None if failed
        """
        # Search for the video
        search_results = self.search_youtube(query, max_results=1)
        
        if not search_results:
            logger.error(f"No search results for: {query}")
            return None
        
        # Get the first result
        video = search_results[0]
        logger.info(f"Found: {video['title']} by {video['channel']}")
        
        # Download the audio
        audio_file = self.download_audio(video['url'])
        
        if not audio_file:
            logger.error(f"Failed to download: {video['title']}")
            return None
        
        # Save metadata to JSON file for better UX
        try:
            video_id = video.get('id')
            if video_id:
                # Make sure all text fields are properly decoded before saving
                for field in ['title', 'description', 'channel']:
                    if field in video and isinstance(video[field], str):
                        video[field] = html.unescape(video[field])
                
                json_path = os.path.join(os.path.dirname(audio_file), f"{video_id}.json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(video, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved video metadata to {json_path}")
        except Exception as e:
            logger.warning(f"Could not save metadata: {str(e)}")
        
        # Populate result with video and audio information
        result = {
            'audio_file': audio_file,
            'title': video['title'],
            'id': video['id'],
            'url': video['url'],
            'channel': video['channel'],
            'thumbnail': video['thumbnail']
        }
        
        return result
    
    def extract_song_name(self, query: str) -> str:
        """
        Extract the song name from a query like "play X" or "mở bài hát X".
        
        Args:
            query: The user's query
            
        Returns:
            The extracted song name
        """
        query = query.lower().strip()
        
        # Define patterns to extract song names from various phrasings
        patterns = [
            # Vietnamese patterns
            r'mở\s+bài\s+(?:hát|)\s+(.*)',  # "mở bài hát Despacito"
            r'phát\s+bài\s+(?:hát|)\s+(.*)',  # "phát bài hát Despacito"
            r'nghe\s+bài\s+(?:hát|)\s+(.*)',  # "nghe bài hát Despacito"
            r'(?:bật|mở)\s+nhạc\s+(.*)',  # "bật nhạc Despacito"
            
            # English patterns
            r'play\s+(.*)',  # "play Despacito"
            r'listen\s+to\s+(.*)',  # "listen to Despacito"
            
            # General patterns - if the above don't match
            r'(?:youtube|yt|video|audio|song|music|bài hát|nhạc|ca khúc)\s+(.*)',
            
            # Last resort - capture everything after common keywords
            r'(?:mở|phát|bật|play|listen|youtube|yt)\s+(.*)'
        ]
        
        # Try each pattern in order
        for pattern in patterns:
            match = re.search(pattern, query)
            if match and match.group(1):
                # Clean up any trailing noise words
                song_name = match.group(1).strip()
                # Remove common stop words at the end
                noise_words = ['nhé', 'nha', 'đi', 'ạ', 'không', 'please', 'for me', 'cho tôi', 'cho mình']
                for word in noise_words:
                    if song_name.endswith(f" {word}"):
                        song_name = song_name[:-(len(word)+1)].strip()
                
                return song_name
        
        # If no patterns match, return the entire query as a fallback
        # This handles simple queries like "Despacito"
        return query