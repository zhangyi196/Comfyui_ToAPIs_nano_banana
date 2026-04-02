import torch
import requests
from PIL import Image
import io
import time
import numpy as np
from typing import Dict, Any, Tuple


class ToAPIGenNode:
    """
    ComfyUI 自定义节点：调用 ToAPIs 的图生图接口
    支持上传、生成、轮询等完整工作流
    """
    
    def __init__(self):
        self.base_url = "https://toapis.com/v1"
    
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "mode": (["text-to-image", "image-to-image"], {"default": "image-to-image"}),
                "api_key": ("STRING", {"multiline": False}),
                "prompt": ("STRING", {"multiline": True}),
                "model": (["gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview", "gemini-2.5-flash-image-preview"], {"default": "gemini-3-pro-image-preview"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "size": (["1:1", "2:3", "3:2", "3:4", "4:3", "16:9"], {"default": "3:2"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "image_5": ("IMAGE",),
                "image_6": ("IMAGE",),
                "image_7": ("IMAGE",),
                "image_8": ("IMAGE",),
                "image_9": ("IMAGE",),
                "image_10": ("IMAGE",),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "image_url", "response")
    FUNCTION = "execute"
    CATEGORY = "image/ToAPIs"
    
    def tensor_to_pil(self, image_tensor: torch.Tensor) -> Image.Image:
        """
        将 ComfyUI Tensor 转换为 PIL Image
        
        Args:
            image_tensor: shape (B, H, W, C) 的 torch.Tensor，值范围 [0, 1]
        
        Returns:
            PIL Image 对象
        """
        # 获取第一张图片 (batch 维度)
        if image_tensor.dim() == 4:
            image_tensor = image_tensor[0]
        
        # 确保在 CPU 上并转换为 float32
        image_tensor = image_tensor.cpu().float()
        
        # 转换为 numpy 数组
        image_np = image_tensor.numpy()
        
        # 值范围 [0, 1] 转换为 [0, 255]
        # 使用更安全的方式处理，避免溢出
        image_np = np.clip(image_np, 0.0, 1.0)
        image_np = (image_np * 255.0).astype(np.uint8)
        
        # 确保是 RGB 模式 (H, W, C)
        if image_np.shape[2] == 4:  # RGBA
            image_pil = Image.fromarray(image_np, mode='RGBA')
            image_pil = image_pil.convert('RGB')
        elif image_np.shape[2] == 3:  # RGB
            image_pil = Image.fromarray(image_np, mode='RGB')
        elif image_np.shape[2] == 1:  # Grayscale
            image_pil = Image.fromarray(image_np[:, :, 0], mode='L')
            image_pil = image_pil.convert('RGB')
        else:
            raise Exception(f"不支持的通道数: {image_np.shape[2]}")
        
        return image_pil
    
    def pil_to_tensor(self, image_pil: Image.Image) -> torch.Tensor:
        """
        将 PIL Image 转换为 ComfyUI Tensor
        
        Args:
            image_pil: PIL Image 对象
        
        Returns:
            shape (1, H, W, C) 的 torch.Tensor，值范围 [0, 1]
        """
        # 确保图片是 RGB 模式
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
        
        # 转换为 numpy 数组
        image_np = np.array(image_pil).astype(np.float32)
        
        # 值范围 [0, 255] 转换为 [0, 1]
        image_np = image_np / 255.0
        
        # 转换为 torch.Tensor，添加 batch 维度
        image_tensor = torch.from_numpy(image_np).unsqueeze(0)
        return image_tensor
    
    def upload_image(self, image_pil: Image.Image, api_key: str) -> str:
        """
        上传图片到 ToAPIs，获取 URL
        
        Args:
            image_pil: PIL Image 对象
            api_key: API 密钥
        
        Returns:
            图片 URL
        
        Raises:
            Exception: 上传失败
        """
        url = f"{self.base_url}/uploads/images"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # 确保是 RGB 模式
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
        
        # 将 PIL Image 转换为二进制流，使用无损 PNG 格式
        img_bytes = io.BytesIO()
        # PNG 是无损格式，最适合保存原始质量
        image_pil.save(img_bytes, format='PNG', optimize=False)
        img_bytes.seek(0)
        
        files = {"file": ("image.png", img_bytes, "image/png")}
        
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        
        data = response.json()
        if "data" not in data or "url" not in data["data"]:
            raise Exception(f"上传响应格式错误: {data}")
        
        return data["data"]["url"]
    
    def generate_image(
        self,
        api_key: str,
        prompt: str,
        model: str,
        resolution: str,
        size: str,
        mode: str,
        image_url: str = None
    ) -> str:
        """
        调用图生图/文生图接口生成图片
        
        Args:
            api_key: API 密钥
            prompt: 提示词
            model: 模型名称
            resolution: 分辨率
            size: 宽高比
            mode: 生成模式 ('text-to-image' 或 'image-to-image')
            image_url: 图片 URL (仅在 image-to-image 模式使用)
        
        Returns:
            任务 ID
        
        Raises:
            Exception: 生成失败
        """
        url = f"{self.base_url}/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 构建基础 payload
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1,
            "metadata": {"resolution": resolution}
        }
        
        # 根据模式调整 payload
        if mode == "image-to-image":
            if image_url is None:
                raise Exception("图生图模式必须提供图片 URL")
            # 注意：image_urls 应该是字符串数组，不是对象数组
            payload["image_urls"] = [image_url]
        elif mode == "text-to-image":
            # 文生图模式不需要 image_urls
            pass
        else:
            raise Exception(f"未知的生成模式: {mode}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # 输出完整的错误响应信息
            error_details = f"HTTP {response.status_code}"
            try:
                error_body = response.text
                if error_body:
                    print(f"[ToAPIGenNode] 响应内容: {error_body[:500]}")
                    error_details += f" - {error_body[:500]}"
            except:
                pass
            raise Exception(f"API 请求失败: {error_details}, 请求体: {payload}")
        
        data = response.json()
        if "id" not in data:
            print(f"[ToAPIGenNode] 完整响应: {data}")
            raise Exception(f"生成响应格式错误: {data}")
        
        return data["id"]
    
    def poll_task_status(self, task_id: str, api_key: str, max_retries: int = 60) -> Tuple[str, str]:
        """
        轮询任务状态，直到完成
        
        Args:
            task_id: 任务 ID
            api_key: API 密钥
            max_retries: 最大重试次数 (60 * 4s = 240秒)
        
        Returns:
            (完成后的图片 URL, 最终响应的JSON字符串)
        
        Raises:
            Exception: 任务失败或超时
        """
        url = f"{self.base_url}/images/generations/{task_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        for attempt in range(max_retries):
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            status = data.get("status")
            
            if status == "completed":
                # 处理新的响应格式：result.data[0].url
                if "result" in data and "data" in data["result"] and len(data["result"]["data"]) > 0:
                    result_url = data["result"]["data"][0]["url"]
                    return result_url, str(data)
                # 兼容旧的响应格式：data.url
                elif "data" in data and "url" in data["data"]:
                    result_url = data["data"]["url"]
                    return result_url, str(data)
                else:
                    raise Exception(f"任务完成但无法找到结果 URL，响应: {data}")
            
            elif status == "failed":
                raise Exception(f"任务失败: {data.get('error', '未知错误')}")
            
            # 继续轮询，等待 4 秒
            if attempt < max_retries - 1:
                time.sleep(4)
        
        raise Exception(f"任务超时 (尝试 {max_retries} 次，共耗时 {max_retries * 4} 秒)")
    
    def download_image(self, image_url: str) -> Image.Image:
        """
        下载生成的图片
        
        Args:
            image_url: 图片 URL
        
        Returns:
            PIL Image 对象
        
        Raises:
            Exception: 下载失败
        """
        response = requests.get(image_url)
        response.raise_for_status()
        
        image_pil = Image.open(io.BytesIO(response.content))
        return image_pil
    
    def execute(
        self,
        mode: str,
        api_key: str,
        prompt: str,
        model: str,
        resolution: str,
        size: str,
        seed: int,
        image_1: torch.Tensor = None,
        image_2: torch.Tensor = None,
        image_3: torch.Tensor = None,
        image_4: torch.Tensor = None,
        image_5: torch.Tensor = None,
        image_6: torch.Tensor = None,
        image_7: torch.Tensor = None,
        image_8: torch.Tensor = None,
        image_9: torch.Tensor = None,
        image_10: torch.Tensor = None
    ) -> Tuple[torch.Tensor, str, str]:
        """
        主执行函数
        
        Args:
            mode: 生成模式 ('text-to-image' 或 'image-to-image')
            api_key: API 密钥
            prompt: 提示词
            model: 选择的模型
            resolution: 选择的分辨率
            size: 选择的宽高比
            seed: 种子 (用于防止缓存)
            image_1: ComfyUI 输入的图片 Tensor (可选，仅在 image-to-image 模式使用)
            image_2-image_10: 额外的图片输入接口
        
        Returns:
            (生成的图片 Tensor, 结果图片 URL, 任务状态响应 JSON 字符串)
        """
        try:
            print(f"[ToAPIGenNode] 开始处理... (模式: {mode})")
            
            image_url = None
            
            # 图生图模式：上传输入图片
            if mode == "image-to-image":
                if image_1 is None:
                    raise Exception("图生图模式必须提供输入图片")
                
                print("[ToAPIGenNode] 步骤 1: 转换图片格式...")
                image_pil = self.tensor_to_pil(image_1)
                
                print("[ToAPIGenNode] 步骤 2: 上传图片到 ToAPIs...")
                image_url = self.upload_image(image_pil, api_key)
                print(f"[ToAPIGenNode] 图片上传成功，URL: {image_url}")
            
            elif mode == "text-to-image":
                if image_1 is not None:
                    print("[ToAPIGenNode] 警告: 文生图模式下将忽略输入图片")
                print("[ToAPIGenNode] 文生图模式，跳过上传步骤")
            
            else:
                raise Exception(f"未知的生成模式: {mode}")
            
            # 步骤 3: 调用生成接口
            print(f"[ToAPIGenNode] 步骤 {3 if mode == 'image-to-image' else 1}: 调用图生图接口...")
            task_id = self.generate_image(api_key, prompt, model, resolution, size, mode, image_url)
            print(f"[ToAPIGenNode] 任务已创建，ID: {task_id}")
            
            # 步骤 4: 轮询任务状态
            print(f"[ToAPIGenNode] 步骤 {4 if mode == 'image-to-image' else 2}: 轮询任务状态 (每 4 秒查询一次，共60次)...")
            image_url, response = self.poll_task_status(task_id, api_key)
            print(f"[ToAPIGenNode] 任务完成，结果 URL: {image_url}")
            
            # 步骤 5: 下载结果图片
            print(f"[ToAPIGenNode] 步骤 {5 if mode == 'image-to-image' else 3}: 下载结果图片...")
            result_image_pil = self.download_image(image_url)
            
            # 步骤 6: 转换回 Tensor
            print(f"[ToAPIGenNode] 步骤 {6 if mode == 'image-to-image' else 4}: 转换回 ComfyUI 格式...")
            result_tensor = self.pil_to_tensor(result_image_pil)
            
            print("[ToAPIGenNode] 处理完成!")
            return (result_tensor, image_url, response)
        
        except Exception as e:
            print(f"[ToAPIGenNode] 错误: {str(e)}")
            raise Exception(f"ToAPIGenNode 执行失败: {str(e)}")


# 注册节点
NODE_CLASS_MAPPINGS = {
    "ToAPIGenNode": ToAPIGenNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ToAPIGenNode": "ToAPIs Image Generation",
}
