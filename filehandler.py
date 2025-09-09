import aiohttp
import os
import tempfile
from pathlib import Path
import asyncio
from typing import Optional, Dict, Any
import logging

# PDF processing
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Word document processing  
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileHandler:
    
    def __init__(self):
        self.supported_extensions = {'.txt', '.pdf', '.doc', '.docx'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit
    
    def is_supported_file(self, filename: str, content_type: str = None) -> bool:
        """Check if file is supported for text extraction"""
        file_extension = Path(filename).suffix.lower()
        
        # Check by extension
        if file_extension in self.supported_extensions:
            return True
            
        # Check by content type as fallback
        if content_type:
            supported_types = {
                'text/plain',
                'application/pdf', 
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            return content_type in supported_types
            
        return False
    
    async def download_file(self, url: str, filename: str) -> Optional[str]:
        """Download file from URL and return temporary file path"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download file: HTTP {response.status}")
                        return None
                    
                    # Check file size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        logger.error(f"File too large: {content_length} bytes")
                        return None
                    
                    # Create temporary file
                    suffix = Path(filename).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)
                        temp_file_path = temp_file.name
                    
                    logger.info(f"Downloaded file to: {temp_file_path}")
                    return temp_file_path
                    
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def extract_text_from_txt(self, file_path: str) -> Optional[str]:
        """Extract text from .txt file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                logger.error(f"Error reading txt file with latin-1: {e}")
                return None
        except Exception as e:
            logger.error(f"Error reading txt file: {e}")
            return None
    
    def extract_text_from_pdf(self, file_path: str) -> Optional[str]:
        """Extract text from PDF file"""
        if not PDF_AVAILABLE:
            logger.error("PyPDF2 not installed. Cannot process PDF files.")
            return None
            
        try:
            text_content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content.append(page.extract_text())
                    
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error reading PDF file: {e}")
            return None
    
    def extract_text_from_docx(self, file_path: str) -> Optional[str]:
        """Extract text from .docx file"""
        if not DOCX_AVAILABLE:
            logger.error("python-docx not installed. Cannot process .docx files.")
            return None
            
        try:
            doc = Document(file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)
                
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error reading .docx file: {e}")
            return None
    
    def extract_text_from_doc(self, file_path: str) -> Optional[str]:
        """Extract text from .doc file (legacy Word format)"""
        # Note: .doc files are more complex to handle and would need additional libraries
        # like python-docx2txt or antiword. For now, return None with a message.
        logger.warning(".doc files are not yet supported. Please convert to .docx format.")
        return None
    
    def extract_text(self, file_path: str, filename: str) -> Optional[str]:
        """Extract text based on file extension"""
        file_extension = Path(filename).suffix.lower()
        
        if file_extension == '.txt':
            return self.extract_text_from_txt(file_path)
        elif file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            return self.extract_text_from_docx(file_path)
        elif file_extension == '.doc':
            return self.extract_text_from_doc(file_path)
        else:
            logger.error(f"Unsupported file extension: {file_extension}")
            return None
    
    def cleanup_temp_file(self, file_path: str):
        """Delete temporary file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary file: {e}")
    
    async def process_attachment(self, attachment_data: Dict[str, Any]) -> Optional[str]:
        """Process attachment and extract text content"""
        filename = attachment_data.get('filename', '')
        url = attachment_data.get('url', '')
        content_type = attachment_data.get('content_type', '')
        
        if not self.is_supported_file(filename, content_type):
            logger.info(f"File type not supported: {filename}")
            return None
        
        # Download file
        temp_file_path = await self.download_file(url, filename)
        if not temp_file_path:
            return None
        
        try:
            # Extract text
            text_content = self.extract_text(temp_file_path, filename)
            if text_content:
                # Clean up the text (remove excessive whitespace)
                text_content = '\n'.join(line.strip() for line in text_content.splitlines() if line.strip())
                logger.info(f"Successfully extracted text from {filename} ({len(text_content)} characters)")
            
            return text_content
            
        finally:
            # Always clean up temporary file
            self.cleanup_temp_file(temp_file_path)

# Create global instance
file_handler = FileHandler()