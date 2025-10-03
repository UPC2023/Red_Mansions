#scripts\extract_character_events.py
import argparse
import csv
import json
import os
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Iterable, Set


EVENT_KEYWORDS = {
    # 婚恋相关
    "娶": 2.0, "嫁": 2.0, "婚": 2.0, "聘": 1.5, "纳": 1.5, "结亲": 2.0, "成亲": 2.0, "配": 1.5,
    "妻": 2.0, "丈夫": 2.0, "二房": 1.8, "妾": 1.8, "夫妻": 1.8,
    # 生死病灾
    "死": 2.5, "亡": 2.3, "逝": 2.3, "殁": 2.3, "病": 1.8, "病重": 2.2, "病逝": 3.0, "痊": 1.2, "亡故": 2.5,
    # 家庭亲属与出入
    "出生": 2.0, "生": 1.2, "养": 1.2, "认": 1.2, "送": 1.0, "接": 1.0, "祭": 1.6,
    # 官职功过（适度）
    "封": 1.2, "赐": 1.2, "升": 1.4, "贬": 1.6, "罚": 1.4,
    # 冲突互动
    "怒": 1.3, "打": 1.6, "骂": 1.4, "哭": 1.2, "笑": 1.0, "闹": 1.4, "吵": 1.4, "斗": 1.6, "辱": 1.6,
    # 关键社会活动/场景
    "宴": 1.2, "诗": 1.2, "题": 1.0, "会": 1.0, "访": 1.0, "请": 1.0, "救": 1.6, "丧": 2.0,
}

# 关系触发词映射为标准化事件标题模板
RELATION_EVENT_TEMPLATES = {
    "妻": "与{other}成婚",
    "丈夫": "与{other}成婚",
    "二房": "纳{other}为二房",
    "妾": "纳{other}为妾",
    "父亲": "与{other}父子关系",
    "母亲": "与{other}母子关系",
    "女儿": "与{other}母女/父女关系",
    "儿子": "与{other}父子/母子关系",
    "朋友": "与{other}交友",
    "姐妹": "与{other}姐妹关系",
    "兄弟": "与{other}兄弟关系",
}

SENT_SPLIT_RE = re.compile(r"(?<=[。！？；!?;])\s+|\n+")


