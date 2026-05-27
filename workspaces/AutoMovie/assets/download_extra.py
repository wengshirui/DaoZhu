"""补充下载 demo4《背影》所需的额外素材"""
import time
import httpx
from pathlib import Path

BASE_DIR = Path(__file__).parent
LUCIDE = "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg"
TABLER = "https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{name}.svg"

EXTRA = {
    "characters/people": [
        ("lucide", "user-round-check", "person-helping", "搀扶/帮助"),
        ("tabler", "stretching", "person-climbing", "攀爬/伸展"),
        ("tabler", "friends", "people-together", "两人一起"),
        ("lucide", "users-round", "crowd", "人群"),
    ],
    "props/items": [
        ("lucide", "citrus", "orange", "橘子/柑橘"),
        ("lucide", "apple", "fruit", "水果"),
        ("lucide", "shopping-bag", "bag-luggage", "行李袋"),
        ("lucide", "briefcase", "suitcase", "手提箱"),
        ("tabler", "hat", "hat", "帽子"),
        ("tabler", "jacket", "jacket", "外套"),
        ("tabler", "coat", "coat", "大衣"),
    ],
    "nature/trees": [
        ("tabler", "tree", "tree-bare", "枯树"),
        ("lucide", "shrub", "shrub", "灌木"),
    ],
    "buildings/structures": [
        ("tabler", "barrier-block", "barrier", "栏杆/障碍"),
        ("lucide", "rail-symbol", "rail", "铁轨"),
        ("tabler", "bench", "bench", "长椅"),
        ("lucide", "columns-3", "pillars", "柱子/站台柱"),
    ],
    "effects/emotions": [
        ("lucide", "droplet", "tear", "泪滴"),
        ("tabler", "mood-cry", "crying", "哭泣"),
    ],
    "nature/sky": [
        ("tabler", "mist", "mist", "薄雾"),
        ("lucide", "cloud-hail", "winter-sky", "冬日天空"),
    ],
    "vehicles/transport": [
        ("tabler", "train", "train-side", "火车侧面"),
    ],
}

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}

def download(source, icon, save_path):
    url = LUCIDE.format(name=icon) if source == "lucide" else TABLER.format(name=icon)
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get(url, headers=HEADERS)
            if r.status_code == 200 and "<svg" in r.text[:200]:
                save_path.write_text(r.text, encoding="utf-8")
                return True
    except Exception as e:
        print(f"  ❌ {icon}: {e}")
    return False

def main():
    print("🎨 补充素材下载（背影专用）")
    total = success = 0
    for cat, items in EXTRA.items():
        d = BASE_DIR / cat
        d.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 {cat}/")
        for src, icon, name, desc in items:
            total += 1
            p = d / f"{name}.svg"
            if p.exists():
                print(f"  ⏭️  {name}.svg")
                success += 1
                continue
            if download(src, icon, p):
                print(f"  ✅ {name}.svg — {desc}")
                success += 1
            else:
                print(f"  ⚠️  {name}.svg — 未找到")
            time.sleep(0.3)
    print(f"\n📊 {success}/{total} 下载成功")

if __name__ == "__main__":
    main()
