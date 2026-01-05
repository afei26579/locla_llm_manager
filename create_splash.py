"""
创建启动画面

这个脚本会生成一个简单的启动画面图片
你也可以使用自己设计的图片替换
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_splash_screen(width=600, height=400, output_path='splash.png'):
    """创建启动画面
    
    Args:
        width: 宽度
        height: 高度
        output_path: 输出路径
    """
    # 创建渐变背景
    img = Image.new('RGB', (width, height), color='#1e1e1e')
    draw = ImageDraw.Draw(img)
    
    # 绘制渐变背景
    for i in range(height):
        # 从深色到浅色的渐变
        r = int(30 + (i / height) * 20)
        g = int(30 + (i / height) * 20)
        b = int(30 + (i / height) * 20)
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    
    # 绘制装饰圆圈
    circle_color = (0, 122, 255, 100)  # 半透明蓝色
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # 大圆圈
    overlay_draw.ellipse([width//2-150, height//2-150, width//2+150, height//2+150], 
                         fill=None, outline=(0, 122, 255, 50), width=2)
    overlay_draw.ellipse([width//2-100, height//2-100, width//2+100, height//2+100], 
                         fill=None, outline=(0, 122, 255, 80), width=3)
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # 绘制文字
    try:
        # 尝试使用系统字体
        title_font = ImageFont.truetype("msyh.ttc", 48)  # 微软雅黑
        subtitle_font = ImageFont.truetype("msyh.ttc", 24)
        info_font = ImageFont.truetype("msyh.ttc", 16)
    except:
        # 如果找不到字体，使用默认字体
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
    
    # 标题
    title = "本地大模型助手"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = height // 2 - 60
    
    # 绘制标题阴影
    draw.text((title_x + 2, title_y + 2), title, fill='#000000', font=title_font)
    # 绘制标题
    draw.text((title_x, title_y), title, fill='#007AFF', font=title_font)
    
    # 副标题
    subtitle = "Local LLM Assistant"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    subtitle_y = title_y + 70
    draw.text((subtitle_x, subtitle_y), subtitle, fill='#8e8e93', font=subtitle_font)
    
    # 版本信息
    version = "v1.0.0"
    version_bbox = draw.textbbox((0, 0), version, font=info_font)
    version_width = version_bbox[2] - version_bbox[0]
    version_x = (width - version_width) // 2
    version_y = height - 50
    draw.text((version_x, version_y), version, fill='#6e6e73', font=info_font)
    
    # 保存图片
    img.save(output_path, 'PNG')
    print(f"✅ 启动画面已创建: {output_path}")
    print(f"   尺寸: {width}x{height}")
    
    return output_path


def create_icon(size=256, output_path='icon.png'):
    """创建应用图标
    
    Args:
        size: 图标尺寸
        output_path: 输出路径
    """
    # 创建图标
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制圆形背景
    margin = size // 8
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill='#007AFF', outline=None)
    
    # 绘制内圆
    inner_margin = size // 4
    draw.ellipse([inner_margin, inner_margin, size-inner_margin, size-inner_margin], 
                 fill=None, outline='white', width=size//20)
    
    # 绘制字母 "AI"
    try:
        font = ImageFont.truetype("msyh.ttc", size//3)
    except:
        font = ImageFont.load_default()
    
    text = "AI"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - size // 20
    
    draw.text((text_x, text_y), text, fill='white', font=font)
    
    # 保存 PNG
    img.save(output_path, 'PNG')
    print(f"✅ 图标已创建: {output_path}")
    
    # 转换为 ICO（需要 pillow）
    try:
        ico_path = output_path.replace('.png', '.ico')
        img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print(f"✅ ICO 图标已创建: {ico_path}")
        return ico_path
    except Exception as e:
        print(f"⚠️ ICO 转换失败: {e}")
        print("   请手动使用在线工具转换 PNG 为 ICO")
        return output_path


if __name__ == '__main__':
    print("=" * 60)
    print("创建启动资源")
    print("=" * 60)
    
    # 创建启动画面
    splash_path = create_splash_screen()
    
    # 创建图标
    icon_path = create_icon()
    
    print("\n" + "=" * 60)
    print("资源创建完成！")
    print("=" * 60)
    print("\n提示：")
    print("1. 你可以使用自己设计的图片替换这些文件")
    print("2. 启动画面建议尺寸: 600x400 或 800x600")
    print("3. 图标建议尺寸: 256x256 或更大")
    print("4. 如果 ICO 转换失败，可以使用在线工具：")
    print("   https://convertio.co/zh/png-ico/")
