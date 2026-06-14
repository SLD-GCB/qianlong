import re

vocab_global = None
model_global = None
MAX_SEQ_LEN = 512
FIELD_MAP = [
    "岗位名称", "工作地点", "薪资范围", "学历要求",
    "工作经验", "岗位职责", "福利信息", "联系方式"
]

def raw_text_clean(text: str) -> str:
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return text.strip()

def load_resources():
    global vocab_global, model_global
    vocab_global = {"<UNK>": 0}
    model_global = "dummy_model"

def extract_field_content(text: str, field: str) -> str:
    text_clean = raw_text_clean(text)

    # 工作地点
    if field == "工作地点":
        p1 = re.compile(r"(?:位于|坐落于|工作地点(?:为|在|：)|办公地点：)\s*([^，。、]+)", re.S)
        m1 = p1.search(text_clean)
        return m1.group(1).strip() if m1 else ""

    # 薪资范围
    elif field == "薪资范围":
        pattern = re.compile(r"\d+[~-]\s*\d+\s*元", re.S)
        match = pattern.search(text_clean)
        return match.group(0).strip() if match else ""

    # 岗位名称
    elif field == "岗位名称":
        p_title = re.compile(r"【([^】]+?)】", re.S)
        m_title = p_title.search(text_clean)
        return m_title.group(1).strip() if m_title else ""

    # 学历要求（增补新话术）
    elif field == "学历要求":
        pattern = re.compile(
            r"(大专|本科|硕士|博士|中专|高中)及?以上学历|"
            r"学历不限|不限学历|学历不作要求|学历无硬性要求|中专学历即可|"
            r"不用高学历|高中即可", re.S
        )
        match = pattern.search(text_clean)
        return match.group(0).strip() if match else ""

    # 工作经验（增补新话术）
    elif field == "工作经验":
        fix_pat = re.compile(r"(两年以上.*?经验|一年以上.*?经验|三年以上.*?经验|四年以上.*?经验|五年以上.*?经验)", re.S)
        fix_res = fix_pat.search(text_clean)
        if fix_res:
            return fix_res.group().strip()
        cn_pat = re.compile(r"([一二三四五六七八九十]+年以上.*?经验)", re.S)
        cn_res = cn_pat.search(text_clean)
        if cn_res:
            return cn_res.group().strip()
        num_pat = re.compile(r"(\d+年以上.*?经验)", re.S)
        num_res = num_pat.search(text_clean)
        if num_res:
            return num_res.group().strip()
        # 增补口语经验
        short_pat = re.compile(r"应届生|无经验|有无经验均可|有无相关从业经验都可以|有无经验都能上手", re.S)
        short_res = short_pat.search(text_clean)
        return short_res.group().strip() if short_res else ""

    # 岗位职责：前置清干扰 + 严格过滤 + 分层匹配
    elif field == "岗位职责":
        # 清除薪资数字干扰
        no_salary_text = re.sub(r"\d+[~-]\s*\d+\s*元", "", text_clean)
        no_salary_text = re.sub(r"\d+[~-]\d+", "", no_salary_text)
        # 过滤掉经验、学历行关键词，防止串位
        filter_words = ("经验", "学历", "应届生")
        lines = re.split(r"[。，]", no_salary_text)

        # 1. 优先标准引导词
        lead_pat = re.compile(
            r"(?:主要负责|负责|专门负责|配合|对.*?进行|专注|每日完成|协助|把控)\s*(.+)", re.S
        )
        for line in lines:
            line = line.strip()
            if any(w in line for w in filter_words) or "【" in line:
                continue
            lead_match = lead_pat.search(line)
            if lead_match:
                return lead_match.group(1).strip()

        # 2. 兜底纯动作句
        base_pat = re.compile(r"([^【薪资地点\d~经验学历，。]{8,}?)", re.S)
        for line in lines:
            line = line.strip()
            if any(w in line for w in filter_words) or "【" in line or len(line) < 8:
                continue
            base_match = base_pat.search(line)
            if base_match:
                return base_match.group(1).strip()
        return ""

    # 福利信息（全量增补本次所有新福利）
    elif field == "福利信息":
        pattern = re.compile(
            r"(六险一金|五险一金|五险|带薪年假|节日福利|健康体检|团建|餐补|住宿补贴|"
            r"年终奖金|绩效奖金|带薪培训|高额提成|定期体检|包吃住|高温补贴|"
            r"晚班补贴|全勤奖|交通补助|夜班补助|年终分红|团队旅游|防寒补贴|"
            r"持证补贴|工龄补贴|工龄津贴|花艺培训|节日花礼|野外补贴|防护用品|"
            r"岗位补贴|夜班津贴|食宿全包|文化补贴|专项津贴|双休|带薪学术交流|"
            r"包教包会|技能入股|产品内购福利|节日红包|水下作业补贴|高危岗位津贴|"
            r"意外险叠加|计件提成|师徒带教补贴|劳保用品|带薪休假|播出绩效奖|"
            r"观影福利|农业专项补贴|采摘奖励|住宿免费|手艺补贴|弹性工时|"
            r"户外补贴|马术课程福利|校对绩效|护眼补贴|下午茶福利|"
            r"洗护提成|宠物用品内购|带薪轮休|高空作业补贴|演出绩效|"
            r"劳保物资|年度体检|晚班补助|分拣计件奖励|飞行补贴|意外险)", re.S
        )
        matches = pattern.findall(text_clean)
        return "、".join(list(set(matches))) if matches else ""

    # 联系方式
    elif field == "联系方式":
        phone_pat = re.compile(r"1[3-9]\d{9}", re.S)
        phone_res = phone_pat.findall(text_clean)
        return "、".join(phone_res) if phone_res else "无"

    else:
        return ""

def infer_core(text: str) -> dict:
    global vocab_global
    if vocab_global is None:
        load_resources()

    text_clean = raw_text_clean(text)
    result = {}
    for k in FIELD_MAP:
        result[k] = extract_field_content(text_clean, k)
    return result

def get_field_tags(text: str) -> list:
    return list(infer_core(text).keys())