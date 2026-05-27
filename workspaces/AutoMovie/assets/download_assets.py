"""
AutoMovie 素材批量下载脚本
从 GitHub 开源仓库下载 SVG 素材（Lucide Icons + Tabler Icons）
所有素材均为 MIT/ISC 协议，可商用

用法: python download_assets.py
"""

import time
import httpx
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 素材源：GitHub Raw（无反爬限制）
# Lucide Icons: https://github.com/lucide-icons/lucide (ISC License)
# Tabler Icons: https://github.com/tabler/tabler-icons (MIT License)

LUCIDE_RAW = "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg"
TABLER_RAW = "https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/filled/{name}.svg"
TABLER_OUTLINE = "https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{name}.svg"

# 素材清单：分类 → [(源, icon名, 保存名, 描述)]
ASSETS = {
    "nature/mountains": [
        ("lucide", "mountain", "mountain", "山峰"),
        ("lucide", "mountain-snow", "mountain-snow", "雪山"),
        ("tabler", "mountain", "mountain-filled", "山峰(填充)"),
    ],
    "nature/trees": [
        ("lucide", "tree-pine", "tree-pine", "松树"),
        ("lucide", "tree-deciduous", "tree-deciduous", "落叶树"),
        ("lucide", "trees", "trees", "树林"),
        ("lucide", "flower-2", "flower", "花朵"),
        ("lucide", "leaf", "leaf", "树叶"),
        ("tabler", "plant", "plant", "植物"),
    ],
    "nature/water": [
        ("lucide", "waves", "waves", "波浪"),
        ("lucide", "droplets", "droplets", "水滴"),
        ("tabler", "ripple", "ripple", "涟漪"),
    ],
    "nature/sky": [
        ("lucide", "sun", "sun", "太阳"),
        ("lucide", "moon", "moon", "月亮"),
        ("lucide", "cloud", "cloud", "云朵"),
        ("lucide", "star", "star", "星星"),
        ("lucide", "sunrise", "sunrise", "日出"),
        ("lucide", "sunset", "sunset", "日落"),
        ("lucide", "rainbow", "rainbow", "彩虹"),
    ],
    "animals/common": [
        ("lucide", "cat", "cat", "猫"),
        ("lucide", "dog", "dog", "狗"),
        ("lucide", "bird", "bird", "鸟"),
        ("lucide", "fish", "fish", "鱼"),
        ("lucide", "rabbit", "rabbit", "兔子"),
        ("lucide", "squirrel", "squirrel", "松鼠"),
        ("lucide", "turtle", "turtle", "乌龟"),
        ("lucide", "snail", "snail", "蜗牛"),
    ],
    "animals/wild": [
        ("lucide", "bug", "bug", "虫子"),
        ("tabler", "deer", "deer", "鹿"),
        ("tabler", "horse", "horse", "马"),
        ("tabler", "butterfly", "butterfly", "蝴蝶"),
        ("tabler", "fish", "fish-wild", "鱼(野生)"),
    ],
    "buildings/houses": [
        ("lucide", "house", "house", "房屋"),
        ("lucide", "home", "home", "家"),
        ("lucide", "building", "building", "建筑"),
        ("lucide", "building-2", "building-2", "高楼"),
        ("lucide", "warehouse", "warehouse", "仓库"),
        ("lucide", "church", "church", "教堂"),
        ("lucide", "castle", "castle", "城堡"),
        ("tabler", "home", "home-filled", "家(填充)"),
    ],
    "buildings/structures": [
        ("lucide", "fence", "fence", "栅栏"),
        ("lucide", "landmark", "landmark", "地标"),
        ("lucide", "tower-control", "tower", "塔"),
        ("tabler", "bridge", "bridge", "桥"),
    ],
    "props/furniture": [
        ("lucide", "bed-double", "bed", "床"),
        ("lucide", "bed-single", "bed-single", "单人床"),
        ("lucide", "sofa", "sofa", "沙发"),
        ("lucide", "armchair", "armchair", "扶手椅"),
        ("lucide", "lamp", "lamp", "台灯"),
        ("lucide", "lamp-desk", "lamp-desk", "书桌灯"),
        ("tabler", "armchair", "armchair-filled", "扶手椅(填充)"),
    ],
    "props/doors": [
        ("lucide", "door-open", "door-open", "开门"),
        ("lucide", "door-closed", "door-closed", "关门"),
        ("tabler", "door", "door", "门"),
        ("tabler", "door-enter", "door-enter", "进门"),
        ("tabler", "door-exit", "door-exit", "出门"),
    ],
    "props/items": [
        ("lucide", "book-open", "book-open", "打开的书"),
        ("lucide", "book", "book", "书"),
        ("lucide", "cup-soda", "cup", "杯子"),
        ("lucide", "clock", "clock", "时钟"),
        ("lucide", "key", "key", "钥匙"),
        ("lucide", "phone", "phone", "手机"),
        ("lucide", "tv", "tv", "电视"),
        ("lucide", "laptop", "laptop", "笔记本"),
        ("lucide", "utensils", "utensils", "餐具"),
        ("lucide", "cooking-pot", "cooking-pot", "锅"),
        ("lucide", "scissors", "scissors", "剪刀"),
        ("lucide", "umbrella", "umbrella", "雨伞"),
    ],
    "characters/people": [
        ("lucide", "user", "person", "人物"),
        ("lucide", "user-round", "person-round", "人物(圆形)"),
        ("lucide", "users", "people", "多人"),
        ("lucide", "baby", "baby", "婴儿"),
        ("lucide", "person-standing", "person-standing", "站立"),
        ("tabler", "walk", "person-walking", "走路"),
        ("tabler", "run", "person-running", "跑步"),
        ("tabler", "sit", "person-sitting", "坐着"),
        ("tabler", "man", "man", "男人"),
        ("tabler", "woman", "woman", "女人"),
    ],
    "characters/expressions": [
        ("lucide", "smile", "smile", "微笑"),
        ("lucide", "frown", "frown", "皱眉"),
        ("lucide", "laugh", "laugh", "大笑"),
        ("lucide", "angry", "angry", "生气"),
        ("lucide", "meh", "meh", "无聊"),
        ("tabler", "mood-happy", "mood-happy", "开心"),
        ("tabler", "mood-sad", "mood-sad", "悲伤"),
    ],
    "effects/weather": [
        ("lucide", "cloud-rain", "rain", "下雨"),
        ("lucide", "cloud-snow", "snow", "下雪"),
        ("lucide", "cloud-lightning", "lightning", "闪电"),
        ("lucide", "wind", "wind", "风"),
        ("lucide", "cloud-fog", "fog", "雾"),
        ("lucide", "thermometer-sun", "hot", "炎热"),
        ("lucide", "snowflake", "snowflake", "雪花"),
    ],
    "effects/emotions": [
        ("lucide", "heart", "heart", "爱心"),
        ("lucide", "sparkles", "sparkles", "闪光"),
        ("lucide", "zap", "zap", "闪电"),
        ("lucide", "flame", "flame", "火焰"),
        ("lucide", "music", "music", "音乐"),
        ("lucide", "speech", "speech", "对话"),
        ("tabler", "bulb", "idea", "灵感"),
    ],
    "effects/actions": [
        ("lucide", "hand", "hand", "手"),
        ("lucide", "hand-helping", "hand-helping", "帮助"),
        ("lucide", "footprints", "footprints", "脚印"),
        ("lucide", "move", "move", "移动"),
        ("lucide", "rotate-cw", "rotate", "旋转"),
        ("tabler", "arrows-move", "arrows-move", "移动箭头"),
    ],
    "vehicles/transport": [
        ("lucide", "car", "car", "汽车"),
        ("lucide", "bike", "bike", "自行车"),
        ("lucide", "bus", "bus", "公交车"),
        ("lucide", "train-front", "train", "火车"),
        ("lucide", "ship", "ship", "船"),
        ("lucide", "plane", "plane", "飞机"),
        ("tabler", "boat", "boat", "小船"),
    ],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
}


