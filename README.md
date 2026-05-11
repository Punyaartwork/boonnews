# บุญนิวส์ (Boonnews)

เว็บ static site แสดงข่าวงานบุญและกิจกรรมของวัด พร้อม workflow เพิ่มข้อมูลจากการ์ดด้วย Claude Code Vision

## TL;DR

```bash
# วางรูปการ์ดไว้ที่ inbox/
cp ~/Downloads/card.jpg inbox/

# ใน Claude Code
/add

# Claude อ่านรูป → ถอด JSON → preview → user ยืนยัน
# → commit + push GitHub → ssh VPS git pull → เว็บอัปเดต
```

## โครงสร้าง

```
boonnews/
├── index.html              # หน้าเว็บ (pure HTML/CSS/JS)
├── events.json             # ฐานข้อมูลกิจกรรม
├── cards/                  # รูปการ์ด (track ใน git)
├── inbox/                  # drop zone (gitignored)
├── scripts/
│   ├── add_card.py         # validate + commit + push
│   └── deploy.py           # ssh + git pull บน VPS
├── .claude/commands/add.md # slash command /add
├── CLAUDE.md               # คู่มือสำหรับ Claude Code
└── README.md
```

## Setup ครั้งแรก

### 1. Git repo

```bash
cd boonnews
git init
git add .
git commit -m "init: boonnews static site"
git branch -M main
git remote add origin git@github.com:USER/boonnews.git
git push -u origin main
```

### 2. ตั้งค่า VPS deploy

สร้าง `.env` ที่ repo root (gitignored):

```env
BOONNEWS_VPS_HOST=your.vps.host
BOONNEWS_VPS_USER=ubuntu
BOONNEWS_VPS_PATH=/var/www/boonnews
BOONNEWS_VPS_PORT=22
BOONNEWS_VPS_URL=https://boonnews.example.com
BOONNEWS_VPS_BRANCH=main
```

ตรวจสอบว่า:
- VPS clone repo มาที่ `BOONNEWS_VPS_PATH` แล้ว
- SSH key ของเครื่องคุณ authorized บน VPS
- VPS user มีสิทธิ์ `git pull` ใน path นั้น
- Web server (Nginx/Caddy) ชี้ไปที่ `BOONNEWS_VPS_PATH`

### 3. Dev / preview เว็บ

```bash
python3 -m http.server 8000
# เปิด http://localhost:8000
```

## การใช้งานปกติ (เพิ่มกิจกรรม)

1. วางรูปการ์ด `.jpg` ลงใน `inbox/`
2. เปิด Claude Code ในโฟลเดอร์นี้
3. พิมพ์ `/add`
4. Claude อ่านรูป → preview JSON
5. ตอบ `yes` เพื่อ commit + push + deploy
6. เสร็จ — รีโหลดเว็บ

## Schema events.json

```json
{
  "id": 1,
  "temple": "วัดพระธรรมกาย",
  "title": "พิธีทอดผ้าป่าวันวิสาขบูชา",
  "date": "2026-05-22",
  "date_display": "วันที่ 22 พฤษภาคม 2569",
  "categories": ["ทำบุญ", "เทศกาล", "งานบุญ"],
  "important": true,
  "contact": "02-395-0098",
  "cards": ["2026-05-22_dhammakaya_01.jpg"],
  "card_count": 1
}
```

`date` เป็น ค.ศ. (YYYY-MM-DD), `date_display` เป็น พ.ศ. แบบอ่านง่าย

Categories whitelist: `งานบุญ`, `ทำบุญ`, `เทศกาล`, `งานอบรม`, `ต่างประเทศ`, `ศูนย์สาขา`

ดู [CLAUDE.md](CLAUDE.md) สำหรับรายละเอียดทั้งหมด

## CLI manual (ถ้าไม่ใช้ /add)

```bash
# Validate JSON อย่างเดียว
python scripts/add_card.py \
  --json '{"temple":"วัดทดสอบ","title":"งานทดสอบ","date":"2026-12-01","categories":["ทำบุญ"]}' \
  --dry-run

# เพิ่มกิจกรรมจริง (จะ commit + push)
python scripts/add_card.py \
  --json '<event JSON>' \
  --image inbox/card.jpg

# Skip git (สำหรับ test)
python scripts/add_card.py --json '<JSON>' --image inbox/card.jpg --no-git

# Deploy เฉยๆ
python scripts/deploy.py

# Deploy แบบทดลอง
python scripts/deploy.py --dry-run
```

## Stack

- Frontend: HTML5 + CSS3 + Vanilla JS (no framework)
- Fonts: Sarabun + Noto Serif Thai (Google Fonts)
- Backend สำหรับ add: Python 3 (std lib เท่านั้น)
- Deploy: ssh + git pull
- Storage: git repo (รูป + JSON ใน repo เดียว)

## License

ส่วนตัว — ปรับใช้ตามสะดวก
