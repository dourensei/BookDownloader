from PIL import Image as PILImage
from PyPDF2 import PdfReader, PdfWriter
import common.logger_utils as log_utils

def images_to_pdf(image_paths : list[str], pdf_path: str) -> bool:
    """
    将图片转为 PDF 文件

    :param image_paths: 图片文件路径列表（必须按页码排序）
    :param pdf_path: PDF 文件保存路径
    """
    if not image_paths:
        return False
    
    try:
        # 读取第一张图，作为 PDF 文件的首页
        first_img = PILImage.open(image_paths[0]).convert("RGB")
        rest_imgs = []
        for path in image_paths[1:]:
            img = PILImage.open(path).convert("RGB")
            rest_imgs.append(img)
        
        # 将图片转为 PDF 文件（无目录）
        first_img.save(
            pdf_path,
            save_all=True,
            append_images=rest_imgs,
            resolution=100.0
        )

        log_utils.get_logger().info(f"创建 PDF 文件成功（{pdf_path}）")
        return True
    except Exception:
        log_utils.get_logger().exception(f"创建 PDF 文件异常（{pdf_path}）")
        return False

def add_pdf_outline(pdf_temp_path, pdf_final_path, outline_items) -> bool:
    """
    为 PDF 文件添加目录

    :param pdf_temp_path: 无目录 PDF 文件路径
    :param pdf_final_path: 添加目录后的 PDF 文件保存路径
    :param outline_items: 目录信息列表，格式为：
        [
            {"title": "1", "page": 1, "level": 0},
            {"title": "2", "page": 2, "level": 0},
            {"title": "2-1", "page": 2, "level": 1},
        ]
    """
    try:
        # 读取无目录 PDF 文件
        reader = PdfReader(pdf_temp_path)
        writer = PdfWriter()
        
        # 复制所有页
        for page in reader.pages:
            writer.add_page(page)
        
        # 创建目录
        parent_map = {0: None}  # 记录每级目录的父书签（level: 父书签对象）
        for item in outline_items:
            title = item["title"]
            page_num = item["page"] - 1  # PyPDF2 页码从 0 开始
            level = item.get("level", 0)
            
            # 添加书签
            bookmark = writer.add_outline_item(
                title=title,
                page_number=page_num,
                parent=parent_map.get(level - 1)
            )
            
            # 记录书签，作为下一级目录的父书签
            parent_map[level] = bookmark
        
        # 保存 PDF 文件
        with open(pdf_final_path, "wb") as f:
            writer.write(f)
        
        log_utils.get_logger().info(f"创建 PDF 文件成功（{pdf_final_path}）")
        return True
    except Exception:
        log_utils.get_logger().exception(f"创建 PDF 文件异常（{pdf_final_path}）")
        return False