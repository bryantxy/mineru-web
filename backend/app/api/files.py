import json
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.file import File as FileModel
from app.models.parsed_content import ParsedContent
from app.utils.minio_client import minio_client, MINIO_BUCKET
from app.utils.user_dep import get_user_id
from app.services.parser import get_buckets

router = APIRouter()

@router.get("/files")
def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query('', description="按文件名搜索"),
    status: str = Query('', description="按状态筛选"),
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    query = db.query(FileModel).filter(FileModel.user_id == user_id)
    if search:
        query = query.filter(FileModel.filename.contains(search))
    if status:
        query = query.filter(FileModel.status == status.upper())
    total = query.count()
    files = query.order_by(FileModel.upload_time.desc()) \
        .offset((page-1)*page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "files": [f.to_dict() for f in files]
    }

@router.get("/files/{file_id}")
def file_detail(
    file_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    return file.to_dict()

@router.get("/files/{file_id}/download_url")
def file_download_url(
    file_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    from app.utils.minio_client import get_file_url
    url = get_file_url(file.minio_path)
    return {"url": url}

@router.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 删除 MinIO 对象
        minio_client.remove_object(MINIO_BUCKET, file.minio_path)

        # 删除解析内容
        db.query(ParsedContent).filter(
            ParsedContent.file_id == file_id,
            ParsedContent.user_id == user_id
        ).delete()

        # 删除文件记录
        db.delete(file)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

    return {"msg": "删除成功"}


@router.get("/files/{file_id}/content")
def get_file_content(
    file_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """
    代理获取文件内容，解决浏览器跨域问题
    """
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        response = minio_client.get_object(MINIO_BUCKET, file.minio_path)
        content_type = file.content_type or 'application/octet-stream'
        
        # 对 PDF 文件设置正确的 Content-Type
        if file.filename.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        
        # 读取文件内容到内存
        file_data = response.read()
        
        return Response(
            content=file_data,
            media_type=content_type,
            headers={
                'Content-Disposition': f'inline; filename="{file.filename}"',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(len(file_data))
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")


@router.get("/files/{file_id}/regions")
def get_file_regions(
    file_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """
    获取文件识别区域信息（从 middle.json）
    返回每页的识别区域包括位置、类型等信息
    """
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 获取 middle.json 文件路径
        file_name_stem = Path(file.minio_path).stem
        middle_json_path = f"{file_name_stem}_middle.json"
        
        # 获取 bucket，如果配置不存在则使用默认值
        try:
            buckets = get_buckets()
            mds_bucket = buckets[0]
        except Exception:
            mds_bucket = 'mds'  # 默认 bucket 名称
        
        # 从 MinIO 获取 middle.json
        try:
            response = minio_client.get_object(mds_bucket, middle_json_path)
            middle_json = json.loads(response.read().decode('utf-8'))
        except Exception:
            return {"regions": [], "message": "暂无识别区域信息"}
        
        # 解析 middle.json 提取区域信息
        regions = []
        pdf_info = middle_json.get('pdf_info', [])
        
        for page_info in pdf_info:
            page_idx = page_info.get('page_idx', 0)
            page_size = page_info.get('page_size', [0, 0])
            page_width = page_size[0] if len(page_size) > 0 else 0
            page_height = page_size[1] if len(page_size) > 1 else 0
            
            page_regions = []
            
            # 处理 preproc_blocks（预处理块，包含图片、表格等）
            preproc_blocks = page_info.get('preproc_blocks', [])
            for block in preproc_blocks:
                block_type = block.get('type', 'unknown')
                bbox = block.get('bbox', [])
                if bbox and len(bbox) >= 4:
                    page_regions.append({
                        'type': block_type,
                        'bbox': bbox,  # [x0, y0, x1, y1]
                        'category': 'preproc'
                    })
            
            # 处理 para_blocks（段落块）
            para_blocks = page_info.get('para_blocks', [])
            for block in para_blocks:
                block_type = block.get('type', 'unknown')
                bbox = block.get('bbox', [])
                if bbox and len(bbox) >= 4:
                    page_regions.append({
                        'type': block_type,
                        'bbox': bbox,
                        'category': 'para'
                    })
                
                # 处理嵌套的 lines（行）
                lines = block.get('lines', [])
                for line in lines:
                    line_bbox = line.get('bbox', [])
                    if line_bbox and len(line_bbox) >= 4:
                        line_type = 'text_line'
                        # 检查是否包含公式
                        spans = line.get('spans', [])
                        for span in spans:
                            if span.get('type') == 'interline_equation':
                                line_type = 'equation'
                                break
                        page_regions.append({
                            'type': line_type,
                            'bbox': line_bbox,
                            'category': 'line'
                        })
            
            regions.append({
                'page_idx': page_idx,
                'page_width': page_width,
                'page_height': page_height,
                'regions': page_regions
            })
        
        return {"regions": regions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取区域信息失败: {str(e)}")


@router.get("/files/{file_id}/download")
def download_file(
    file_id: int,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """
    下载原始文件
    """
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        response = minio_client.get_object(MINIO_BUCKET, file.minio_path)
        content_type = file.content_type or 'application/octet-stream'
        
        # 读取文件内容
        file_data = response.read()
        
        return Response(
            content=file_data,
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{file.filename}"',
                'Content-Length': str(len(file_data))
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}") 