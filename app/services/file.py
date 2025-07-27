"""
파일 업로드 서비스
"""
import os
import uuid
import shutil
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
from app.config import settings

class FileService:
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
        # 업로드 디렉토리 생성
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def save_uploaded_file(self, file: UploadFile, subfolder: str = "general") -> str:
        """업로드된 파일을 저장하고 경로를 반환"""
        try:
            # 파일 확장자 검증
            if not self._is_allowed_file(file.filename):
                raise HTTPException(
                    status_code=400,
                    detail="허용되지 않는 파일 형식입니다. JPG, PNG, GIF, WEBP만 허용됩니다."
                )
            
            # 파일 크기 검증
            file.file.seek(0, 2)  # 파일 끝으로 이동
            file_size = file.file.tell()
            file.file.seek(0)  # 파일 처음으로 이동
            
            if file_size > self.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail="파일 크기가 10MB를 초과합니다."
                )
            
            # 파일명 생성
            file_extension = os.path.splitext(file.filename)[1].lower()
            new_filename = f"{uuid.uuid4()}{file_extension}"
            
            # 서브폴더 생성
            subfolder_path = os.path.join(self.upload_dir, subfolder)
            os.makedirs(subfolder_path, exist_ok=True)
            
            # 파일 저장 경로
            file_path = os.path.join(subfolder_path, new_filename)
            
            # 파일 저장
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 이미지 파일인 경우 리사이즈
            if file_extension in {'.jpg', '.jpeg', '.png'}:
                self._resize_image(file_path)
            
            # 상대 경로 반환
            return os.path.join(subfolder, new_filename).replace("\\", "/")
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"파일 저장 중 오류가 발생했습니다: {str(e)}"
            )
    
    def _is_allowed_file(self, filename: str) -> bool:
        """허용된 파일 확장자인지 확인"""
        if not filename:
            return False
        return os.path.splitext(filename)[1].lower() in self.allowed_extensions
    
    def _resize_image(self, file_path: str, max_size: tuple = (800, 600)) -> None:
        """이미지 리사이즈"""
        try:
            with Image.open(file_path) as img:
                # EXIF 정보 기반 회전
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif is not None:
                        orientation = exif.get(0x0112)
                        if orientation == 3:
                            img = img.rotate(180, expand=True)
                        elif orientation == 6:
                            img = img.rotate(270, expand=True)
                        elif orientation == 8:
                            img = img.rotate(90, expand=True)
                
                # 리사이즈
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 품질 조정하여 저장
                img.save(file_path, optimize=True, quality=85)
                
        except Exception as e:
            # 리사이즈 실패해도 원본 파일은 유지
            pass
    
    def get_file_url(self, file_path: str) -> str:
        """파일 URL 생성"""
        if not file_path:
            return ""
        return f"{settings.base_url}/uploads/{file_path}"
    
    def delete_file(self, file_path: str) -> bool:
        """파일 삭제"""
        try:
            full_path = os.path.join(self.upload_dir, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception:
            return False
