# Boonnews (บุญนิวส์) — คู่มือสำหรับ Claude Code

เว็บ static site แสดงข่าวงานบุญและกิจกรรมของวัด พร้อม workflow เพิ่มข้อมูลจากการ์ดด้วย Vision

## โครงสร้างโปรเจกต์

```
boonnews/
├── index.html              # หน้าแรก: กริดความเคลื่อนไหวทุกวัด (จาก centers.json)
├── map.html                # แผนที่เครือข่ายวัด ไทย/รอบโลก (จาก centers.json)
├── analysis.html           # หน้าวิเคราะห์คลังข่าว 4 ปี (จาก analysis.json + calendar.json)
├── centers.json            # ฐานข้อมูลศูนย์ 253 แห่ง (generate — ห้ามแก้มือ)
├── analysis.json           # สถิติข่าว 4 ปี: 251 แหล่ง, รายเดือน, quadrant (generate — ห้ามแก้มือ)
├── calendar.json           # ฤดูกาลงานบุญ 16 งาน × 12 เดือน จากพาดหัวจริง (generate — ห้ามแก้มือ)
├── events.html             # หน้าข่าวงานบุญ/กิจกรรมวัด (เดิมคือ index.html — workflow /add ชี้หน้านี้)
├── events.json             # ฐานข้อมูลกิจกรรมทั้งหมด (ของ events.html)
├── cards/                  # รูปการ์ดทั้งหมด (track ใน git)
├── inbox/                  # drop zone การ์ดใหม่ (gitignored)
├── scripts/
│   ├── add_card.py         # validate + commit + push
│   ├── deploy.py           # ssh + git pull บน VPS
│   ├── build_centers_json.py   # สร้าง centers.json
│   ├── build_analysis_json.py  # สร้าง analysis.json (ต้องมี openpyxl)
│   └── build_calendar_json.py  # สร้าง calendar.json (สแกน docx ~1,100 วัน ใช้เวลาราว 1 นาที)
├── .claude/commands/add.md # slash command /add
├── .claude/launch.json     # config เปิด dev server (python3 -m http.server 8641) สำหรับ preview
├── .gitignore
└── README.md
```

หมายเหตุ: "หน้าเว็บหลัก" ของ workflow /add และ Frontend Logic ด้านล่าง หมายถึง `events.html`

## หน้า BOON NEWS (แผนที่/กริด/วิเคราะห์) + Data Pipeline

ทุกหน้ามีเมนู 4 แท็บบน header เชื่อมกัน: ▦ แผนที่ / ▤ กริด / ▣ ข่าวงานบุญ / ▨ วิเคราะห์
ดีไซน์มาจาก Claude Design (BoonnewsWorld handoff) — ธีม IBM Plex Sans Thai + Space Mono, navy `#15276B`, ส้ม `#F5821F`

### แหล่งข้อมูลจริงอยู่นอก repo ที่ `~/Documents/boonnews_work/`

| ไฟล์ generate | สคริปต์ | แหล่งข้อมูล |
|---|---|---|
| `centers.json` | `build_centers_json.py` | `data/all_centers_profiles_v2.csv` (253 ศูนย์ + FB) + `data/boonnews_catalog_newest4000.csv` (จับคู่คลิป — logic เดียวกับ video_matches) + ชื่ออังกฤษจาก `data/intl_centers.py` |
| `analysis.json` | `build_analysis_json.py` | `รวมบทความ/สรุปข่าวรายวัด_2565-2568.xlsx` (251 แหล่ง, รายเดือน Top60) + profiles_v2 (quadrant A70/B16/C116/D51) |
| `calendar.json` | `build_calendar_json.py` | `รวมบทความ/บทข่าวปี 25XX/<เดือน>/<DDMMYY>/*.docx` — สแกนบทหลัก BOON NEWS วันละไฟล์ (แก้ไข > ปกติ > เหลือง, ข้ามไฟล์เบรก/temp) สกัดพาดหัวในวงเล็บ |

### เมื่อข้อมูลใน boonnews_work อัปเดต

```bash
python3 scripts/build_centers_json.py     # และ/หรือ build_analysis_json.py, build_calendar_json.py
git add -A && git commit && git push      # commit เฉพาะเมื่อ user สั่ง
python3 scripts/deploy.py                 # deploy เฉพาะเมื่อ user สั่ง
```

### กฎเฉพาะส่วนนี้

