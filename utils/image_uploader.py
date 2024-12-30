import os
import requests
from typing import Optional

class ImageUploader:
    @staticmethod
    async def upload_image(file) -> Optional[str]:
        """
        Upload an image to SM.MS and return the URL
        """
        try:
            # 获取API密钥    API_KEY = os.getenv("SMMS_API_KEY", "wLVadsW6aYifPtuZUWrCh4cyTsdNilnh")  # 从环境变量获取API密钥

            api_token = os.getenv("SMMS_API_KEY", "wLVadsW6aYifPtuZUWrCh4cyTsdNilnh")
            if not api_token:
                print("Warning: SMMS_API_KEY not set")
                return None
            
            # 准备上传
            headers = {'Authorization': api_token}
            files = {'smfile': file.file}
            
            # 发送请求
            response = requests.post(
                'https://sm.ms/api/v2/upload',
                headers=headers,
                files=files
            )
            
            # 检查响应
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data['data']['url']
                else:
                    print(f"Upload failed: {data.get('message')}")
                    return None
            else:
                print(f"Upload failed with status code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error uploading image: {str(e)}")
            return None
