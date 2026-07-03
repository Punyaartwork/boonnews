#!/usr/bin/env python3
"""สร้าง calendar.json — ฤดูกาลงานบุญจากพาดหัวข่าวจริง 4 ปี (2565–2568)

สแกนบทรายการหลัก BOON NEWS วันละ 1 ไฟล์ จาก:
  ~/Documents/boonnews_work/รวมบทความ/บทข่าวปี 25XX/<เดือน>/<DDMMYY>/*.docx
สกัดพาดหัว (ข้อความในวงเล็บ) → จับคู่คีย์เวิร์ดของแต่ละงานบุญ → นับ ปี × เดือน

วิธีเลือกไฟล์บทหลักต่อวัน (ตาม methodology ของรายงานวิเคราะห์):
  ไฟล์ .docx ที่ชื่อมี "BOON NEWS" (เลือกเวอร์ชัน แก้ไข > ปกติ > เหลือง)
  ไม่นับไฟล์เบรกสั้นและไฟล์ temp (~$)

ใช้: python3 scripts/build_calendar_json.py [--out calendar.json]
"""
import argparse
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

SRC = Path.home() / 'Documents' / 'boonnews_work' / 'รวมบทความ'
YEARS = ['2565', '2566', '2567', '2568']

# กลุ่มงานบุญ × คีย์เวิร์ดในพาดหัว (เรียงตามลำดับที่อยากให้แสดงบนหน้า)
EVENTS = [
    ('ธรรมยาตรา', ['ธรรมยาตรา']),
    ('มาฆบูชา', ['มาฆบูชา']),
    ('บวช / บรรพชา / สามเณร', ['บวช', 'บรรพชา', 'อุปสมบท', 'สามเณร']),
    ('สงกรานต์', ['สงกรานต์']),
    ('วันคุ้มครองโลก', ['คุ้มครองโลก']),
    ('วิสาขบูชา', ['วิสาขบูชา']),
    ('อาสาฬหฯ / เข้าพรรษา', ['อาสาฬห', 'เข้าพรรษา']),
    ('วันสมาธิโลก / วันธรรมชัย', ['สมาธิโลก', 'วันธรรมชัย']),
    ('ออกพรรษา / ตักบาตรเทโว', ['ออกพรรษา', 'เทโว']),
    ('กฐิน / ผ้าป่า', ['กฐิน', 'ผ้าป่า']),
    ('สวดมนต์ข้ามปี', ['ข้ามปี']),
    ('ตักบาตร', ['ตักบาตร']),
    ('บูชาข้าวพระ', ['บูชาข้าวพระ']),
    ('สวดธัมมจักกัปปวัตตนสูตร', ['ธัมมจัก']),
    ('มุทิตา / วาระบูรพาจารย์', ['มุทิตา', 'ปูชนียาจารย์', 'คุณยายอาจารย์', 'พระมงคลเทพมุนี', 'ทัตตชีโว', 'ธัมมชโย']),
    ('ภัยพิบัติ / ช่วยเหลือ', ['น้ำท่วม', 'อุทกภัย', 'ถุงยังชีพ', 'แผ่นดินไหว', 'ผู้ประสบภัย']),
]

THAI_RE = re.compile(r'[฀-๿]')
HEAD_RE = re.compile(r'[(（]([^)）]{15,220})[)）]')
PARA_RE = re.compile(r'<w:p[ >].*?</w:p>', re.S)
TEXT_RE = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')


def docx_text(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    except Exception:
        return ''
    return '\n'.join(''.join(TEXT_RE.findall(p)) for p in PARA_RE.findall(xml))


def pick_main(day_dir):
    """เลือกไฟล์บทหลักของวัน: BOON NEWS (แก้ไข > ปกติ > เหลือง) > ไฟล์ข่าวอื่น"""
    cands = [f for f in day_dir.glob('*.docx')
             if not f.name.startswith('~$') and 'เบรก' not in f.name]
    if not cands:
        return None
    boon = [f for f in cands if re.search(r'boon\s*news', f.name, re.I)]
    pool = boon or cands

    def rank(f):
        n = f.name
        if 'แก้ไข' in n:
            return 0
        if 'เหลือง' in n:
            return 2
        return 1

    pool.sort(key=lambda f: (rank(f), -f.stat().st_size))
    return pool[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent / 'calendar.json')
    args = ap.parse_args()

    if not SRC.exists():
        sys.exit(f'ไม่พบ {SRC}')

    # counts[event][year_idx][month_idx], samples[event][month_idx]
    counts = {name: [[0] * 12 for _ in range(4)] for name, _ in EVENTS}
    samples = {name: [''] * 12 for name, _ in EVENTS}
    days_scanned = [0] * 4
    total_heads = 0

    for yi, year in enumerate(YEARS):
        root = SRC / f'บทข่าวปี {year}'
        if not root.exists():
            continue
        for day_dir in sorted(root.glob('*/[0-9][0-9][0-9][0-9][0-9][0-9]')):
            dmy = day_dir.name
            mo = int(dmy[2:4])
            yy = dmy[4:6]
            if yy != year[-2:] or not 1 <= mo <= 12:
                continue
            f = pick_main(day_dir)
            if not f:
                continue
            text = docx_text(f)
            if not text:
                continue
            days_scanned[yi] += 1
            heads = [h.strip() for h in HEAD_RE.findall(text) if THAI_RE.search(h)]
            total_heads += len(heads)
            for h in heads:
                for name, kws in EVENTS:
                    if any(k in h for k in kws):
                        counts[name][yi][mo - 1] += 1
                        if not samples[name][mo - 1]:
                            samples[name][mo - 1] = h[:120]

    events_out = []
    for name, kws in EVENTS:
        by_year = counts[name]
        by_month = [sum(by_year[y][m] for y in range(4)) for m in range(12)]
        total = sum(by_month)
        if total == 0:
            continue
        # เดือนพีค + ความสม่ำเสมอ: งานโผล่เดือนพีคเดียวกันกี่ปีจาก 4 ปี
        peak_m = max(range(12), key=lambda m: by_month[m])
        years_hit = sum(1 for y in range(4) if by_year[y][peak_m] > 0)
        events_out.append({
            'name': name,
            'byMonth': by_month,
            'byYear': by_year,
            'total': total,
            'peakMonth': peak_m,
            'peakYearsHit': years_hit,
            'samples': samples[name],
        })

    data = {
        'generated': date.today().isoformat(),
        'years': YEARS,
        'daysScanned': days_scanned,
        'totalHeadlines': total_heads,
        'events': events_out,
    }
    args.out.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    print(f'เขียน {args.out}')
    print(f'สแกน {sum(days_scanned)} วัน ({" / ".join(str(d) for d in days_scanned)}) · พาดหัว {total_heads:,} ชิ้น')
    mo_names = ['ม.ค', 'ก.พ', 'มี.ค', 'เม.ย', 'พ.ค', 'มิ.ย', 'ก.ค', 'ส.ค', 'ก.ย', 'ต.ค', 'พ.ย', 'ธ.ค']
    for e in events_out:
        bar = ' '.join(f'{v:4d}' for v in e['byMonth'])
        print(f"  {e['name'][:26]:28s} รวม {e['total']:5d} | พีค {mo_names[e['peakMonth']]} ({e['peakYearsHit']}/4 ปี) | {bar}")


if __name__ == '__main__':
    main()