- **ห้ามแก้ `centers.json` / `analysis.json` / `calendar.json` ด้วยมือ** — แก้ที่สคริปต์หรือแหล่งข้อมูลแล้ว generate ใหม่
- แผนที่ใช้ d3 + topojson จาก CDN (แค่ projection ไม่มี build step) · โหลด world-atlas 110m + provinces.geojson จาก CDN
- จังหวัดจับคู่ด้วยชื่อไทย `pro_th` ตรงตัว (77 จังหวัดตรงกับทะเบียน 100%)
- ประเทศที่ไม่มี outline ใน atlas 110m (สิงคโปร์/มอลตา/บาห์เรน) ปักหมุดจากพิกัด lonlat ใน `COUNTRY_INFO` และคลิกแล้วเปิด panel แทนการซูม
- ตำแหน่งหมุดศูนย์ตอนซูมเข้าประเทศเป็นตำแหน่งจำลองในเขตแดน (ยังไม่มี lat/lng รายศูนย์ — รอ Phase 2 Geocode)
- "เรื่องเล่า" ในหน้า temple ยังเป็น placeholder (ยังไม่มีข้อมูล Story)
- ข้อมูลที่รู้ว่าไม่ครบ: บทข่าว ธ.ค.66 และ เม.ย.–พ.ค.68 ไม่มีในเซิร์ฟเวอร์ (แสดงเป็นแถบลายในกราฟ) · ตัวเลขปี 2568 ช่วงปลายปียังไม่ครบ

## Schema ของ events.json

แต่ละ event เป็น object รูปแบบนี้:

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

### กฎสำคัญของ schema

- `id` — integer, unique, auto-increment จาก `max(existing_ids) + 1`
- `temple` — ชื่อวัดภาษาไทยเต็ม **หรือชื่อสถานที่จัดงาน** ถ้าเป็นงานนอกวัด (ตักบาตรกลางอำเภอ, ฉลองเมือง, จุดประทีปลานสาธารณะ ฯลฯ) → ใช้รูปแบบ `"ณ <สถานที่> อำเภอ<X> จังหวัด<Y>"` เช่น `"ณ ลานศิลปวัฒนธรรม อำเภอเมือง จังหวัดปัตตานี"` หรือ `"ณ ตลาดฟ้าเชียงดาว อำเภอเชียงดาว"` (ดูหัวข้อ "Heuristics เลือก temple" ด้านล่าง)
- `title` — ชื่องาน/กิจกรรม
- `date` — `YYYY-MM-DD` (ค.ศ.) เท่านั้น ห้ามใส่ พ.ศ. ใน field นี้
- `date_display` — string ภาษาไทย แสดงเป็น พ.ศ. (เช่น "วันที่ 22 พฤษภาคม 2569")
- `categories` — array อย่างน้อย 1 ตัว ทุกค่าอยู่ใน whitelist
- `categories[0]` = primary tag (แสดงเด่นบน card)
- `important` — boolean, `true` ถ้าเป็นวันสำคัญทางพระพุทธศาสนา
- `contact` — string เบอร์โทร/ช่องทางติดต่อ (ว่างได้ถ้าไม่มีในการ์ด)
- `cards` — array ชื่อไฟล์รูปการ์ด (เก็บใน `cards/`)
- `card_count` — integer = `cards.length` (เก็บไว้เพื่อ frontend ไม่ต้องคำนวณ)

### Whitelist ของ categories

ต้องเป็นค่าใน list นี้เท่านั้น (case-sensitive):

```
["งานบุญ", "ทำบุญ", "เทศกาล", "งานอบรม", "ต่างประเทศ", "ศูนย์สาขา"]
```

ถ้า extract แล้วได้คำที่ไม่ตรง → map ให้ตรงก่อน (เช่น "บวช" → "งานบุญ", "ฝึกอบรม" → "งานอบรม")

### Heuristics เลือก temple

ลำดับความสำคัญ:

1. ถ้าการ์ดระบุชื่อวัดที่เป็น "เจ้าภาพจัดงาน" ชัดเจน → ใช้ชื่อวัดเต็ม
2. ถ้าเป็นงานนอกวัด (mass ตักบาตร, ฉลองเมือง/อำเภอ, จุดประทีป, ลอยกระทงสาธารณะ) → ใช้สถานที่จัดงานจริงที่ระบุบนการ์ด พร้อมคำว่า "ณ" นำหน้า
3. ระบุให้แคบที่สุดที่การ์ดให้มา (ถนน/ลาน/ตลาด/เจดีย์ > อำเภอ > จังหวัด) ห้ามถอยไปแค่จังหวัดถ้าการ์ดมี venue ชัดเจน
4. ระวัง OCR ผิดในชื่อสถานที่ไทย (เพียง vs เชียง, ช่วง vs ถนน) — ถ้าไม่แน่ใจถาม user ก่อน

ตัวอย่างที่ผ่าน user confirm แล้ว:
- `"ณ ลานศิลปวัฒนธรรม อำเภอเมือง จังหวัดปัตตานี"` (ตักบาตรพระ 1,000 รูป)
- `"ณ ตลาดฟ้าเชียงดาว อำเภอเชียงดาว"` (ตักบาตรพระ 1,118 รูป ฉลองเมือง 117 ปี)

### Heuristics เลือก categories

เลือกได้หลายตัว (multi-tag) ตาม signal ที่พบในการ์ด:

