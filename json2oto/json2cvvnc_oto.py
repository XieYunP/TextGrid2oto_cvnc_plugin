#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
json2cvvnc_oto - 从 TextGrid JSON 生成 CVNC/CVVNC 方案的 oto.ini

支持两段式 / 三段式 / 四段式：
- 两段式：元音主体与韵尾合并
- 三段式：辅音 + 元音主体 + 韵尾
- 四段式：辅音 + 介母 + 元音主体 + 韵尾
判定依据是 RULE 文件里字内衔接数量（0 / 1 / 2）与 JSON 段数。
"""
import json
import os
import re
from collections import defaultdict


# ============================================================
# 参数默认值与映射
# ============================================================
DEFAULT_PARAMS = {
    'ini.left_shift_ms': 75.0, 'ini.fixed_pct': 30.0, 'ini.overlap_pct': 30.0,
    'onset_nm.right_pct': 65.0, 'onset_nm.fixed_pct': 30.0, 'onset_nm.overlap_pct': 30.0,
    'onset_m.right_pct': 15.0, 'onset_m.fixed_pct': 30.0, 'onset_m.overlap_pct': 30.0,
    'pure_v.left_shift_ms': 75.0, 'pure_v.right_pct': 65.0,
    'pure_v.fixed_pct': 15.0, 'pure_v.overlap_pct': 30.0,
    'nonfirst_v.right_pct': 65.0, 'nonfirst_v.preutt_pct': 15.0,
    'nonfirst_v.fixed_pct': 15.0, 'nonfirst_v.overlap_pct': 30.0,
    'trans_a.boundary_pct': 15.0, 'trans_a.right_pct': 65.0,
    'trans_a.fixed_pct': 30.0, 'trans_a.overlap_pct': 100.0,
    'trans_b.left_pct': 65.0, 'trans_b.assumed_pct': 75.0,
    'trans_b.fixed_pct': 30.0, 'trans_b.overlap_pct': 50.0,
    'codaR.left_pct': 75.0, 'codaR.right_shift_ms': 150.0,
    'codaR.fixed_pct': 30.0, 'codaR.overlap_pct': 50.0,
    'cV.left_pct': 65.0, 'cV.fixed_pct': 30.0, 'cV.overlap_pct': 30.0,
    'cO.left_pct': 65.0, 'cO.right_pct': 65.0, 'cO.fixed_pct': 30.0, 'cO.overlap_pct': 30.0,
}

_PARAM_KEY_MAP = {
    '开头辅音.左边界向左偏移': 'ini.left_shift_ms',
    '开头辅音.固定': 'ini.fixed_pct', '开头辅音.重叠': 'ini.overlap_pct',
    '整音-无介母.右边界': 'onset_nm.right_pct',
    '整音-无介母.固定': 'onset_nm.fixed_pct', '整音-无介母.重叠': 'onset_nm.overlap_pct',
    '整音-有介母.右边界': 'onset_m.right_pct',
    '整音-有介母.固定': 'onset_m.fixed_pct', '整音-有介母.重叠': 'onset_m.overlap_pct',
    '开头纯元音.左边界向左偏移': 'pure_v.left_shift_ms',
    '开头纯元音.右边界': 'pure_v.right_pct',
    '开头纯元音.固定': 'pure_v.fixed_pct', '开头纯元音.重叠': 'pure_v.overlap_pct',
    '非开头纯元音.右边界': 'nonfirst_v.right_pct',
    '非开头纯元音.预发声位置': 'nonfirst_v.preutt_pct',
    '非开头纯元音.固定': 'nonfirst_v.fixed_pct', '非开头纯元音.重叠': 'nonfirst_v.overlap_pct',
    '字内衔接-介母→主元音.分界点': 'trans_a.boundary_pct',
    '字内衔接-介母→主元音.右边界': 'trans_a.right_pct',
    '字内衔接-介母→主元音.固定': 'trans_a.fixed_pct',
    '字内衔接-介母→主元音.重叠': 'trans_a.overlap_pct',
    '字内衔接-主元音→韵尾.左边界': 'trans_b.left_pct',
    '字内衔接-主元音→韵尾.假定韵尾起点': 'trans_b.assumed_pct',
    '字内衔接-主元音→韵尾.固定': 'trans_b.fixed_pct',
    '字内衔接-主元音→韵尾.重叠': 'trans_b.overlap_pct',
    'coda R.左边界': 'codaR.left_pct',
    'coda R.右偏移': 'codaR.right_shift_ms',
    'coda R.固定': 'codaR.fixed_pct', 'coda R.重叠位置': 'codaR.overlap_pct',
    '元音→辅音.左边界': 'cV.left_pct',
    '元音→辅音.固定': 'cV.fixed_pct', '元音→辅音.重叠': 'cV.overlap_pct',
    '元音→整音.左边界': 'cO.left_pct', '元音→整音.右边界': 'cO.right_pct',
    '元音→整音.固定': 'cO.fixed_pct', '元音→整音.重叠': 'cO.overlap_pct',
}


def _parse_params(params):
    out = dict(DEFAULT_PARAMS)
    if not params:
        return out
    for k, v in params.items():
        key = _PARAM_KEY_MAP.get(k)
        if key is not None:
            out[key] = float(v)
    return out


# ============================================================
# RULE / JSON 读取
# ============================================================
def parse_rule_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    rules = {}
    pattern = re.compile(r',(?=(?:[^"]*"[^"]*")*[^"]*$)')
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('[', '#', ';')):
            continue
        if '=' not in line:
            continue
        syllable, value = line.split('=', 1)
        syllable = syllable.strip()
        value = value.strip()
        if not syllable:
            continue
        components = [c.strip().strip('"') for c in pattern.split(value)]
        while len(components) < 4:
            components.append('')
        rules[syllable] = {
            'consonant': components[0].strip(),
            'onset': components[1].strip(),
            'transitions': [t.strip() for t in components[2].split(',') if t.strip()] if components[2].strip() else [],
            'coda': components[3].strip(),
        }
    return rules


def _find_json_path(json_folder):
    for c in [os.path.join(json_folder, 'json', 'ds_phone_filter.json'),
              os.path.join(json_folder, 'json', 'ds_phone.json')]:
        if os.path.exists(c):
            return c
    return None


def read_word_phone_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _ms(x):
    return float(x) * 1000.0


# ============================================================
# 对齐 helper
# ============================================================
def _to_oto(left, preutt, right, fixed, overlap):
    return {
        'offset': int(round(left)),
        'consonant': int(round(fixed - left)),
        'cutoff': int(round(left - right)),
        'preutterance': int(round(preutt - left)),
        'overlap': int(round(overlap - left)),
    }


def _calc_initial_consonant(c_start, c_end, P):
    preutt = c_start
    left = max(c_start - P['ini.left_shift_ms'], 0.0)
    right = c_end
    fixed = left + (right - left) * P['ini.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['ini.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)


def _calc_onset_no_mediant(c_start, v_start, v_end, P):
    """整音-无介母：左=辅音起点（无则元音起点），预=元音起点，右=元音段后 pct%"""
    v_dur = max(v_end - v_start, 1.0)
    left = c_start if c_start is not None else v_start
    preutt = v_start
    right = v_start + v_dur * P['onset_nm.right_pct'] / 100.0
    fixed = preutt + (right - preutt) * P['onset_nm.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['onset_nm.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)


def _calc_onset_with_mediant(c_start, v_start, v_end, P):
    """整音-有介母：右边界 = 介母/主元音分界点 = 元音段前 pct%"""
    v_dur = max(v_end - v_start, 1.0)
    left = c_start if c_start is not None else v_start
    preutt = v_start
    right = v_start + v_dur * P['onset_m.right_pct'] / 100.0
    fixed = preutt + (right - preutt) * P['onset_m.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['onset_m.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)


def _calc_onset_pure_vowel(v_start, v_end, is_first, P):
    v_dur = max(v_end - v_start, 1.0)
    if is_first:
        left = max(v_start - P['pure_v.left_shift_ms'], 0.0)
        preutt = v_start
        right = v_start + v_dur * P['pure_v.right_pct'] / 100.0
        fixed = preutt + (right - preutt) * P['pure_v.fixed_pct'] / 100.0
        overlap = left + (preutt - left) * P['pure_v.overlap_pct'] / 100.0
    else:
        left = v_start
        right = v_start + v_dur * P['nonfirst_v.right_pct'] / 100.0
        preutt = v_start + (right - v_start) * P['nonfirst_v.preutt_pct'] / 100.0
        fixed = preutt + (right - preutt) * P['nonfirst_v.fixed_pct'] / 100.0
        overlap = left + (preutt - left) * P['nonfirst_v.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)


def _calc_trans_a(v_start, v_end, coda_start, P):
    """类型 A：介母→主元音

    - 左边界：元音起点
    - 分界点：元音起点 + 元音时长 × boundary_pct
    - 右边界：有独立韵尾段 → 韵尾起点；无 → 元音起点 + 元音时长 × right_pct
    """
    v_dur = max(v_end - v_start, 1.0)
    left = v_start
    preutt = v_start + v_dur * P['trans_a.boundary_pct'] / 100.0
    if coda_start is not None:
        right = coda_start
    else:
        right = v_start + v_dur * P['trans_a.right_pct'] / 100.0
    fixed = preutt + (right - preutt) * P['trans_a.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['trans_a.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)


def _calc_trans_b(v_start, v_end, coda_start, coda_end, P):
    """类型 B：主元音→韵尾

    - 韵尾起点：有独立韵尾段 → 韵尾起点；无 → 元音起点 + 元音时长 × assumed_pct
    - 左边界：元音起点→韵尾起点之间偏右 left_pct
    - 预发声：韵尾起点
    - 右边界：有独立韵尾段 → 韵尾结束；无 → 元音结束
    """
    v_dur = max(v_end - v_start, 1.0)
    if coda_start is not None:
        coda_or_assumed = coda_start
        right = coda_end
    else:
        coda_or_assumed = v_start + v_dur * P['trans_b.assumed_pct'] / 100.0
        right = v_end
    left = v_start + (coda_or_assumed - v_start) * P['trans_b.left_pct'] / 100.0
    preutt = coda_or_assumed
    fixed = preutt + (right - preutt) * P['trans_b.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['trans_b.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)
def _calc_coda_r(v_start, v_end, coda_start, coda_end, audio_end_ms, P):
    """coda R：有韵尾用韵尾段，无韵尾用元音段"""
    if coda_start is not None:
        seg_start, seg_end = coda_start, coda_end
    else:
        seg_start, seg_end = v_start, v_end
    seg_dur = max(seg_end - seg_start, 1.0)
    left = seg_start + seg_dur * P['codaR.left_pct'] / 100.0
    preutt = seg_end
    right = preutt + P['codaR.right_shift_ms']
    if audio_end_ms is not None and right > audio_end_ms:
        right = audio_end_ms
    if right < preutt:
        right = preutt
    fixed = preutt + (right - preutt) * P['codaR.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['codaR.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)

def _calc_cV(v_start, v_end, coda_start, coda_end, nc_start, nc_end, P):
    """元音→辅音（跨音节）：预=前音节韵尾或元音结束，右=下一辅音中点"""
    if coda_start is not None:
        seg_start, seg_end = coda_start, coda_end
    else:
        seg_start, seg_end = v_start, v_end
    seg_dur = max(seg_end - seg_start, 1.0)
    left = seg_start + seg_dur * P['cV.left_pct'] / 100.0
    preutt = seg_end
    right = (nc_start + nc_end) / 2.0
    fixed = preutt + (right - preutt) * P['cV.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['cV.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)


def _calc_cO(v_start, v_end, coda_start, coda_end, nv_start, nv_end, P):
    """元音→整音（跨音节）：预=下一元音起点"""
    if coda_start is not None:
        seg_start, seg_end = coda_start, coda_end
    else:
        seg_start, seg_end = v_start, v_end
    seg_dur = max(seg_end - seg_start, 1.0)
    left = seg_start + seg_dur * P['cO.left_pct'] / 100.0
    preutt = nv_start
    nv_dur = max(nv_end - nv_start, 1.0)
    right = nv_start + nv_dur * P['cO.right_pct'] / 100.0
    fixed = preutt + (right - preutt) * P['cO.fixed_pct'] / 100.0
    overlap = left + (preutt - left) * P['cO.overlap_pct'] / 100.0
    return _to_oto(left, preutt, right, fixed, overlap)


# ============================================================
# Phone 分配与拆分判定
# ============================================================
def _scan_syllable_phones_by_word(audio_name, item, word_data, rules, ignore):
    """按 word_phone.json 的音节时间戳切分 ds_phone_filter 的 phone 段。

    不依赖文本匹配；符号不同也能正确归属。
    返回 [(syl, rule, phone_list), ...]；phone_list 里每项是 (None, phone_dict)。
    若 word_data 里找不到对应条目，返回 None（调用方回退旧逻辑）。
    """
    word_item = word_data.get(audio_name)
    if not word_item:
        return None

    word_syls = []
    for k, v in sorted(word_item.get('phones', {}).items(), key=lambda x: int(x[0])):
        text = (v.get('text') or '').strip()
        if not text or text in ignore:
            continue
        syl = text if text in rules else None
        if syl is None:
            alt = text.replace('_', '')
            if alt in rules:
                syl = alt
        if syl is None:
            continue
        word_syls.append({
            'syl': syl,
            'start_ms': _ms(v['xmin']),
            'end_ms': _ms(v['xmax']),
        })
    if not word_syls:
        return None

    phones_list = []
    for k, v in sorted(item.get('phones', {}).items(), key=lambda x: int(x[0])):
        text = v.get('text', '')
        if text in ignore:
            continue
        phones_list.append({
            'text': text,
            'xmin_s': v['xmin'],
            'xmax_s': v['xmax'],
            'start_ms': _ms(v['xmin']),
            'end_ms': _ms(v['xmax']),
        })

    result = []
    for ws in word_syls:
        assigned = []
        for ap in phones_list:
            ap_dur = ap['end_ms'] - ap['start_ms']
            if ap_dur <= 1e-3:
                center = (ap['start_ms'] + ap['end_ms']) / 2.0
                if ws['start_ms'] - 1 <= center <= ws['end_ms'] + 1:
                    assigned.append(ap)
            else:
                ov = min(ap['end_ms'], ws['end_ms']) - max(ap['start_ms'], ws['start_ms'])
                if ov / ap_dur >= 0.5:
                    assigned.append(ap)
        plist = [(None, {'text': ap['text'],
                         'xmin': ap['xmin_s'],
                         'xmax': ap['xmax_s']}) for ap in assigned]
        result.append((ws['syl'], rules[ws['syl']], plist))
    return result


def _scan_syllable_phones(syllables, actual_phones, rules):
    """按"是否匹配下一音节辅音"为界，把 actual_phones 切给每个音节。

    返回 [(syl, rule, phone_list), ...]
    phone_list 的段数可能是 2（C+V）/ 3（C+V+coda 或 C+介母+V 合并）
    或 4（C+介母+V+coda，罕见）。
    """
    result = []
    p_idx = 0
    n = len(syllables)
    for i, syl in enumerate(syllables):
        rule = rules[syl]
        start = p_idx
        # 1) 辅音段（与 RULE 声明同名）
        if rule['consonant'] and p_idx < len(actual_phones):
            if actual_phones[p_idx][1].get('text') == rule['consonant']:
                p_idx += 1
        # 2) 元音主体（含介母，如果模型把介母合并进元音）
        if p_idx < len(actual_phones):
            p_idx += 1
        # 3) 韵尾段（可选）：看下一段是否等于下一音节的辅音
        next_cons = None
        if i + 1 < n and syllables[i + 1] in rules:
            next_cons = rules[syllables[i + 1]]['consonant']
        if p_idx < len(actual_phones):
            text = actual_phones[p_idx][1].get('text', '')
            if text != next_cons:
                p_idx += 1
        result.append((syl, rule, actual_phones[start:p_idx]))
    return result

def _has_mediant_in_rule(rule):
    """判定 RULE 是否声明了介母分界点。

    - transitions >= 2 → 有介母
    - transitions == 1:
        - coda 带 ~ → 该 transition 是"元音→韵尾" → 无介母
        - coda 不带 ~ → 该 transition 是"介母→元音" → 有介母
    - transitions == 0 → 无介母
    """
    n_trans = len(rule['transitions'])
    if n_trans >= 2:
        return True
    if n_trans == 1:
        return '~' not in rule['coda']
    return False


def _decide_mode(rule, seg_len, trans_mode, has_coda):
    n_trans = len(rule['transitions'])
    has_mediant = _has_mediant_in_rule(rule)
    warn = None

    if trans_mode == '2seg':
        if has_coda:
            warn = "JSON 切出了独立韵尾，已按两段式合并"
        return True, False, False, False, warn

    # auto
    if n_trans == 0:
        return True, False, False, False, None

    if has_mediant:
        return False, False, True, True, None   # 四段式

    # n_trans >= 1 且无介母 → RULE 声明的是"元音→韵尾"过渡
    # 无论 JSON 是否切出独立韵尾，都产字内衔接
    if has_coda:
        return False, True, False, False, None
    warn = f"音节 '{rule['onset']}' JSON 未切出独立韵尾，字内衔接用假定韵尾起点"
    return False, True, False, False, warn   # ← 由 2seg 改回 3seg
    
# ============================================================
# 核心生成
# ============================================================
def generate_oto(json_data, rules, word_data=None,
                 first_sound='consonant', ignore=None,
                 max_cv_aliases=0, max_vc_aliases=0, ensure_all_audio=False,
                 keep_isolated_vowel=False, params=None, alias_strategy='replace',
                 trans_mode='auto', ncv_enabled=False):
    if ignore is None:
        ignore = {'R', 'SP', 'AP', 'sil', 'pau', 'EP'}

    P = _parse_params(params)

    all_entries = []
    full_index = {}
    warnings = []
    infos = []
    cv_count = defaultdict(int)
    vc_count = defaultdict(int)

    def add_entry(entry, is_cv):
        # 先记录全量索引：无论后续是否被 max_cv/max_vc 剔除，都留下
        _fn = entry['filename']
        _base = entry['alias'].split('#')[0]
        if (_fn, _base) not in full_index:
            full_index[(_fn, _base)] = dict(entry)
        base = entry['alias']
        counts = cv_count if is_cv else vc_count
        max_n = max_cv_aliases if is_cv else max_vc_aliases
        n = counts[base]
        if max_n > 0 and n >= max_n:
            if alias_strategy == 'replace':
                # 找所有同名候选
                candidates = [i for i, e in enumerate(all_entries)
                              if e['alias'].split('#')[0] == base]
                if not candidates:
                    return False
                # 选一个"pop 后目标音频还有其他条目"的候选
                target_idx = None
                for i in candidates:
                    fn = all_entries[i]['filename']
                    # 同一 filename 下条目数 > 1 才安全 pop
                    if sum(1 for e in all_entries if e['filename'] == fn) > 1:
                        target_idx = i
                        break
                if target_idx is None:
                    # 所有候选的目标音频都只有这一条 → 不能 pop
                    # 放弃添加当前条目，原音频完整保留
                    return False
                all_entries.pop(target_idx)
                counts[base] -= 1
                n = counts[base]
            else:
                return False
        if n > 0:
            entry = dict(entry)
            entry['alias'] = f"{base}#{n}"
        counts[base] += 1
        all_entries.append(entry)
        return True

    for audio_name, item in json_data.items():
        before = len(all_entries)

        wav_long = item.get('wav_long', [0, 0])
        audio_end_ms = _ms(wav_long[1]) if len(wav_long) >= 2 else None

        # 优先用 word_phone 时间戳切分
        syllable_phones = None
        if word_data:
            syllable_phones = _scan_syllable_phones_by_word(
                audio_name, item, word_data, rules, ignore
            )

        # 回退：旧的文件名 + 文本匹配方式
        if syllable_phones is None:
            syllables = [s.strip() for s in audio_name.split('_') if s.strip()]
            syllables = [s for s in syllables if s not in ignore]
            if not syllables:
                warnings.append(f"{audio_name}: 文件名中没有有效音节")
                continue
            missing = [s for s in syllables if s not in rules]
            if missing:
                warnings.append(f"{audio_name}: 音节 {', '.join(missing)} 在规则文件中找不到")
                syllables = [s for s in syllables if s in rules]
                if not syllables:
                    continue
            phones = item.get('phones', {})
            if not phones:
                warnings.append(f"{audio_name}: 没有 phones 数据")
                continue
            sorted_phones = sorted(phones.items(), key=lambda x: int(x[0]))
            actual_phones = [(k, v) for k, v in sorted_phones
                             if v.get('text') not in ignore]
            syllable_phones = _scan_syllable_phones(
                syllables, actual_phones, rules
            )
        # 无论走 word_phone 还是回退，都从 syllable_phones 反推 syllables
        syllables = [s for (s, _, _) in syllable_phones]
        if not syllable_phones:
            warnings.append(f"{audio_name}: 没有可用的音节-phone 匹配")
            continue

        n_syl = len(syllable_phones)

        # 预先把每个音节的段信息打包
        parsed = []
        for syl, rule, plist in syllable_phones:
            seg_len = len(plist)
            cons_p = vowel_p = coda_p = None
            # 假设段顺序是 [辅音?] [元音（含介母）] [韵尾?]
            i = 0
            if rule['consonant'] and i < seg_len:
                if plist[i][1].get('text') == rule['consonant']:
                    cons_p = plist[i]
                    i += 1
            if i < seg_len:
                vowel_p = plist[i]
                i += 1
            if i < seg_len:
                coda_p = plist[i]
                i += 1
            if vowel_p is None:
                parsed.append(None)
                continue
            # 元音区：所有非辅音段的合并（含 vowel_p 和 coda_p）
            v_start = _ms(vowel_p[1]['xmin'])
            v_end = _ms(vowel_p[1]['xmax'])
            v_zone_start = v_start
            v_zone_end = v_end
            if coda_p is not None:
                v_zone_end = _ms(coda_p[1]['xmax'])

            parsed.append({
                'syl': syl, 'rule': rule,
                'cons_p': cons_p, 'vowel_p': vowel_p, 'coda_p': coda_p,
                'seg_len': seg_len,
                'v_zone_start': v_zone_start,   
                'v_zone_end': v_zone_end,       
            })

        # 生成
        for syl_idx, info in enumerate(parsed):
            if info is None:
                continue
            syl = info['syl']
            rule = info['rule']
            cons_p = info['cons_p']
            vowel_p = info['vowel_p']
            coda_p = info['coda_p']
            seg_len = info['seg_len']

            is_first = syl_idx == 0
            is_last = syl_idx == n_syl - 1

            c_start = _ms(cons_p[1]['xmin']) if cons_p else None
            c_end = _ms(cons_p[1]['xmax']) if cons_p else None
            v_start = _ms(vowel_p[1]['xmin'])
            v_end = _ms(vowel_p[1]['xmax'])
            co_start = _ms(coda_p[1]['xmin']) if coda_p else None
            co_end = _ms(coda_p[1]['xmax']) if coda_p else None

            has_coda = coda_p is not None
            is_2seg, is_3seg, is_4seg, has_mediant, warn = _decide_mode(
                rule, seg_len, trans_mode, has_coda
            )
            if warn:
                infos.append(f"音节 '{syl}': {warn}")

            # ── 开头 / 非开头整音 ──
            # ── 开头 / 非开头整音 ──
            if is_first:
                if first_sound == 'consonant' and rule['consonant'] and c_start is not None:
                    entry = {
                        'filename': f"{audio_name}.wav",
                        'alias': f"- {rule['consonant']}",
                        **_calc_initial_consonant(c_start, c_end, P),
                    }
                    add_entry(entry, is_cv=True)
                elif not rule['consonant']:
                    # 开头纯元音：走 pure_v 公式（left 提前 75ms）
                    pd = _calc_onset_pure_vowel(v_start, v_end, True, P)
                    entry = {
                        'filename': f"{audio_name}.wav",
                        'alias': f"- {rule['onset']}",
                        **pd,
                    }
                    add_entry(entry, is_cv=True)
                else:
                    if is_4seg or has_mediant:
                        pd = _calc_onset_with_mediant(c_start, v_start, v_end, P)
                    else:
                        pd = _calc_onset_no_mediant(c_start, v_start, v_end, P)
                    entry = {
                        'filename': f"{audio_name}.wav",
                        'alias': f"- {rule['onset']}",
                        **pd,
                    }
                    add_entry(entry, is_cv=True)

            # ── 字内衔接 ──
            if is_2seg:
                # 强制二段式：字内衔接不生成
                pass
            vz_start = info['v_zone_start']
            vz_end = info['v_zone_end']

            if is_2seg:
                pass
            elif is_3seg:
                if len(rule['transitions']) >= 1:
                    pd = _calc_trans_b(vz_start, vz_end, None, None, P)
                    add_entry({
                        'filename': f"{audio_name}.wav",
                        'alias': rule['transitions'][0], **pd,
                    }, is_cv=is_first)
            elif is_4seg:
                if len(rule['transitions']) >= 1:
                    pd = _calc_trans_a(vz_start, vz_end, None, P)
                    add_entry({
                        'filename': f"{audio_name}.wav",
                        'alias': rule['transitions'][0], **pd,
                    }, is_cv=is_first)
                if len(rule['transitions']) >= 2:
                    pd = _calc_trans_b(vz_start, vz_end, None, None, P)
                    add_entry({
                        'filename': f"{audio_name}.wav",
                        'alias': rule['transitions'][1], **pd,
                    }, is_cv=is_first)
                    
            # ── 跨音节衔接 ──
            if not is_last:
                next_info = parsed[syl_idx + 1]
                if next_info is None:
                    continue
                next_rule = next_info['rule']
                next_cons_p = next_info['cons_p']
                next_vowel_p = next_info['vowel_p']
                nv_start = _ms(next_vowel_p[1]['xmin'])
                nv_end = _ms(next_vowel_p[1]['xmax'])
                if next_cons_p:
                    nc_start = _ms(next_cons_p[1]['xmin'])
                    nc_end = _ms(next_cons_p[1]['xmax'])
                else:
                    nc_start = nc_end = None

                front = rule['coda'] if rule['coda'] else rule['onset']

                # 元音→辅音（cV）：仅传统模式产
                if (not ncv_enabled) and next_rule['consonant'] and nc_start is not None:
                    pd = _calc_cV(v_start, v_end, co_start, co_end,
                                  nc_start, nc_end, P)
                    entry = {
                        'filename': f"{audio_name}.wav",
                        'alias': f"{front} {next_rule['consonant']}",
                        **pd,
                    }
                    add_entry(entry, is_cv=False)

                # 元音→整音（cO）：NCV 模式下无条件产；传统模式下仅下一音节无辅音时产
                if ncv_enabled or (not next_rule['consonant']):
                    pd = _calc_cO(v_start, v_end, co_start, co_end,
                                  nv_start, nv_end, P)
                    entry = {
                        'filename': f"{audio_name}.wav",
                        'alias': f"{front} {next_rule['onset']}",
                        **pd,
                    }
                    add_entry(entry, is_cv=False)

        # ── 兜底 ──
        # 不用 added==0 判断（replace 策略下 pop+add 净变化可能是 0）
        cur_fn = f"{audio_name}.wav"
        has_entry = any(e['filename'] == cur_fn for e in all_entries)
        if not has_entry:
            if ensure_all_audio:
                fallback_syl = next((s for s in syllables if s in rules), None)
                if fallback_syl is not None:
                    fb_rule = rules[fallback_syl]
                    # 兜底别名遵从 first_sound 设定
                    if first_sound == 'consonant' and fb_rule['consonant']:
                        alias = f"- {fb_rule['consonant']}"
                    else:
                        # first_sound == 'onset' 或纯元音音节（无辅音可作开头）
                        alias = f"- {fb_rule['onset']}"
                else:
                    alias = "- a"
                # 直接从 item 里算起止，不依赖分支外的 actual_phones
                phones_all = item.get('phones', {})
                valid = [
                    v for _, v in sorted(phones_all.items(), key=lambda x: int(x[0]))
                    if v.get('text') not in ignore
                ]
                if valid:
                    p_start = _ms(valid[0]['xmin'])
                    p_end = _ms(valid[-1]['xmax'])
                else:
                    wl = item.get('wav_long', [0, 1])
                    p_start = _ms(wl[0])
                    p_end = _ms(wl[1])
                dur = max(p_end - p_start, 1.0)
                all_entries.append({
                    'filename': f"{audio_name}.wav",
                    'alias': alias,
                    'offset': int(round(p_start)),
                    'consonant': int(round(dur * 0.5)),
                    'cutoff': int(round(-dur)),
                    'preutterance': int(round(dur * 0.2)),
                    'overlap': int(round(dur * 0.1)),
                })
                warnings.append(f"{audio_name}: 所有音节失败，已生成兜底 '{alias}'")
            else:
                warnings.append(f"{audio_name}: 所有音节失败，已跳过")

    return all_entries, warnings, infos, full_index


# ============================================================
# 排序 / 去重 / 覆盖检查 / 模板
# ============================================================
def _natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def _syllables_in_filename(filename, rules):
    """从 filename 拆出在 rules 里的音节列表"""
    stem = filename[:-4] if filename.lower().endswith('.wav') else filename
    return [s.strip() for s in stem.split('_') if s.strip() in rules]

def _classify_alias(alias, syllables, rules):
    result = []
    if not syllables:
        return result

    base = alias.split('#')[0]

    # 1. 开头
    if base.startswith('- '):
        target = base[2:]
        rule = rules[syllables[0]]
        if rule['consonant'] == target:
            result.append((0, 'initial', 0))
        if rule['onset'] == target:
            result.append((0, 'onset_first', 0))
        return result

    # 2. coda R
    if base.endswith(' R') or base.endswith(' -'):
        target = base[:-2].strip()
        last_idx = len(syllables) - 1
        rule = rules[syllables[last_idx]]
        coda = rule['coda'] if rule['coda'] else rule['onset']
        if coda == target:
            result.append((last_idx, 'coda_r', 0))
        return result

    # 3. 字内衔接
    for i, s in enumerate(syllables):
        for j, t in enumerate(rules[s]['transitions']):
            if t == base:
                result.append((i, 'transition', j))

    # 4. 非首整音
    for i, s in enumerate(syllables):
        if i == 0:
            continue
        if rules[s]['onset'] == base:
            result.append((i, 'onset_nonfirst', 0))

    # 5. 跨音节
    if ' ' in base:
        parts = base.split(' ', 1)
        front, back = parts[0].strip(), parts[1].strip()
        for i in range(len(syllables) - 1):
            cur_rule = rules[syllables[i]]
            next_rule = rules[syllables[i + 1]]
            cur_front = cur_rule['coda'] if cur_rule['coda'] else cur_rule['onset']
            if cur_front != front:
                continue
            if next_rule['consonant'] == back:
                result.append((i, 'cross_cons', 0))
            if next_rule['onset'] == back:
                result.append((i, 'cross_onset', 0))

    return result

def _keep_alias(alias, first_sound, rules):
    """开头条目按 first_sound 过滤；非开头一律保留"""
    if not alias.startswith('- '):
        return True
    target = alias[2:]
    if first_sound == 'consonant':
        all_cons = {r['consonant'] for r in rules.values() if r['consonant']}
        all_vowel_onsets = {r['onset'] for r in rules.values() if not r['consonant']}
        return target in all_cons or target in all_vowel_onsets
    all_onsets = {r['onset'] for r in rules.values()}
    return target in all_onsets

def sort_oto_entries(entries, mode, rules, template_order=None):
    if mode == 'natural':
        return sorted(entries, key=lambda e: (_natural_key(e['filename']), e['offset']))

    if mode == 'template' and template_order is not None:
        # 按模板出现顺序排
        order_map = {f"{fn}={alias}": i
                     for i, (fn, alias) in enumerate(template_order)}
        return sorted(entries, key=lambda e: order_map.get(
            f"{e['filename']}={e['alias'].split('#')[0]}", 999999))

    all_onsets = set()
    all_codas = set()
    all_consonants = set()
    all_vowel_onsets = set()
    all_transitions = set()
    for info in rules.values():
        all_onsets.add(info['onset'])
        if info['coda']:
            all_codas.add(info['coda'])
        if info['consonant']:
            all_consonants.add(info['consonant'])
        if not info['consonant']:
            all_vowel_onsets.add(info['onset'])
        all_transitions.update(info['transitions'])

    def category(alias):
        if alias.startswith('- '):
            return (0, 0)
        if alias in all_onsets:
            return (1, 0)
        if alias in all_transitions:
            return (2, 0)
        if alias.endswith(' R') or alias.endswith(' -'):
            return (6, 0)
        if ' ' in alias:
            first, second = alias.split(' ', 1)
            if first in all_codas:
                if second in all_consonants:
                    return (3, 0)
                elif second in all_vowel_onsets:
                    return (4, 0)
            elif first in all_onsets and second in all_consonants:
                return (5, 0)
        return (7, 0)

    return sorted(entries, key=lambda e: (
        category(e['alias']), _natural_key(e['filename']), e['offset']
    ))


def remove_redundant(entries):
    audio_total = defaultdict(int)
    for e in entries:
        audio_total[e['filename']] += 1
    audio_kept = defaultdict(int)
    covered = set()
    result = []
    for e in entries:
        base = e['alias'].split('#')[0]
        if base in covered:
            remaining = audio_total[e['filename']] - audio_kept[e['filename']]
            if remaining <= 1:
                result.append(e)
                audio_kept[e['filename']] += 1
        else:
            result.append(e)
            audio_kept[e['filename']] += 1
        covered.add(base)
    return result


def check_coverage(entries, json_data, rules, first_sound, keep_isolated_vowel=False):
    covered = set(e['alias'].split('#')[0] for e in entries)
    missing = set()

    # 只统计数据里实际出现的音节和相邻对
    appearing_syls = set()
    appearing_pairs = set()
    for audio_name in json_data.keys():
        s = [x.strip() for x in audio_name.split('_') if x.strip()]
        s = [x for x in s if x in rules]
        for x in s:
            appearing_syls.add(x)
        for i in range(len(s) - 1):
            appearing_pairs.add((s[i], s[i + 1]))

    for syl in appearing_syls:
        info = rules[syl]
        a = (f"- {info['consonant']}" if (first_sound == 'consonant' and info['consonant'])
             else f"- {info['onset']}")
        if a not in covered:
            missing.add(a)
        a2 = f"{info['coda']} R" if info['coda'] else f"{info['onset']} R"
        if a2 not in covered:
            missing.add(a2)
        for t in info['transitions']:
            if t not in covered:
                missing.add(t)
        if keep_isolated_vowel and info['onset'] not in covered:
            missing.add(info['onset'])

    for sa, sb in appearing_pairs:
        ia, ib = rules[sa], rules[sb]
        front = ia['coda'] if ia['coda'] else ia['onset']
        if ib['consonant']:
            a = f"{front} {ib['consonant']}"
        else:
            a = f"{front} {ib['onset']}"
        if a not in covered:
            missing.add(a)

    return sorted(missing)


def load_template_oto(path):
    template = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('#', '[')):
                continue
            if '=' not in line:
                continue
            fn, rest = line.split('=', 1)
            fn = fn.strip()
            parts = [p.strip() for p in rest.split(',')]
            if len(parts) < 6:
                continue
            alias = parts[0]
            try:
                vals = [int(round(float(parts[i]))) if parts[i] else 0 for i in range(1, 6)]
            except ValueError:
                continue
            template[(fn, alias)] = {
                'filename': fn, 'alias': alias,
                'offset': vals[0], 'consonant': vals[1],
                'cutoff': vals[2], 'preutterance': vals[3], 'overlap': vals[4],
            }
    return template

def _bootstrap_missing_aliases(all_entries, json_data, word_data, rules, P,
                                first_sound, trans_mode, ignore,
                                keep_isolated_vowel=False, ncv_enabled=False):
    """笛卡尔积补全：理论需要的别名若未覆盖，从任意音频找一条能产它的强制 append。

    不再检查 max_cv_aliases —— 覆盖优先。
    """
    covered = set(e['alias'].split('#')[0] for e in all_entries)

    # ── 理论需要的别名全集 ──
    all_onsets = set()
    all_transitions = set()
    all_codas = set()
    all_consonants = set()
    all_vowel_onsets = set()
    for info in rules.values():
        all_onsets.add(info['onset'])
        all_transitions.update(info['transitions'])
        if info['coda']:
            all_codas.add(info['coda'])
        if info['consonant']:
            all_consonants.add(info['consonant'])
        else:
            all_vowel_onsets.add(info['onset'])

    needed = set()
    # 开头音
    for info in rules.values():
        if first_sound == 'consonant' and info['consonant']:
            needed.add(f"- {info['consonant']}")
        else:
            needed.add(f"- {info['onset']}")
    # coda R
    for info in rules.values():
        coda = info['coda'] if info['coda'] else info['onset']
        needed.add(f"{coda} R")
    # 单独整音（无前缀 onset）
    needed.update(all_onsets)
    # transitions
    needed.update(all_transitions)
    # 跨音节
    for coda in all_codas:
        for cons in all_consonants:
            needed.add(f"{coda} {cons}")
        for vo in all_vowel_onsets:
            needed.add(f"{coda} {vo}")

    missing = needed - covered
    if not missing:
        return

    # ── 遍历所有音频，能产 missing 里的别名就补 ──
    for audio_name, item in json_data.items():
        if not missing:
            break

        wav_long = item.get('wav_long', [0, 0])
        audio_end_ms = _ms(wav_long[1]) if len(wav_long) >= 2 else None

        # 复用切分逻辑
        syllable_phones = None
        if word_data:
            syllable_phones = _scan_syllable_phones_by_word(
                audio_name, item, word_data, rules, ignore
            )
        if syllable_phones is None:
            syllables = [s.strip() for s in audio_name.split('_') if s.strip()]
            syllables = [s for s in syllables if s in rules]
            phones = item.get('phones', {})
            if not phones or not syllables:
                continue
            
            sorted_phones = sorted(phones.items(), key=lambda x: int(x[0]))
            actual_phones = [(k, v) for k, v in sorted_phones
                             if v.get('text') not in ignore]
            syllable_phones = _scan_syllable_phones(syllables, actual_phones, rules)
        if not syllable_phones:
            continue

        n_syl = len(syllable_phones)
        cur_fn = f"{audio_name}.wav"

        def _emit(alias, pd):
            all_entries.append({'filename': cur_fn, 'alias': alias, **pd})
            covered.add(alias)
            missing.discard(alias)

        for syl_idx, (syl, rule, plist) in enumerate(syllable_phones):
            seg_len = len(plist)
            cons_p = vowel_p = coda_p = None
            i = 0
            if rule['consonant'] and i < seg_len:
                if plist[i][1].get('text') == rule['consonant']:
                    cons_p = plist[i]; i += 1
            if i < seg_len:
                vowel_p = plist[i]; i += 1
            if i < seg_len:
                coda_p = plist[i]; i += 1
            if vowel_p is None:
                continue

            is_first = syl_idx == 0
            is_last = syl_idx == n_syl - 1
            c_start = _ms(cons_p[1]['xmin']) if cons_p else None
            c_end = _ms(cons_p[1]['xmax']) if cons_p else None
            v_start = _ms(vowel_p[1]['xmin'])
            v_end = _ms(vowel_p[1]['xmax'])
            co_start = _ms(coda_p[1]['xmin']) if coda_p else None
            co_end = _ms(coda_p[1]['xmax']) if coda_p else None
            has_coda = coda_p is not None

            # 元音区：所有非辅音段的合并
            v_zone_start = v_start
            v_zone_end = v_end
            if coda_p is not None:
                v_zone_end = _ms(coda_p[1]['xmax'])

            is_2seg, is_3seg, is_4seg, has_mediant, _ = _decide_mode(
                rule, seg_len, trans_mode, has_coda
            )

            # 开头音
            if is_first:
                if first_sound == 'consonant' and rule['consonant'] and c_start is not None:
                    alias = f"- {rule['consonant']}"
                    if alias in missing:
                        _emit(alias, _calc_initial_consonant(c_start, c_end, P))
                else:
                    alias = f"- {rule['onset']}"
                    if alias in missing:
                        if is_4seg or has_mediant:
                            _emit(alias, _calc_onset_with_mediant(c_start, v_start, v_end, P))
                        else:
                            _emit(alias, _calc_onset_no_mediant(c_start, v_start, v_end, P))
            else:
                alias = rule['onset']
                if alias in missing:
                    if not rule['consonant']:
                        # 纯元音 onset：只在用户开启时补
                        if keep_isolated_vowel:
                            _emit(alias, _calc_onset_pure_vowel(v_start, v_end, False, P))
                    else:
                        # 有辅音整音：无条件补
                        if is_4seg or has_mediant:
                            _emit(alias, _calc_onset_with_mediant(c_start, v_start, v_end, P))
                        else:
                            _emit(alias, _calc_onset_no_mediant(c_start, v_start, v_end, P))

            # 字内衔接
            if is_2seg:
                pass
            elif is_3seg:
                if len(rule['transitions']) >= 1:
                    alias = rule['transitions'][0]
                    if alias in missing:
                        _emit(alias, _calc_trans_b(v_zone_start, v_zone_end, None, None, P))
            elif is_4seg:
                if len(rule['transitions']) >= 1:
                    alias = rule['transitions'][0]
                    if alias in missing:
                        _emit(alias, _calc_trans_a(v_zone_start, v_zone_end, None, P))
                if len(rule['transitions']) >= 2:
                    alias = rule['transitions'][1]
                    if alias in missing:
                        _emit(alias, _calc_trans_b(v_zone_start, v_zone_end, None, None, P))

            # coda R
            if is_last:
                alias = f"{rule['coda']} R" if rule['coda'] else f"{rule['onset']} R"
                if alias in missing:
                    _emit(alias, _calc_coda_r(v_start, v_end, co_start, co_end, audio_end_ms, P))

            # 跨音节
            if not is_last:
                next_syl, next_rule, next_plist = syllable_phones[syl_idx + 1]
                nseg_len = len(next_plist)
                next_cons_p = next_vowel_p = None
                ni = 0
                if next_rule['consonant'] and ni < nseg_len:
                    if next_plist[ni][1].get('text') == next_rule['consonant']:
                        next_cons_p = next_plist[ni]; ni += 1
                if ni < nseg_len:
                    next_vowel_p = next_plist[ni]
                if next_vowel_p is None:
                    continue

                nv_start = _ms(next_vowel_p[1]['xmin'])
                nv_end = _ms(next_vowel_p[1]['xmax'])
                if next_cons_p:
                    nc_start = _ms(next_cons_p[1]['xmin'])
                    nc_end = _ms(next_cons_p[1]['xmax'])
                else:
                    nc_start = nc_end = None

                front = rule['coda'] if rule['coda'] else rule['onset']

                if (not ncv_enabled) and next_rule['consonant'] and nc_start is not None:
                    alias = f"{front} {next_rule['consonant']}"
                    if alias in missing:
                        _emit(alias, _calc_cV(v_start, v_end, co_start, co_end, nc_start, nc_end, P))
                if ncv_enabled or (not next_rule['consonant']):
                    alias = f"{front} {next_rule['onset']}"
                    if alias in missing:
                        _emit(alias, _calc_cO(v_start, v_end, co_start, co_end, nv_start, nv_end, P))

def _fallback_consonant_range(next_syl, word_data, audio_name, v_start_ms):
    """辅音段在 ds_phone_filter 里没切出时，从 word_phone 的 middle 点估算。"""
    if word_data:
        word_item = word_data.get(audio_name)
        if word_item:
            for k, v in word_item.get('phones', {}).items():
                text = (v.get('text') or '').strip()
                if text == next_syl:
                    xmin = _ms(v['xmin'])
                    middle = _ms(v.get('middle', v['xmin']))
                    if middle > xmin:
                        return xmin, middle
    return v_start_ms - 30.0, v_start_ms


def _build_full_index(json_data, word_data, rules, P, first_sound, trans_mode,
                      ignore, keep_isolated_vowel=False, ncv_enabled=False):
    """扫描所有音频 → 每个音节都产所有可能别名 → (filename, alias) → entry

    返回 (full_index, start_index)：
      full_index:  {(filename, alias): entry}          —— 模板 (fn, alias) 直接匹配
      start_index: {filename: [(syl_idx, alias, entry), ...]}
                   —— 用于模板要求 - X 出现在非首音节的情况（按顺序取）
    """
    full_index = {}
    start_index = {}
    forced_index = {}

    for audio_name, item in json_data.items():
        wav_long = item.get('wav_long', [0, 0])
        audio_end_ms = _ms(wav_long[1]) if len(wav_long) >= 2 else None

        syllable_phones = None
        if word_data:
            syllable_phones = _scan_syllable_phones_by_word(
                audio_name, item, word_data, rules, ignore
            )
        if syllable_phones is None:
            syllables = [s.strip() for s in audio_name.split('_') if s.strip()]
            syllables = [s for s in syllables if s in rules]
            phones = item.get('phones', {})
            if not phones or not syllables:
                continue
            sorted_phones = sorted(phones.items(), key=lambda x: int(x[0]))
            actual_phones = [(k, v) for k, v in sorted_phones
                             if v.get('text') not in ignore]
            syllable_phones = _scan_syllable_phones(syllables, actual_phones, rules)
        if not syllable_phones:
            continue

        n_syl = len(syllable_phones)
        cur_fn = f"{audio_name}.wav"
        start_entries = []

        def _put(alias, pd):
            full_index.setdefault((cur_fn, alias), {
                'filename': cur_fn, 'alias': alias, **pd
            })

        def _put_forced(alias, pd):
            """强制索引：不看 _decide_mode，只要 RULE 声明了就按公式算一份"""
            forced_index.setdefault((cur_fn, alias), {
                'filename': cur_fn, 'alias': alias, **pd
            })

        for syl_idx, (syl, rule, plist) in enumerate(syllable_phones):
            seg_len = len(plist)
            cons_p = vowel_p = coda_p = None
            i = 0
            if rule['consonant'] and i < seg_len:
                if plist[i][1].get('text') == rule['consonant']:
                    cons_p = plist[i]; i += 1
            if i < seg_len:
                vowel_p = plist[i]; i += 1
            if i < seg_len:
                coda_p = plist[i]; i += 1
            if vowel_p is None:
                continue

            is_first = syl_idx == 0
            is_last = syl_idx == n_syl - 1

            c_start = _ms(cons_p[1]['xmin']) if cons_p else None
            c_end = _ms(cons_p[1]['xmax']) if cons_p else None
            v_start = _ms(vowel_p[1]['xmin'])
            v_end = _ms(vowel_p[1]['xmax'])
            co_start = _ms(coda_p[1]['xmin']) if coda_p else None
            co_end = _ms(coda_p[1]['xmax']) if coda_p else None
            has_coda = coda_p is not None

            # 元音区
            v_zone_start = v_start
            v_zone_end = v_end
            if coda_p is not None:
                v_zone_end = _ms(coda_p[1]['xmax'])

            is_2seg, is_3seg, is_4seg, has_mediant, _ = _decide_mode(
                rule, seg_len, trans_mode, has_coda
            )

            # ── 每个音节的起始音别名（用于模板 - X 出现在非首音节）──
            if rule['consonant'] and c_start is not None:
                start_alias = f"- {rule['consonant']}"
                start_pd = _calc_initial_consonant(c_start, c_end, P)
            elif not rule['consonant']:
                start_alias = f"- {rule['onset']}"
                start_pd = _calc_onset_pure_vowel(v_start, v_end, True, P)
            else:
                # 有辅音但段没切出：用 onset 公式 + 元音起点兜底
                start_alias = f"- {rule['onset']}"
                if is_4seg or has_mediant:
                    start_pd = _calc_onset_with_mediant(c_start, v_start, v_end, P)
                else:
                    start_pd = _calc_onset_no_mediant(c_start, v_start, v_end, P)

            start_entries.append((syl_idx, start_alias, {
                'filename': cur_fn, 'alias': start_alias, **start_pd
            }))

            if is_first:
                _put(start_alias, start_pd)
            else:
                # 非首音节：加 #idx 后缀，避免和首音节冲突
                _put(f"{start_alias}#{syl_idx}", start_pd)

            # ── 非开头整音 ──
            if not is_first:
                if rule['consonant']:
                    if is_4seg or has_mediant:
                        _put(rule['onset'],
                             _calc_onset_with_mediant(c_start, v_start, v_end, P))
                    else:
                        _put(rule['onset'],
                             _calc_onset_no_mediant(c_start, v_start, v_end, P))
                else:
                    _put(rule['onset'],
                         _calc_onset_pure_vowel(v_start, v_end, False, P))

            # ── 字内衔接 ──
            if is_2seg:
                pass
            elif is_3seg:
                if len(rule['transitions']) >= 1:
                    _put(rule['transitions'][0],
                         _calc_trans_b(v_zone_start, v_zone_end, None, None, P))
            elif is_4seg:
                if len(rule['transitions']) >= 1:
                    _put(rule['transitions'][0],
                         _calc_trans_a(v_zone_start, v_zone_end, None, P))
                if len(rule['transitions']) >= 2:
                    _put(rule['transitions'][1],
                         _calc_trans_b(v_zone_start, v_zone_end, None, None, P))

            # ── 字内衔接（强制产出）：不看 _decide_mode ──
            n_trans = len(rule['transitions'])
            if n_trans >= 1:
                if has_mediant:
                    _put_forced(rule['transitions'][0],
                                _calc_trans_a(v_zone_start, v_zone_end, None, P))
                else:
                    _put_forced(rule['transitions'][0],
                                _calc_trans_b(v_zone_start, v_zone_end, None, None, P))
                if n_trans >= 2:
                    _put_forced(rule['transitions'][1],
                                _calc_trans_b(v_zone_start, v_zone_end, None, None, P))
                    
            # ── coda R ──
            if is_last:
                alias = f"{rule['coda']} R" if rule['coda'] else f"{rule['onset']} R"
                _put(alias, _calc_coda_r(v_start, v_end, co_start, co_end,
                                          audio_end_ms, P))

            # ── 跨音节 ──
            if not is_last:
                next_syl, next_rule, next_plist = syllable_phones[syl_idx + 1]
                nseg_len = len(next_plist)
                next_cons_p = next_vowel_p = None
                ni = 0
                if next_rule['consonant'] and ni < nseg_len:
                    if next_plist[ni][1].get('text') == next_rule['consonant']:
                        next_cons_p = next_plist[ni]; ni += 1
                if ni < nseg_len:
                    next_vowel_p = next_plist[ni]
                if next_vowel_p is None:
                    continue

                nv_start = _ms(next_vowel_p[1]['xmin'])
                nv_end = _ms(next_vowel_p[1]['xmax'])

                if next_cons_p is not None:
                    nc_start = _ms(next_cons_p[1]['xmin'])
                    nc_end = _ms(next_cons_p[1]['xmax'])
                else:
                    #  兜底：从 word_phone 的 middle 点估算辅音位置
                    nc_start, nc_end = _fallback_consonant_range(
                        next_syl, word_data, audio_name, nv_start
                    )

                front = rule['coda'] if rule['coda'] else rule['onset']

                # cV：仅传统模式产
                if (not ncv_enabled) and next_rule['consonant']:
                    _put(f"{front} {next_rule['consonant']}",
                         _calc_cV(v_start, v_end, co_start, co_end,
                                  nc_start, nc_end, P))

                # cO：NCV 无条件产；传统模式仅下一音节无辅音时产
                if ncv_enabled or (not next_rule['consonant']):
                    _put(f"{front} {next_rule['onset']}",
                         _calc_cO(v_start, v_end, co_start, co_end,
                                  nv_start, nv_end, P))

                # cO（强制产出）：下一音节有辅音时也产一份，auto 兜底用
                if next_rule['consonant']:
                    _put_forced(f"{front} {next_rule['onset']}",
                                _calc_cO(v_start, v_end, co_start, co_end,
                                         nv_start, nv_end, P))

        start_index[cur_fn] = start_entries

    return full_index, start_index, forced_index

def apply_template_with_offset(entries, template_path, json_data, rules,
                                ignore, first_sound, params, full_index, start_index,
                                forced_index=None, use_forced=False):
    """模板作为白名单 + 顺序。

    - 优先从 full_index 精确匹配
    - 对 - X 别名（非首音节情况）：从 start_index 按 filename 顺序取未使用的
    """
    if not template_path or not os.path.exists(template_path):
        return entries, []
    template = load_template_oto(template_path)
    if not template:
        return entries, []

    start_used = {fn: [False] * len(lst) for fn, lst in start_index.items()}

    result = []
    missing = []
    for (fn, alias), t in template.items():
        if not _keep_alias(alias, first_sound, rules):
            continue

        # 精确匹配：full_index（生成侧正常产出，最优先）
        e = full_index.get((fn, alias))
        if e is not None:
            result.append(dict(e))
            continue

        # start_index：专用于 - X 出现在非首音节的情况
        if alias.startswith('- ') and fn in start_index:
            matched = False
            for idx, (syl_idx, sa, se) in enumerate(start_index[fn]):
                if start_used[fn][idx]:
                    continue
                if sa == alias:
                    result.append(dict(se))
                    start_used[fn][idx] = True
                    matched = True
                    break
            if matched:
                continue

        # forced_index：当前音频按公式强制算一份（时间戳正确，不会错位）
        # 仅 auto 模式启用
        if use_forced and forced_index is not None:
            fe = forced_index.get((fn, alias))
            if fe is not None:
                result.append(dict(fe))
                continue

        # 都没找到 → 记 missing
        missing.append((fn, alias))

    return result, missing

def write_oto(path, entries):
    with open(path, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(
                f"{e['filename']}={e['alias']},{e['offset']},"
                f"{e['consonant']},{e['cutoff']},{e['preutterance']},{e['overlap']}\n"
            )


# ============================================================
# 入口
# ============================================================
def run(rule_path, json_folder, first_sound='consonant', ignore=None,
        max_cv_aliases=0, max_vc_aliases=0, ensure_all_audio=False,
        keep_isolated_vowel=False, params=None, alias_strategy='replace',
        trans_mode='auto', sort_mode='natural', template_path=None,
        ncv_enabled=False, tmpl_sort='template', tmpl_align='auto'):
    rules = parse_rule_file(rule_path)
    json_path = _find_json_path(json_folder)
    if json_path is None:
        raise FileNotFoundError(
            f"未在 {json_folder}/json/ 下找到 ds_phone_filter.json 或 ds_phone.json"
        )
    data = read_word_phone_json(json_path)

    # 额外加载 word_phone.json
    word_json_path = os.path.join(json_folder, 'json', 'word_phone.json')
    word_data = (read_word_phone_json(word_json_path)
                 if os.path.exists(word_json_path) else {})

    if ignore is None:
        ignore = {'R', 'SP', 'AP', 'sil', 'pau', 'EP'}

    if template_path and os.path.exists(template_path):
        ensure_all_audio = False   # 有模板时关闭兜底

    # ── 生成（注意：generate_oto 现在返回 3 值）──
    entries, warnings, infos, full_index = generate_oto(
        data, rules, word_data=word_data, first_sound=first_sound, ignore=ignore,
        max_cv_aliases=max_cv_aliases, max_vc_aliases=max_vc_aliases,
        ensure_all_audio=ensure_all_audio,
        keep_isolated_vowel=keep_isolated_vowel,
        params=params, alias_strategy=alias_strategy, trans_mode=trans_mode,
        ncv_enabled=ncv_enabled,
    )

    has_template = bool(template_path and os.path.exists(template_path))

    #  关键：无条件构建全量索引。generate_oto 产的优先，其余从 _build_full_index 补。
    P_full = _parse_params(params)
    full_index_extra, start_index, forced_index = _build_full_index(
        data, word_data, rules, P_full,
        first_sound=first_sound, trans_mode=trans_mode, ignore=ignore,
        keep_isolated_vowel=keep_isolated_vowel,
        ncv_enabled=ncv_enabled,
    )
    for k, v in full_index_extra.items():
        full_index.setdefault(k, v)

    if has_template:
        entries, missing_in_template = apply_template_with_offset(
            entries, template_path, data, rules, ignore, first_sound,
            params, full_index, start_index,
            forced_index=forced_index,
            use_forced=(tmpl_align == 'auto'),
        )
    else:
        P_bootstrap = _parse_params(params)
        _bootstrap_missing_aliases(
            entries, data, word_data, rules, P_bootstrap,
            first_sound=first_sound, trans_mode=trans_mode, ignore=ignore,
            keep_isolated_vowel=keep_isolated_vowel,
            ncv_enabled=ncv_enabled,
        )
        missing_in_template = []

    # ── 警告去重（原样）──
    seen = set()
    deduped = []
    for w in warnings:
        if w in seen:
            continue
        seen.add(w)
        deduped.append(w)
    warnings = deduped

    # ── 覆盖检查 ──
    # 无模板时才报"缺失"；模板模式下缺失信息由 missing_in_template 承担
    if has_template:
        missing_aliases = []
    else:
        missing_aliases = check_coverage(
            entries, data, rules, first_sound, keep_isolated_vowel
        )

    # ── 排序 ──
    template_order = None
    if has_template and tmpl_sort == 'template':
        # 从模板按原顺序提取 (fn, alias)
        tmpl = load_template_oto(template_path)
        template_order = list(tmpl.keys())
        entries = sort_oto_entries(entries, 'template', rules,
                                    template_order=template_order)
    else:
        entries = sort_oto_entries(entries, sort_mode, rules)

    # ── 去重 ──
    if has_template:
        # 模板已保证 (fn, alias) 唯一，不跑 remove_redundant
        removed_count = 0
    else:
        before = len(entries)
        entries = remove_redundant(entries)
        removed_count = before - len(entries)

    # ── 报告 ──
    report = {
        'bootstrap_details': [],
        'unresolved': [],
        'unresolved_template': missing_in_template,
        'infos': infos,    # ← 新增
    }

    write_oto(os.path.join(json_folder, 'oto.ini'), entries)

    return len(entries), warnings, missing_aliases, removed_count, report