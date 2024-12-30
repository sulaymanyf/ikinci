import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models

class DatabaseExporter:
    @staticmethod
    def export_to_json(export_dir: str = "exports") -> str:
        """
        将数据库中的所有数据导出为JSON文件
        :param export_dir: 导出目录
        :return: 导出文件的路径
        """
        # 确保导出目录存在
        os.makedirs(export_dir, exist_ok=True)
        
        # 创建数据库会话
        db: Session = SessionLocal()
        
        try:
            # 导出数据
            data = {
                "metadata": {
                    "export_date": datetime.now().isoformat(),
                    "version": "1.0"
                },
                "categories": [],
                "items": [],
                "images": []
            }
            
            # 导出分类
            categories = db.query(models.Category).all()
            for category in categories:
                data["categories"].append({
                    "id": category.id,
                    "name": category.name
                })
            
            # 导出商品
            items = db.query(models.Item).all()
            for item in items:
                item_data = {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "price": item.price,
                    "condition": item.condition,
                    "category_id": item.category_id,
                    "user_id": item.user_id,
                    "is_sold": item.is_sold
                }
                data["items"].append(item_data)
            
            # 导出图片
            images = db.query(models.ItemImage).all()
            for image in images:
                image_data = {
                    "id": image.id,
                    "item_id": image.item_id,
                    "image_url": image.image_url
                }
                data["images"].append(image_data)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_export_{timestamp}.json"
            filepath = os.path.join(export_dir, filename)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return filepath
            
        finally:
            db.close()
    
    @staticmethod
    def import_from_json(filepath: str) -> bool:
        """
        从JSON文件导入数据到数据库
        :param filepath: JSON文件路径
        :return: 是否成功
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        db: Session = SessionLocal()
        
        try:
            # 读取JSON文件
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 清空现有数据（可选）
            db.query(models.ItemImage).delete()
            db.query(models.Item).delete()
            db.query(models.Category).delete()
            
            # 导入分类
            category_map = {}  # 用于存储旧ID到新ID的映射
            for cat_data in data["categories"]:
                category = models.Category(name=cat_data["name"])
                db.add(category)
                db.flush()
                category_map[cat_data["id"]] = category.id
            
            # 导入商品
            item_map = {}  # 用于存储旧ID到新ID的映射
            for item_data in data["items"]:
                item = models.Item(
                    title=item_data["title"],
                    description=item_data["description"],
                    price=item_data["price"],
                    condition=item_data["condition"],
                    category_id=category_map.get(item_data["category_id"]),
                    user_id=item_data["user_id"],
                    is_sold=item_data["is_sold"]
                )
                db.add(item)
                db.flush()
                item_map[item_data["id"]] = item.id
            
            # 导入图片
            for image_data in data["images"]:
                image = models.ItemImage(
                    item_id=item_map.get(image_data["item_id"]),
                    image_url=image_data["image_url"]
                )
                db.add(image)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise e
        
        finally:
            db.close()

if __name__ == "__main__":
    # 示例用法
    try:
        # 导出数据
        export_path = DatabaseExporter.export_to_json()
        print(f"Data exported to: {export_path}")
        
        # 导入数据（谨慎使用，会清空现有数据）
        # success = DatabaseExporter.import_from_json(export_path)
        # print(f"Data import {'successful' if success else 'failed'}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