def load_persons(persons_file: str) -> List[str]:
    persons: List[str] = []
    if os.path.exists(persons_file):
        with open(persons_file, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name:
                    persons.append(name)
    return persons


def load_relations(rel_file: str) -> List[Tuple[str, str, str]]:
    rels: List[Tuple[str, str, str]] = []
    if not os.path.exists(rel_file):
        return rels
    with open(rel_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(",")]
            if len(parts) >= 3:
                h, t, r = parts[0], parts[1], parts[2]
                rels.append((h, t, r))
    return rels


def read_chapters(chapters_dir: str) -> List[Tuple[str, str]]:
    files = [fn for fn in os.listdir(chapters_dir) if fn.endswith(".txt")]
    # sort by leading number if any
    def key_fn(fn: str) -> int:
        m = re.match(r"(\d+)", fn)
        return int(m.group(1)) if m else 0

    files.sort(key=key_fn)
    chapters: List[Tuple[str, str]] = []
    for fn in files:
        path = os.path.join(chapters_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read()
            chapters.append((fn, txt))
        except Exception:
            # skip unreadable files
            continue
    return chapters


def split_sentences(text: str) -> List[str]:
    # Keep punctuation markers by splitting on punctuation followed by whitespace or line break
    # Also collapse excessive spaces
    sents: List[str] = []
    for seg in SENT_SPLIT_RE.split(text):
        seg = seg.strip()
        if seg:
            sents.append(seg)
    return sents


def find_other_persons(sent: str, target: str, person_set: Set[str]) -> List[str]:
    others = []
    for p in person_set:
        if p == target:
            continue
        if p in sent:
            others.append(p)
    # limit to 3 names to avoid overly long fields
    return others[:3]


def score_sentence(sent: str, target: str, others: List[str]) -> Tuple[float, List[str]]:
    score = 0.0
    hit_keywords: List[str] = []
    for kw, w in EVENT_KEYWORDS.items():
        if kw in sent:
            score += w
            hit_keywords.append(kw)
    # interaction with others increases significance
    score += 0.6 * len(others)
    # emphasis punctuation
    if any(ch in sent for ch in ["！", "?", "！", "?"]):
        score += 0.4
    # slightly reward presence near name (heuristic): if keyword is within ±8 chars of the name
    name_pos = sent.find(target)
    if name_pos != -1:
        context_window = sent[max(0, name_pos - 8): name_pos + len(target) + 8]
        for kw, w in EVENT_KEYWORDS.items():
            if kw in context_window:
                score += 0.2
    return score, hit_keywords


def make_title_from_sentence(sent: str, target: str, others: List[str], hit_keywords: List[str]) -> str:
    # Simple templates
    if any(k in hit_keywords for k in ["死", "亡", "逝", "病逝", "殁", "亡故"]):
        return f"{target}去世/病故"
    if any(k in hit_keywords for k in ["娶", "嫁", "婚", "妻", "丈夫", "二房", "妾", "夫妻"]):
        other = others[0] if others else "对方"
        return f"{target}与{other}成婚/成配"
    if any(k in hit_keywords for k in ["怒", "打", "骂", "闹", "吵", "斗", "辱"]):
        other = others[0] if others else "他人"
        return f"{target}与{other}发生冲突"
    if any(k in hit_keywords for k in ["宴", "诗", "会", "访"]):
        return f"{target}参与宴集/游会"
    if any(k in hit_keywords for k in ["丧", "祭"]):
        return f"{target}参与丧事/祭奠"
    # fallback: truncate sentence as summary
    text = sent
    if len(text) > 30:
        text = text[:28] + "…"
    return text


def seed_events_from_relations(persons: Set[str], rels: List[Tuple[str, str, str]]) -> List[Dict[str, str]]:
    events = []
    for h, t, r in rels:
        if r in RELATION_EVENT_TEMPLATES and (h in persons or t in persons):
            title_ht = RELATION_EVENT_TEMPLATES[r].format(other=t)
            title_th = RELATION_EVENT_TEMPLATES[r].format(other=h)
            # Create two directional events for better coverage
            if h in persons:
                events.append({
                    "person": h,
                    "title": title_ht,
                    "sentence": f"{h}与{t}{r}",
                    "chapter": "关系表",
                    "score": 2.2,
                    "counterparts": t,
                    "keywords": r,
                    "rule": "seed_relation",
                })
            if t in persons:
                events.append({
                    "person": t,
                    "title": title_th,
                    "sentence": f"{t}与{h}{r}",
                    "chapter": "关系表",
                    "score": 2.2,
                    "counterparts": h,
                    "keywords": r,
                    "rule": "seed_relation",
                })
    return events


def dedup_events(events: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    result = []
    for e in events:
        key = (e["person"], e["sentence"], e.get("chapter", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(e)
    return result


def extract_events_for_person(person: str, chapters: List[Tuple[str, str]], person_set: Set[str], min_score: float) -> List[Dict[str, str]]:
    extracted: List[Dict[str, str]] = []
    for chap_name, text in chapters:
        sentences = split_sentences(text)
        for sent in sentences:
            if person not in sent:
                continue
            others = find_other_persons(sent, person, person_set)
            score, hit_kws = score_sentence(sent, person, others)
            if score < min_score:
                continue
            title = make_title_from_sentence(sent, person, others, hit_kws)
            extracted.append({
                "person": person,
                "title": title,
                "sentence": sent,
                "chapter": chap_name,
                "score": round(score, 3),
                "counterparts": ",".join(others),
                "keywords": ",".join(hit_kws),
                "rule": "keyword",
            })
    return dedup_events(extracted)


def aggregate_topk(events: List[Dict[str, str]], topk: int) -> List[Dict[str, str]]:
    by_person: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for e in events:
        by_person[e["person"]].append(e)
    top_events: List[Dict[str, str]] = []
    for p, lst in by_person.items():
        # sort by score then prefer shorter titles (heuristic readability)
        lst_sorted = sorted(lst, key=lambda x: (-float(x["score"]), len(x["title"])) )
        top_events.extend(lst_sorted[:topk])
    return top_events


def export_character_events_csv_json(outdir: str, events: List[Dict[str, str]]):
    os.makedirs(outdir, exist_ok=True)
    csv_path = os.path.join(outdir, "character_events.csv")
    json_path = os.path.join(outdir, "character_events.json")
    fields = ["person", "title", "sentence", "chapter", "score", "counterparts", "keywords", "rule"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for e in events:
            writer.writerow(e)
    # group by person for JSON
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for e in events:
        grouped[e["person"]].append(e)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)
    return csv_path, json_path


def export_events_kg(outdir: str, events: List[Dict[str, str]]):
    # Create event nodes and person-event edges
    os.makedirs(outdir, exist_ok=True)
    nodes_path = os.path.join(outdir, "kg_events.csv")
    edges_path = os.path.join(outdir, "kg_event_edges.csv")

    # Create unique IDs for events
    event_nodes: Dict[Tuple[str, str, str], str] = {}
    node_rows = []
    edge_rows = []

    def make_event_id(person: str, title: str, chapter: str) -> str:
        base = f"EV_{person}_{chapter}_{title}"
        base = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", base)
        return base

    for e in events:
        key = (e["person"], e["title"], e["chapter"])
        if key not in event_nodes:
            eid = make_event_id(*key)
            event_nodes[key] = eid
            node_rows.append({
                "id": eid,
                "title": e["title"],
                "sentence": e["sentence"],
                "chapter": e["chapter"],
                "person": e["person"],
            })
        else:
            eid = event_nodes[key]
        # person -> event
        edge_rows.append({
            "src": e["person"],
            "dst": eid,
            "type": "参与",
        })
        # optionally link counterparts
        if e.get("counterparts"):
            for other in e["counterparts"].split(","):
                if other:
                    edge_rows.append({
                        "src": other,
                        "dst": eid,
                        "type": "涉及",
                    })

    with open(nodes_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "sentence", "chapter", "person"])
        writer.writeheader()
        for row in node_rows:
            writer.writerow(row)
    with open(edges_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["src", "dst", "type"])
        writer.writeheader()
        for row in edge_rows:
            writer.writerow(row)
    return nodes_path, edges_path


def main():
    parser = argparse.ArgumentParser(description="Extract major plot events per character from chapter texts")
    parser.add_argument("--chapters-dir", default="reddream_chapters_clean", help="Directory of cleaned chapter .txt files")
    parser.add_argument("--persons-file", default="persons_unique.txt", help="File containing person names, one per line")
    parser.add_argument("--relations-file", default="relation.txt", help="Relation file to seed events (optional)")
    parser.add_argument("--persons", default="", help="Comma-separated subset of persons to extract; default all")
    parser.add_argument("--topk", type=int, default=5, help="Top K events per person to keep")
    parser.add_argument("--min-score", type=float, default=1.0, help="Minimum score threshold for an event candidate")
    parser.add_argument("--outdir", default=".", help="Output directory")
    parser.add_argument("--export-kg", action="store_true", help="Export events as KG nodes/edges")
    parser.add_argument("--no-seed-relations", action="store_true", help="Disable seeding events from relation.txt")
    args = parser.parse_args()

    persons_all = load_persons(args.persons_file)
    if not persons_all:
        print(f"[WARN] No persons loaded from {args.persons_file}")
    person_set = set(persons_all)

    if args.persons.strip():
        targets = [p.strip() for p in args.persons.split(",") if p.strip()]
    else:
        targets = persons_all

    chapters = read_chapters(args.chapters_dir)
    print(f"[INFO] Chapters loaded: {len(chapters)}; persons: {len(targets)} (of {len(persons_all)})")

    all_events: List[Dict[str, str]] = []

    # Seed from relations
    if not args.no_seed_relations and os.path.exists(args.relations_file):
        rels = load_relations(args.relations_file)
        seeded = seed_events_from_relations(set(targets), rels)
        print(f"[INFO] Seeded events from relation.txt: {len(seeded)}")
        all_events.extend(seeded)
    else:
        print("[INFO] Seeding from relations disabled or file missing")

    # Extract per person
    for idx, person in enumerate(targets, 1):
        evts = extract_events_for_person(person, chapters, person_set, args.min_score)
        print(f"[PROC] {idx}/{len(targets)} {person}: candidates={len(evts)}")
        all_events.extend(evts)

    # Keep TopK per person
    top_events = aggregate_topk(all_events, args.topk)
    csv_path, json_path = export_character_events_csv_json(args.outdir, top_events)
    print(f"[DONE] Exported events -> {csv_path}, {json_path}; total rows={len(top_events)}")

    if args.export_kg:
        nodes_path, edges_path = export_events_kg(args.outdir, top_events)
        print(f"[KG] Exported -> {nodes_path}, {edges_path}")


if __name__ == "__main__":
    main()