def download_svg(source: str, icon_name: str, save_path: Path) -> bool:
    """下载单个 SVG 文件"""
    if source == "lucide":
        url = LUCIDE_RAW.format(name=icon_name)
    elif source == "tabler":
        url = TABLER_OUTLINE.format(name=icon_name)
    else:
        return False

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=HEADERS)
            if resp.status_code == 200 and "<svg" in resp.text[:200]:
                save_path.write_text(resp.text, encoding="utf-8")
                return True
            # Tabler fallback: try filled version
            if source == "tabler":
                url2 = TABLER_RAW.format(name=icon_name)
                resp2 = client.get(url2, headers=HEADERS)
                if resp2.status_code == 200 and "<svg" in resp2.text[:200]:
                    save_path.write_text(resp2.text, encoding="utf-8")
                    return True
    except Exception as e:
        print(f"  ❌ 下载失败 {icon_name}: {e}")
    return False


def main():
    print("🎨 AutoMovie 素材下载器 (GitHub Raw)")
    print("  源: Lucide Icons (ISC) + Tabler Icons (MIT)")
    print("=" * 50)

    total = 0
    success = 0

    for category, items in ASSETS.items():
        category_dir = BASE_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 {category}/")

        for source, icon_name, save_name, desc in items:
            total += 1
            save_path = category_dir / f"{save_name}.svg"

            if save_path.exists():
                print(f"  ⏭️  {save_name}.svg (已存在)")
                success += 1
                continue

            if download_svg(source, icon_name, save_path):
                print(f"  ✅ {save_name}.svg — {desc}")
                success += 1
            else:
                print(f"  ⚠️  {save_name}.svg — 未找到")

            time.sleep(0.3)

    print(f"\n{'=' * 50}")
    print(f"📊 完成: {success}/{total} 个素材下载成功")
    print(f"📁 保存位置: {BASE_DIR}")


if __name__ == "__main__":
    main()
