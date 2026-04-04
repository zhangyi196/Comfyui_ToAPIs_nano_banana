# Comfyui_ToAPIs_nano_banana

一个用于 **ComfyUI** 的自定义节点，可直接调用 **ToAPIs** 图像生成接口。

支持：

- `text-to-image`
- `image-to-image`

ComfyUI 中的节点名称：

- `ToAPIs Image Generation`

## 安装

将仓库放到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/zhangyi196/Comfyui_ToAPIs_nano_banana.git
```

安装依赖：

```bash
pip install requests pillow numpy
```

然后重启 ComfyUI。

## 使用

在 ComfyUI 中添加 `ToAPIs Image Generation` 节点。

### 文生图

- `mode` 选择 `text-to-image`
- 填写 `api_key`
- 输入 `prompt`
- 选择 `model`、`resolution`、`size`

### 图生图

- `mode` 选择 `image-to-image`
- 给 `image_1` 连接输入图片
- 填写 `api_key`
- 输入 `prompt`
- 选择 `model`、`resolution`、`size`

## 输入参数

必填参数：

- `mode`
- `api_key`
- `prompt`
- `model`
- `resolution`
- `size`
- `seed`

可选图片输入：

- `image_1` 到 `image_10`

当前版本实际只使用了 `image_1`。

## 输出

- `image`：生成后的图片
- `image_url`：结果图片 URL
- `response`：接口响应内容

## 当前支持的模型

- `gemini-3-pro-image-preview`
- `gemini-3.1-flash-image-preview`
- `gemini-2.5-flash-image-preview`

## 注意事项

- 需要可用的 ToAPIs API Key
- 需要网络访问 `https://toapis.com`
- `image-to-image` 模式下必须传入 `image_1`
- 默认最长等待时间约为 `240` 秒

## 已知限制

- `seed` 目前没有实际传入 API
- `image_2` 到 `image_10` 暂未启用
- 目前还没有提供工作流示例 JSON

## License

 `MIT` 许可证。
