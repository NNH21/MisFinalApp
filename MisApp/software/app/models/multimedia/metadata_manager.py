# File: software/app/models/multimedia/metadata_manager.py
from typing import Dict, Any, Optional
import os
import re
import tempfile
import shutil
import json

try:
    import mutagen
    from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

from ...utils import logger

class MetadataManager:
    """
    Component for managing audio file metadata.
    Handles extracting and storing metadata from audio files.
    """
    
    def __init__(self):
        """Initialize the metadata manager."""
        self.metadata_cache = {}  # Cache for metadata by file path
        self.artwork_cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            'resources', 'media_cache', 'artwork'
        )
        os.makedirs(self.artwork_cache_dir, exist_ok=True)
        logger.info("Metadata manager initialized")
        
        # Setup YouTube ID pattern for special handling
        self.youtube_id_pattern = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    
    def get_track_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary of track metadata
        """
        # Return cached metadata if available
        if file_path in self.metadata_cache:
            return self.metadata_cache[file_path]
            
        # Get file base name and extension
        file_name = os.path.basename(file_path)
        file_base, file_ext = os.path.splitext(file_name)
        
        # Default metadata
        metadata = {
            'title': file_base,
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'duration': 0,
            'position': 0,
            'file_path': file_path,
            'is_playing': True,
            'is_paused': False,
            'cover_url': None,
            'youtube_id': None
        }
        
        # Check if this is a YouTube file (the filename would be the video ID)
        youtube_id = None
        if self.youtube_id_pattern.match(file_base):
            youtube_id = file_base
            metadata['youtube_id'] = youtube_id
            metadata['thumbnail'] = f"https://i.ytimg.com/vi/{youtube_id}/mqdefault.jpg"
            
        # Try to extract artist and title from filename if it follows "Artist - Title" format
        if ' - ' in file_base and not youtube_id:
            parts = file_base.split(' - ', 1)
            if len(parts) == 2:
                artist, title = parts
                metadata['artist'] = artist.strip()
                metadata['title'] = title.strip()
        
        # Try to extract metadata using mutagen if available
        if MUTAGEN_AVAILABLE:
            try:
                audio = mutagen.File(file_path)
                
                if audio:
                    # Extract duration
                    if hasattr(audio.info, 'length'):
                        metadata['duration'] = audio.info.length
                    
                    if isinstance(audio, mutagen.mp3.MP3) and audio.tags:
                        # Title
                        if 'TIT2' in audio.tags:
                            metadata['title'] = str(audio.tags['TIT2'])
                        # Artist
                        if 'TPE1' in audio.tags:
                            metadata['artist'] = str(audio.tags['TPE1'])
                        # Album
                        if 'TALB' in audio.tags:
                            metadata['album'] = str(audio.tags['TALB'])
                        
                        # Extract album art if available
                        if 'APIC:' in audio.tags or 'APIC' in audio.tags:
                            apic = audio.tags['APIC:'] if 'APIC:' in audio.tags else audio.tags['APIC']
                            cover_path = self._save_cover_art(file_path, apic.data)
                            if cover_path:
                                metadata['cover_url'] = cover_path
                    
                    # FLAC, OGG, etc. with VorbisComment tags
                    elif hasattr(audio, 'tags') and audio.tags:
                        tags = audio.tags
                        
                        # Title
                        if 'TITLE' in tags:
                            metadata['title'] = str(tags['TITLE'][0])
                        # Artist
                        if 'ARTIST' in tags:
                            metadata['artist'] = str(tags['ARTIST'][0])
                        # Album
                        if 'ALBUM' in tags:
                            metadata['album'] = str(tags['ALBUM'][0])
                        
                        # Cover art for FLAC
                        if hasattr(audio, 'pictures') and audio.pictures:
                            cover_path = self._save_cover_art(file_path, audio.pictures[0].data)
                            if cover_path:
                                metadata['cover_url'] = cover_path
                    
                    # M4A with MP4 tags
                    elif isinstance(audio, mutagen.mp4.MP4):
                        # Title
                        if '\xa9nam' in audio:
                            metadata['title'] = str(audio['\xa9nam'][0])
                        # Artist
                        if '\xa9ART' in audio:
                            metadata['artist'] = str(audio['\xa9ART'][0])
                        # Album
                        if '\xa9alb' in audio:
                            metadata['album'] = str(audio['\xa9alb'][0])
                            
                        # Cover art
                        if 'covr' in audio:
                            cover_path = self._save_cover_art(file_path, audio['covr'][0])
                            if cover_path:
                                metadata['cover_url'] = cover_path
            
            except Exception as e:
                logger.warning(f"Error extracting metadata from {file_path}: {str(e)}")
        
        # Special case for YouTube files: Try to load metadata from adjacent JSON file
        if youtube_id:
            json_path = os.path.join(os.path.dirname(file_path), f"{youtube_id}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        yt_metadata = json.load(f)
                        
                    if 'title' in yt_metadata:
                        metadata['title'] = yt_metadata['title']
                    if 'channel' in yt_metadata:
                        metadata['artist'] = yt_metadata['channel']
                    if 'thumbnail' in yt_metadata:
                        metadata['cover_url'] = yt_metadata['thumbnail']
                        
                    metadata['album'] = 'YouTube'
                    logger.info(f"Successfully loaded metadata for YouTube video {youtube_id} - Title: {metadata['title']}")
                except Exception as e:
                    logger.warning(f"Error loading YouTube metadata from JSON: {str(e)}")
            else:
                # Try to look for a JSON file with a more general search
                try:
                    json_files = [f for f in os.listdir(os.path.dirname(file_path)) 
                                if f.startswith(youtube_id) and f.endswith('.json')]
                    if json_files:
                        json_path = os.path.join(os.path.dirname(file_path), json_files[0])
                        with open(json_path, 'r', encoding='utf-8') as f:
                            yt_metadata = json.load(f)
                            
                        if 'title' in yt_metadata:
                            metadata['title'] = yt_metadata['title']
                        if 'channel' in yt_metadata:
                            metadata['artist'] = yt_metadata['channel']
                        if 'thumbnail' in yt_metadata:
                            metadata['cover_url'] = yt_metadata['thumbnail']
                            
                        metadata['album'] = 'YouTube'
                        logger.info(f"Successfully loaded metadata for YouTube video {youtube_id} using alternative JSON path")
                except Exception as e:
                    logger.warning(f"Error during alternative YouTube metadata search: {str(e)}")
        
        # Cache the metadata
        self.metadata_cache[file_path] = metadata
        
        return metadata
    
    def update_track_metadata(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for an audio file.
        
        Args:
            file_path: Path to the audio file
            metadata: Dictionary of metadata to update
            
        Returns:
            Success status
        """
        if not MUTAGEN_AVAILABLE:
            logger.warning("Mutagen not available. Cannot update metadata.")
            return False
            
        try:
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Handle based on file type
            if file_ext == '.mp3':
                return self._update_mp3_metadata(file_path, metadata)
            elif file_ext == '.flac':
                return self._update_flac_metadata(file_path, metadata)
            elif file_ext == '.ogg' or file_ext == '.oga':
                return self._update_ogg_metadata(file_path, metadata)
            elif file_ext == '.m4a':
                return self._update_m4a_metadata(file_path, metadata)
            else:
                # For YouTube files, store metadata in a side JSON file
                youtube_id = os.path.splitext(os.path.basename(file_path))[0]
                if self.youtube_id_pattern.match(youtube_id):
                    json_path = os.path.join(os.path.dirname(file_path), f"{youtube_id}.json")
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                    logger.info(f"Saved YouTube metadata to {json_path}")
                    
                    # Update cache
                    if file_path in self.metadata_cache:
                        self.metadata_cache[file_path].update(metadata)
                    
                    return True
                
                logger.warning(f"Unsupported file type for metadata update: {file_ext}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating metadata for {file_path}: {str(e)}")
            return False
    
    def _update_mp3_metadata(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for MP3 files."""
        try:
            # Load ID3 tags
            try:
                tags = ID3(file_path)
            except:
                # Create ID3 tags if not present
                tags = ID3()
            
            # Update tags
            if 'title' in metadata:
                tags['TIT2'] = TIT2(encoding=3, text=metadata['title'])
            if 'artist' in metadata:
                tags['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
            if 'album' in metadata:
                tags['TALB'] = TALB(encoding=3, text=metadata['album'])
            
            # Save tags
            tags.save(file_path)
            
            # Update cache
            if file_path in self.metadata_cache:
                self.metadata_cache[file_path].update(metadata)
            
            logger.info(f"Updated MP3 metadata for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating MP3 metadata: {str(e)}")
            return False
    
    def _update_flac_metadata(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for FLAC files."""
        try:
            # Load FLAC file
            flac = mutagen.flac.FLAC(file_path)
            
            # Update tags
            if 'title' in metadata:
                flac['TITLE'] = [metadata['title']]
            if 'artist' in metadata:
                flac['ARTIST'] = [metadata['artist']]
            if 'album' in metadata:
                flac['ALBUM'] = [metadata['album']]
            
            # Save changes
            flac.save()
            
            # Update cache
            if file_path in self.metadata_cache:
                self.metadata_cache[file_path].update(metadata)
            
            logger.info(f"Updated FLAC metadata for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating FLAC metadata: {str(e)}")
            return False
    
    def _update_ogg_metadata(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for OGG files."""
        try:
            # Load OGG file
            ogg = mutagen.oggvorbis.OggVorbis(file_path)
            
            # Update tags
            if 'title' in metadata:
                ogg['TITLE'] = [metadata['title']]
            if 'artist' in metadata:
                ogg['ARTIST'] = [metadata['artist']]
            if 'album' in metadata:
                ogg['ALBUM'] = [metadata['album']]
            
            # Save changes
            ogg.save()
            
            # Update cache
            if file_path in self.metadata_cache:
                self.metadata_cache[file_path].update(metadata)
            
            logger.info(f"Updated OGG metadata for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating OGG metadata: {str(e)}")
            return False
    
    def _update_m4a_metadata(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for M4A files."""
        try:
            # Load M4A file
            m4a = mutagen.mp4.MP4(file_path)
            
            # Update tags
            if 'title' in metadata:
                m4a['\xa9nam'] = [metadata['title']]
            if 'artist' in metadata:
                m4a['\xa9ART'] = [metadata['artist']]
            if 'album' in metadata:
                m4a['\xa9alb'] = [metadata['album']]
            
            # Save changes
            m4a.save()
            
            # Update cache
            if file_path in self.metadata_cache:
                self.metadata_cache[file_path].update(metadata)
            
            logger.info(f"Updated M4A metadata for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating M4A metadata: {str(e)}")
            return False
    
    def _save_cover_art(self, file_path: str, cover_data: bytes) -> Optional[str]:
        """
        Save cover art data to a file.
        
        Args:
            file_path: Path of the source audio file
            cover_data: Binary data of the cover art
            
        Returns:
            Path to the saved cover art file, or None if failed
        """
        try:
            # Generate a unique filename based on the file path
            import hashlib
            file_hash = hashlib.md5(file_path.encode()).hexdigest()
            cover_filename = f"cover_{file_hash}.jpg"
            cover_path = os.path.join(self.artwork_cache_dir, cover_filename)
            
            # Save cover art
            with open(cover_path, 'wb') as f:
                f.write(cover_data)
            
            logger.info(f"Saved cover art to {cover_path}")
            return cover_path
            
        except Exception as e:
            logger.error(f"Error saving cover art: {str(e)}")
            return None
    
    def clear_cache(self):
        """Clear the metadata cache."""
        self.metadata_cache.clear()
    
    def save_youtube_metadata(self, video_id: str, metadata: Dict[str, Any], audio_file: str) -> bool:
        """
        Save YouTube video metadata to a JSON file alongside the audio file.
        
        Args:
            video_id: YouTube video ID
            metadata: Video metadata
            audio_file: Path to the associated audio file
            
        Returns:
            Success status
        """
        try:
            # Create JSON path based on audio file path
            json_path = os.path.join(os.path.dirname(audio_file), f"{video_id}.json")
            
            # Save metadata to JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved YouTube metadata to {json_path}")
            
            # Update cache for audio file
            self.metadata_cache[audio_file] = {
                'title': metadata.get('title', 'Unknown Title'),
                'artist': metadata.get('channel', 'YouTube'),
                'album': 'YouTube',
                'duration': metadata.get('duration', 0),
                'position': 0,
                'file_path': audio_file,
                'is_playing': True,
                'is_paused': False,
                'cover_url': metadata.get('thumbnail', None),
                'youtube_id': video_id
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving YouTube metadata: {str(e)}")
            return False