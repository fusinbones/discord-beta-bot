"""
Image Storage System for Ambassador Program
Handles permanent storage of Discord attachments to prevent link expiration
"""

import os
import base64
import hashlib
import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, Dict, Tuple
from supabase import Client
import logging

class ImageStorageManager:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
        
    async def store_discord_attachment(self, attachment_url: str, ambassador_id: str, submission_id: str) -> Dict:
        """
        Download and store a Discord attachment permanently
        
        Returns:
            Dict with 'success', 'stored_url', 'file_size', 'error' keys
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            url_hash = hashlib.md5(attachment_url.encode()).hexdigest()[:8]
            filename = f"ambassador_{ambassador_id}_{submission_id}_{timestamp}_{url_hash}"
            
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment_url) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f'Failed to download image: HTTP {response.status}'
                        }
                    
                    # Check file size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        return {
                            'success': False,
                            'error': f'File too large: {content_length} bytes (max: {self.max_file_size})'
                        }
                    
                    # Read image data
                    image_data = await response.read()
                    
                    if len(image_data) > self.max_file_size:
                        return {
                            'success': False,
                            'error': f'File too large: {len(image_data)} bytes'
                        }
                    
                    # Get content type
                    content_type = response.headers.get('content-type', 'image/png')
                    file_extension = self._get_extension_from_content_type(content_type)
                    full_filename = f"{filename}.{file_extension}"
                    
                    # Convert to base64 for database storage
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    
                    # Store in Supabase
                    storage_result = await self._store_in_database(
                        filename=full_filename,
                        base64_data=base64_data,
                        content_type=content_type,
                        file_size=len(image_data),
                        ambassador_id=ambassador_id,
                        submission_id=submission_id,
                        original_url=attachment_url
                    )
                    
                    if storage_result['success']:
                        return {
                            'success': True,
                            'stored_url': storage_result['access_url'],
                            'file_size': len(image_data),
                            'filename': full_filename,
                            'storage_id': storage_result['storage_id']
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'Database storage failed: {storage_result["error"]}'
                        }
                        
        except Exception as e:
            logging.error(f"Image storage error: {e}")
            return {
                'success': False,
                'error': f'Storage system error: {str(e)}'
            }
    
    async def _store_in_database(self, filename: str, base64_data: str, content_type: str, 
                               file_size: int, ambassador_id: str, submission_id: str, 
                               original_url: str) -> Dict:
        """Store image data in Supabase database"""
        try:
            # Insert into stored_images table
            result = self.supabase.table('stored_images').insert({
                'filename': filename,
                'base64_data': base64_data,
                'content_type': content_type,
                'file_size': file_size,
                'ambassador_id': ambassador_id,
                'submission_id': submission_id,
                'original_discord_url': original_url,
                'created_at': datetime.now().isoformat(),
                'access_count': 0
            }).execute()
            
            if result.data:
                storage_id = result.data[0]['id']
                # Generate access URL (will be handled by a separate endpoint)
                access_url = f"https://your-domain.com/api/image/{storage_id}"
                
                return {
                    'success': True,
                    'storage_id': storage_id,
                    'access_url': access_url
                }
            else:
                return {
                    'success': False,
                    'error': 'Database insert failed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_stored_image(self, storage_id: str) -> Optional[Dict]:
        """Retrieve stored image by ID"""
        try:
            result = self.supabase.table('stored_images').select('*').eq('id', storage_id).execute()
            
            if result.data:
                image_record = result.data[0]
                
                # Increment access count
                self.supabase.table('stored_images').update({
                    'access_count': image_record['access_count'] + 1,
                    'last_accessed': datetime.now().isoformat()
                }).eq('id', storage_id).execute()
                
                return {
                    'filename': image_record['filename'],
                    'base64_data': image_record['base64_data'],
                    'content_type': image_record['content_type'],
                    'file_size': image_record['file_size']
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Image retrieval error: {e}")
            return None
    
    async def cleanup_old_images(self, days_old: int = 365) -> int:
        """Clean up images older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Get old images
            old_images = self.supabase.table('stored_images').select('id').lt(
                'created_at', cutoff_date.isoformat()
            ).execute()
            
            if old_images.data:
                # Delete old images
                for image in old_images.data:
                    self.supabase.table('stored_images').delete().eq('id', image['id']).execute()
                
                return len(old_images.data)
            
            return 0
            
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
            return 0
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type"""
        type_map = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp'
        }
        return type_map.get(content_type.lower(), 'png')

    async def get_image_stats(self) -> Dict:
        """Get storage statistics"""
        try:
            # Get total count and size
            result = self.supabase.table('stored_images').select('file_size').execute()
            
            if result.data:
                total_count = len(result.data)
                total_size = sum(img['file_size'] for img in result.data)
                avg_size = total_size / total_count if total_count > 0 else 0
                
                return {
                    'total_images': total_count,
                    'total_size_bytes': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'average_size_bytes': round(avg_size),
                    'average_size_kb': round(avg_size / 1024, 2)
                }
            
            return {
                'total_images': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'average_size_bytes': 0,
                'average_size_kb': 0
            }
            
        except Exception as e:
            logging.error(f"Stats error: {e}")
            return {'error': str(e)}
