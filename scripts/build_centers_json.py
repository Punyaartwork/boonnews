#!/usr/bin/env python3
"""สร้าง centers.json สำหรับหน้า map.html / grid.html จากข้อมูลจริงใน boonnews_work

แหล่งข้อมูล (default: ~/Documents/boonnews_work/data):
  - all_centers_profiles_v2.csv   ทะเบียนศูนย์ 253 แห่ง + Facebook + active level + สถิติข่าว 4 ปี
  - boonnews_catalog_newest4000.csv  แคตตาล็อกคลิป 4,000 คลิปล่าสุด (จัดหมวดแล้ว)
  - intl_centers.py               ชื่ออังกฤษของศูนย์ต่างประเทศ (ใช้จับคู่คลิป + แสดงบนแผนที่)

การจับคู่คลิปใช้ logic เดียวกับ build_centers_reference.py / intl_centers.py
เพื่อให้ตัวเลขตรงกับคอลัมน์ video_matches ในทะเบียน

ใช้: python3 scripts/build_centers_json.py [--src DIR] [--out centers.json]
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

DEFAULT_SRC = Path.home() / 'Documents' / 'boonnews_work' / 'data'

THAI_MONTHS = {
    'ม.ค.': 1, 'ก.พ.': 2, 'มี.ค.': 3, 'เม.ย.': 4, 'พ.ค.': 5, 'มิ.ย.': 6,
    'ก.ค.': 7, 'ส.ค.': 8, 'ก.ย.': 9, 'ต.ค.': 10, 'พ.ย.': 11, 'ธ.ค.': 12,
}


def parse_last_post(s):
    """'มิ.ย.2569' → 256906, '2568' → 256800, '-'/'' → None"""
    s = (s or '').strip()
    if not s or s == '-':
        return None
    m = re.match(r'^(.+?)(\d{4})$', s)
    if m:
        mon = THAI_MONTHS.get(m.group(1).strip())
        year = int(m.group(2))
        return year * 100 + (mon or 0)
    if re.match(r'^\d{4}$', s):
        return int(s) * 100
    return None


def fmt_dur(sec):
    try:
        sec = int(float(sec))
    except (TypeError, ValueError):
        return ''
    if sec >= 3600:
        return f'{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}'
    return f'{sec // 60}:{sec % 60:02d}'


def th_core(center):
    """ตัด prefix ทั่วไปออกเพื่อ loose matching (ตาม build_centers_reference.py)"""
    core = center
    for pre in ['ศูนย์ปฏิบัติธรรม', 'ศูนย์อบรมเยาวชน', 'ธุดงคสถาน', 'ศูนย์']:
        core = core.replace(pre, '')
    return core.split('(')[0].strip()


def intl_token(center):
    """token ไทยของศูนย์ต่างประเทศ (ตาม intl_centers.py)"""
    c = center
    for pre in ['วัดพระธรรมกาย', 'วัดภาวนา', 'วัดพุทธ', 'ศูนย์ปฏิบัติธรรม',
                'ศูนย์ประสานงาน', 'ศูนย์สมาธิทางสายกลาง', 'ศูนย์']:
        c = c.replace(pre, '')
    return c.strip().replace(' ', '')


def load_intl_en(src):
    """ดึงชื่ออังกฤษของศูนย์ต่างประเทศจาก data tuples ใน intl_centers.py"""
    path = src / 'intl_centers.py'
    if not path.exists():
        return {}
    text = path.read_text(encoding='utf-8')
    tuples = re.findall(r'\(\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]*)"\s*\)', text)
    return {center: en for _cont, _country, center, en in tuples}


def match_clips(rec, en, catalog):
    """คืน list ของแถว catalog ที่จับคู่กับศูนย์นี้ (เรียงใหม่สุดก่อนตามลำดับ catalog)"""
    out = []
    if rec['scope'] == 'TH':
        center = rec['center']
        core = th_core(center)
        for row in catalog:
            t = row['temple']
            if not t:
                continue
            if center in t or (len(core) >= 4 and core in t):
                out.append(row)
    else:
        tok = intl_token(rec['center'])
        en_l = (en or '').lower()
        for row in catalog:
            title = row['title']
            tt = title.replace(' ', '')
            if tok and len(tok) >= 3 and tok in tt:
                out.append(row)
            elif en_l and len(en_l) >= 4 and en_l in title.lower():
                out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', type=Path, default=DEFAULT_SRC)
    ap.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent / 'centers.json')
    ap.add_argument('--max-videos', type=int, default=8)
    args = ap.parse_args()

    profiles = args.src / 'all_centers_profiles_v2.csv'
    catalog_csv = args.src / 'boonnews_catalog_newest4000.csv'
    if not profiles.exists():
        sys.exit(f'ไม่พบ {profiles}')
    if not catalog_csv.exists():
        sys.exit(f'ไม่พบ {catalog_csv}')

    with open(profiles, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    with open(catalog_csv, encoding='utf-8-sig') as f:
        catalog = list(csv.DictReader(f))
    intl_en = load_intl_en(args.src)

    centers = []
    matched_total = 0
    for r in rows:
        en = intl_en.get(r['center'], '') if r['scope'] == 'INTL' else ''
        clips = match_clips(r, en, catalog)
        matched_total += len(clips)
        cats = Counter(row['category'] for row in clips if row['category'])
        videos = [
            {'t': row['title'], 'c': row['category'], 'd': fmt_dur(row['duration_sec']),
             'u': row['url']}
            for row in clips[:args.max_videos]
        ]
        types = [t.strip() for t in (r['activity_types'] or '').split(',')
                 if t.strip() and t.strip() != '-']
        centers.append({
            'name': r['center'],
            'en': en,
            'scope': r['scope'],
            'region': r['region'],
            'country': r['country'],
            'province': r['province'],
            'fb': r['facebook_url'],
            'fbc': r['fb_confidence'],
            'followers': '' if r['followers'] in ('', '-') else r['followers'],
            'lastPost': '' if r['last_post'] in ('', '-') else r['last_post'],
            'lastTs': parse_last_post(r['last_post']),
            'active': '' if r['active_level'] in ('', '-') else r['active_level'],
            'types': types,
            'boonnews': r['boonnews'],
            'clips': int(r['video_matches'] or 0),
            'news4y': int(r['news4y'] or 0),
            'cats': dict(cats.most_common()),
            'videos': videos,
        })

    th = sum(1 for c in centers if c['scope'] == 'TH')
    data = {
        'generated': date.today().isoformat(),
        'source': profiles.name,
        'counts': {'total': len(centers), 'th': th, 'intl': len(centers) - th},
        'centers': centers,
    }
    args.out.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    with_clips = sum(1 for c in centers if c['videos'])
    print(f'เขียน {args.out} — {len(centers)} ศูนย์ (ไทย {th} · ตปท. {len(centers) - th})')
    print(f'จับคู่คลิปได้ {matched_total} ครั้ง · ศูนย์ที่มีคลิป {with_clips}/{len(centers)}')


if __name__ == '__main__':
    main()
