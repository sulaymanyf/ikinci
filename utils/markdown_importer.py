import os
import re
from typing import Dict, List, Optional
import frontmatter
import markdown
from models import Item, Category, ItemImage
from database import SessionLocal
from sqlalchemy.orm import Session

class MarkdownImporter:
    @staticmethod
    def parse_price(price_str: str) -> float:
        """从字符串中提取价格数值"""
        # 移除所有非数字字符
        price_num = ''.join(filter(str.isdigit, str(price_str)))
        return float(price_num)

    @staticmethod
    def parse_markdown_file(file_path: str) -> Optional[Dict]:
        """解析单个markdown文件，提取frontmatter和内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                
                # 提取frontmatter数据
                metadata = post.metadata
                content = post.content
                
                # 确保必要的字段存在
                required_fields = ['title', 'price', 'condition', 'category']
                if not all(field in metadata for field in required_fields):
                    print(f"Warning: Missing required fields in {file_path}")
                    return None
                
                # 处理价格
                try:
                    price = MarkdownImporter.parse_price(metadata.get('price'))
                except (ValueError, TypeError) as e:
                    print(f"Error parsing price in {file_path}: {str(e)}")
                    return None
                
                # 提取图片URL
                image_urls = []
                img_pattern = r'!\[.*?\]\((.*?)\)'
                image_matches = re.findall(img_pattern, content)
                for img_url in image_matches:
                    # 转换相对路径为绝对路径
                    if not img_url.startswith(('http://', 'https://')):
                        img_url = os.path.join('/static', img_url.lstrip('/'))
                    image_urls.append(img_url)
                
                return {
                    'title': metadata.get('title'),
                    'price': price,
                    'condition': metadata.get('condition'),
                    'category': metadata.get('category'),
                    'description': content,
                    'image_urls': image_urls
                }
        except Exception as e:
            print(f"Error parsing {file_path}: {str(e)}")
            return None

    @staticmethod
    def import_to_database(data_dir: str, db: Session):
        """从指定目录导入所有markdown文件到数据库"""
        # 确保目录存在
        if not os.path.exists(data_dir):
            raise ValueError(f"Directory not found: {data_dir}")
        
        # 获取所有markdown文件
        md_files = [f for f in os.listdir(data_dir) if f.endswith('.md')]
        
        for md_file in md_files:
            file_path = os.path.join(data_dir, md_file)
            data = MarkdownImporter.parse_markdown_file(file_path)
            
            if not data:
                continue
            
            try:
                # 检查或创建分类
                category = db.query(Category).filter(Category.name == data['category']).first()
                if not category:
                    category = Category(name=data['category'])
                    db.add(category)
                    db.commit()
                    db.refresh(category)
                
                # 创建商品
                item = Item(
                    title=data['title'],
                    description=data['description'],
                    price=data['price'],
                    condition=data['condition'],
                    category_id=category.id,
                    user_id=1  # 默认用户ID
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                
                # 添加图片
                for img_url in data['image_urls']:
                    image = ItemImage(
                        image_url=img_url,
                        item_id=item.id
                    )
                    db.add(image)
                
                db.commit()
                print(f"Successfully imported: {data['title']}")
                
            except Exception as e:
                print(f"Error importing {md_file}: {str(e)}")
                db.rollback()
                continue
