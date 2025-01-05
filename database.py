import os
from supabase import create_client, Client

# Supabase 配置
url: str = os.environ.get("SUPABASE_URL","https://utskbomfxaqopnagtwss.supabase.co")
key: str = os.environ.get("SUPABASE_KEY","eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0c2tib21meGFxb3BuYWd0d3NzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYwOTQ2NjksImV4cCI6MjA1MTY3MDY2OX0.3d1Il8ZiXGANoVCJIlkJ6KXlVeiU7EP3dwYuV4x3ssI")

# 创建 Supabase 客户端
supabase: Client = create_client(url, key)

def get_db():
    """获取Supabase客户端实例"""
    return supabase