| คำที่เจอ | แนะนำใส่ tag |
|---|---|
| ทอดผ้าป่า, ทอดกฐิน, บวช, ถวายสังฆทาน | `ทำบุญ`, `งานบุญ` |
| วิสาขบูชา, มาฆบูชา, อาสาฬหบูชา, เข้าพรรษา, ออกพรรษา, ลอยกระทง, สงกรานต์ | `เทศกาล` + tag อื่นที่เกี่ยวข้อง |
| อบรม, ปฏิบัติธรรม, ค่าย, ฝึก | `งานอบรม` |
| ต่างประเทศ, ชื่อประเทศที่ไม่ใช่ไทย, English name | `ต่างประเทศ` |
| ศูนย์สาขา, สำนักสาขา, สาขา | `ศูนย์สาขา` |

primary tag (categories[0]) เลือกอันที่ "เด่นที่สุด" — ถ้าเป็นงานทำบุญในเทศกาล ให้ `ทำบุญ` มาก่อน `เทศกาล`

### Heuristics เลือก important

`important = true` เมื่อพบคำเหล่านี้ในการ์ด:
- วิสาขบูชา
- มาฆบูชา
- อาสาฬหบูชา
- เข้าพรรษา / วันเข้าพรรษา
- ออกพรรษา / วันออกพรรษา
- กฐิน / ทอดกฐิน
- วันพระใหญ่

นอกจากนี้ default `false`

## Workflow การเพิ่มข้อมูลใหม่ (/add)

User วางรูป `.jpg` ใน `inbox/` แล้วพิมพ์ `/add`

Claude ทำตามลำดับนี้:

1. **Vision** — อ่านรูปการ์ดจาก `inbox/`
2. **Extract** — ถอด: `temple`, `title`, `date`, `contact`
3. **Classify** — เลือก `categories` (multi) + `important` (bool) ตาม heuristics
4. **Preview** — แสดง JSON พร้อมเหตุผลเลือก tag/important
5. **Confirm** — หยุดถาม `yes / edit / cancel`
6. **Execute** —
   - `yes` → รัน `python scripts/add_card.py --json '<json>' --image inbox/xxx.jpg`
   - `edit` → ถาม field ไหน → กลับ step 4
   - `cancel` → ลบ preview ทิ้ง ไม่ทำอะไรกับ inbox
7. **Deploy** — หลัง add_card.py สำเร็จ → รัน `python scripts/deploy.py`

## กฎห้ามทำ (Do NOT)

1. **ห้าม commit ก่อนได้คำว่า "yes" จาก user เด็ดขาด** — แม้จะมั่นใจแค่ไหน
2. **ห้ามแก้ `events.json` ด้วยมือเพื่อ "เพิ่ม" event** — ใช้ `scripts/add_card.py` เท่านั้น (validation + auto id + git ops) การลบ event ที่ผ่านไปแล้วทำมือได้ ดูข้อ 7
3. **ห้ามใส่ category ที่ไม่อยู่ใน whitelist** — จะ fail validation
4. **ห้ามใส่ พ.ศ. ใน field `date`** — เป็น ค.ศ. (YYYY-MM-DD) เสมอ
5. **ห้ามใช้ framework / build tool** — pure HTML/CSS/JS เท่านั้น
6. **ห้ามแก้รูปใน `cards/` ตรงๆ** — รูปต้อง rename ผ่าน script เท่านั้น
7. **ลบ event ที่ผ่านไปแล้วได้** — ถ้า `event.date < today` (วันที่ปัจจุบัน YYYY-MM-DD) สามารถลบ entry ใน `events.json` + ไฟล์รูปใน `cards/` ออกได้เลย แล้ว commit + push + deploy ตามปกติ — frontend กรอง `date >= today` อยู่แล้วจึงลบหรือเก็บก็ได้ แต่การลบช่วยให้ repo เบาและไม่ต้อง download ข้อมูลที่ไม่ใช้ ห้ามลบ event ที่ยังไม่ถึง (อนาคต)
8. **ห้าม push --force** — append-only model

## Conventions

- ชื่อไฟล์การ์ด: `{YYYY-MM-DD}_{slug}_{seq:02d}.jpg` เช่น `2026-05-22_dhammakaya_01.jpg`
- `slug` = romanized temple name หรือ hash 6 หลัก (ดู `scripts/add_card.py`)
- Commit message: `add: {temple} - {title} ({date})`
- ทุก UI text เป็นภาษาไทย
- ปี: `date` field = ค.ศ., `date_display` = พ.ศ.

## Frontend Logic สำคัญ

- กรองเฉพาะ `event.date >= today` (วันที่ปัจจุบัน YYYY-MM-DD)
- Filter หมวด: `event.categories.includes(activeCat)` (เพราะ categories เป็น array)
- Filter เวลา: single-select (อาทิตย์นี้ / เดือนนี้ / สำคัญ / ใกล้ที่สุด / ไกลที่สุด)
- Card แสดง `categories[0]` เป็น primary tag + `+N` ถ้ามี categories อื่น
- คลิก `+N` → tooltip แสดง categories ที่เหลือ
- ปุ่มดาวน์โหลด: anchor `<a download href="cards/xxx.jpg">` — ถ้ามีหลายรูป แสดง count
