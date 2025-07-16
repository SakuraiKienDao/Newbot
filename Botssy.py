import requests
from dataclasses import dataclass
import html
import os
import time

# === Config ===
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1394928726432808970/3YCdWbpRK0Zx4-FOIsw6y3H-33oCDLoNnh6mUkW2t9tv6IPjPd9RziTVT_66rW4rGoYD"
CACHE_FILE = "room_cache2.txt"
API_URL = "https://chintai.r6.ur-net.go.jp/chintai/api/bukken/detail/detail_bukken_room/"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.ur-net.go.jp/chintai/kansai/osaka/80_1910.html",
}
PAYLOAD = {
    "rent_low": "",
    "rent_high": "",
    "floorspace_low": "",
    "floorspace_high": "",
    "shisya": "80",  # 関西支社
    "danchi": "223",
    "shikibetu": "0",  # 全部屋種
    "newBukkenRoom": "",
    "orderByField": "0",
    "orderBySort": "0",
    "pageIndex": "0",
    "sp": "",
}

RUN_COUNTER_FILE = "run_count.txt"
CLEAR_EVERY = 8


# === Room Data ===
@dataclass
class Room:
    id: str
    name: str
    rent: str
    fee: str
    layout: str
    size: str
    floor: str
    url: str


# === Fetch Room List ===
def fetch_room_list() -> list[Room]:
    try:
        res = requests.post(API_URL, headers=HEADERS, data=PAYLOAD, timeout=10)
        res.raise_for_status()
        room_data = res.json()
    except Exception:
        return []

    room_list = []
    if not room_data:
        return room_list
    # print (f"rommdata: {room_data}")
    for r in room_data:
        room = Room(id=r.get("id", ""),
                    name=r.get("name", ""),
                    rent=r.get("rent", ""),
                    fee=r.get("commonfee", ""),
                    layout=r.get("type", ""),
                    size=html.unescape(r.get("floorspace",
                                             "")).replace("&#13217;", "㎡"),
                    floor=r.get("floor", ""),
                    url=f"https://www.ur-net.go.jp{r.get('roomDetailLink')}"
                    if r.get("roomDetailLink") else "N/A")
        room_list.append(room)
    return room_list


# === Cache Handling ===
def load_cached_urls() -> set[str]:
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)


def save_cached_urls(urls: set[str]):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")


# === Discord Notification ===
def send_discord_notification(room: Room):
    message = (f"🏠 **{room.name}**\n"
               f"💴 家賃: {room.rent}（共益費: {room.fee}）\n"
               f"📐 間取り: {room.layout} | 面積: {room.size} | 階: {room.floor}\n"
               f"🔗 {room.url}\n"
               f"`ID: {room.id}`")
    try:
        res = requests.post(DISCORD_WEBHOOK_URL,
                            json={"content": message},
                            timeout=5)
        if res.status_code != 204:
            with open("error_log.txt", "a", encoding="utf-8") as f:
                f.write(f"❌ Failed to send: {res.status_code} {res.text}\n")
    except Exception as e:
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"❌ Exception: {e}\n")


def clear_cache_every_n_runs():
    count = 0
    if os.path.exists(RUN_COUNTER_FILE):
        with open(RUN_COUNTER_FILE, "r") as f:
            try:
                count = int(f.read().strip())
            except ValueError:
                count = 0

    count += 1

    if count >= CLEAR_EVERY:

        # Clear cache
        open(CACHE_FILE, "w").close()
        count = 0  # Reset counter

    with open(RUN_COUNTER_FILE, "w") as f:
        f.write(str(count))


# === Main ===
def main():
    clear_cache_every_n_runs()
    rooms = fetch_room_list()
    if not rooms:
        return

    cached_urls = load_cached_urls()
    new_rooms = [room for room in rooms if room.url not in cached_urls]

    if not new_rooms:
        return

    for room in new_rooms:
        send_discord_notification(room)
        time.sleep(1)
    updated_cache = cached_urls.union(room.url for room in new_rooms)
    save_cached_urls(updated_cache)


if __name__ == "__main__":
    main()
