# Boonnews (บุญนิวส์) — คู่มือสำหรับ Claude Code

เว็บ static site แสดงข่าวงานบุญและกิจกรรมของวัด พร้อม workflow เพิ่มข้อมูลจากการ์ดด้วย Vision

## โครงสร้างโปรเจกต์

```
boonnews/
├── index.html              # หน้าเว็บหลัก (pure HTML/CSS/JS)
├── events.json             # ฐานข้อมูลกิจกรรมทั้งหมด
├── cards/                  # รูปการ์ดทั้งหมด (track ใน git)
├── inbox/                  # drop zone การ์ดใหม่ (gitignored)
├── scripts/
│   ├── add_card.py         # validate + commit + push
│   └── deploy.py           # ssh + git pull บน VPS
├── .claude/commands/add.md # slash command /add
├── .gitignore
└── README.md
```

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
