from collections import defaultdict


def aggregate_by_element(onet_items: list, min_score: float = 55) -> set:
    grouped = defaultdict(list)
    for item in onet_items:
        name = item.get("Element Name", "").lower()
        score = item.get("normalized_score")
        if name and score is not None:
            grouped[name].append(float(score))
    return {
        name for name, scores in grouped.items()
        if sum(scores) / len(scores) >= min_score
    }


def fuzzy_match_onet(onet_skill: str, cv_skills: set, cv_text_lower: str, onet_to_terms: dict) -> bool:
    # 1. Прямое вхождение
    if any(onet_skill in cv_s or cv_s in onet_skill for cv_s in cv_skills):
        return True
    # 2. Через динамический маппинг
    for term in onet_to_terms.get(onet_skill, []):
        if term in cv_text_lower:
            return True
    # 3. Первое слово (длиннее 4 букв)
    first_word = onet_skill.split()[0]
    if len(first_word) > 4 and any(first_word in cv_s for cv_s in cv_skills):
        return True
    return False


def score_summary(facts: dict) -> dict:
    score = 0
    details = []

    if facts.get("has_summary"):
        score += 30
        details.append("✓ Summary section present (+30)")
    else:
        details.append("✗ Summary section missing")

    if facts.get("years_experience", 0) >= 2:
        if facts.get("summary_has_achievements"):
            score += 50
            details.append("✓ Contains achievements (required for 2+ yrs exp) (+50)")
        else:
            details.append("✗ Missing achievements in summary (required for 2+ yrs exp)")
    else:
        score += 30
        details.append("~ Career objective acceptable for <2 yrs exp (+30)")

    if facts.get("has_summary"):
        score += 20
        details.append("✓ Summary quality base score (+20)")

    return {"score": min(score, 100), "details": details}


def score_experience(facts: dict, benchmarks: str) -> dict:
    score = 0
    details = []

    if facts.get("experience_is_chronological"):
        score += 25
        details.append("✓ Chronological order (+25)")
    else:
        details.append("✗ Not chronological")

    if facts.get("experience_has_dates"):
        score += 25
        details.append("✓ Dates present (+25)")
    else:
        details.append("✗ Missing dates")

    metrics_count = facts.get("experience_metrics_count", 0)
    if metrics_count >= 5:
        score += 35
        details.append(f"✓ Good use of metrics: {metrics_count} numbers/% found (+35)")
    elif metrics_count >= 2:
        score += 20
        details.append(f"~ Some metrics present: {metrics_count} (+20)")
    else:
        details.append(f"✗ Not enough quantifiable metrics: only {metrics_count} found")

    score += 15
    details.append(f"O*NET benchmark: {benchmarks[:200]}...")

    return {"score": min(score, 100), "details": details}


def score_hard_skills(facts: dict, onet_data: dict, ats_list: list,
                      cv_text: str = "", onet_to_terms: dict = {}) -> dict:
    score = 0
    details = []
    cv_skills = set(s.lower() for s in facts.get("hard_skills_list", []))
    cv_text_lower = cv_text.lower()

    # 1. Покрытие O*NET skills + knowledge
    top_onet_skills = aggregate_by_element(onet_data.get("skills", []), min_score=60)
    top_onet_skills |= aggregate_by_element(onet_data.get("knowledge", []), min_score=60)

    if top_onet_skills:
        matched = sum(
            1 for skill in top_onet_skills
            if fuzzy_match_onet(skill, cv_skills, cv_text_lower, onet_to_terms)
        )
        coverage = matched / len(top_onet_skills)
        skill_score = round(coverage * 60)
        score += skill_score
        details.append(f"✓ O*NET skills coverage: {matched}/{len(top_onet_skills)} (+{skill_score})")

        missing = [s for s in top_onet_skills
                   if not fuzzy_match_onet(s, cv_skills, cv_text_lower, onet_to_terms)]
        if missing:
            details.append(f"  Missing O*NET skills: {missing[:5]}")

    # 2. ATS keywords
    ats_set = set(k.lower() for k in ats_list)
    ats_matched = sum(1 for kw in ats_set if kw in cv_text_lower)
    if ats_matched >= 7:
        score += 25
        details.append(f"✓ ATS keywords: {ats_matched} matched (+25)")
    elif ats_matched >= 4:
        score += 15
        details.append(f"~ ATS keywords: {ats_matched} matched (+15)")
    else:
        details.append(f"✗ ATS keywords: only {ats_matched} matched")

    # 3. Hot tech бонус
    tech_hot = [t for t in onet_data.get("tech_skills", []) if t.get("Hot Technology") == "Y"]
    hot_matched = sum(1 for t in tech_hot if t.get("Example", "").lower() in cv_text_lower)
    if hot_matched > 0:
        bonus = min(hot_matched * 5, 15)
        score += bonus
        details.append(f"✓ Hot technologies matched: {hot_matched} (+{bonus})")

    return {"score": min(score, 100), "details": details}


def score_soft_skills(facts: dict, onet_data: dict) -> dict:
    score = 0
    details = []
    cv_soft = set(s.lower() for s in facts.get("soft_skills_list", []))

    # Если soft skills не найдены в CV — не штрафуем, просто 0 бонус
    if not cv_soft:
        details.append("~ No explicit soft skills section found (not penalized)")
        return {"score": 0, "details": details}

    onet_soft = aggregate_by_element(onet_data.get("abilities", []), min_score=55)
    onet_soft |= aggregate_by_element(onet_data.get("work_styles", []), min_score=55)

    if onet_soft:
        matched = sum(
            1 for skill in onet_soft
            if any(skill in cv_s or cv_s in skill for cv_s in cv_soft)
        )
        coverage = matched / len(onet_soft)
        soft_score = round(coverage * 80)
        score += soft_score
        details.append(f"✓ Soft skills coverage: {matched}/{len(onet_soft)} (+{soft_score})")
    
    score += 20
    details.append(f"✓ Soft skills present: {len(cv_soft)} skills (+20)")

    return {"score": min(score, 100), "details": details}

def score_additional(facts: dict) -> dict:
    score = 0
    details = []

    if facts.get("has_portfolio"):
        score += 25
        details.append("✓ Portfolio present (+25)")

    if facts.get("has_achievements_section"):
        if facts.get("achievements_are_quantified"):
            score += 30
            details.append("✓ Quantified achievements (+30)")
        else:
            score += 15
            details.append("~ Achievements present but not quantified (+15)")

    langs = facts.get("languages", [])
    valid_langs = [l for l in langs if l.get("level", "").upper() != "A1"]
    if valid_langs:
        score += 20
        details.append(f"✓ Languages: {[l['lang'] for l in valid_langs]} (+20)")

    certs = facts.get("certifications", [])
    if certs:
        bonus = min(len(certs) * 10, 25)
        score += bonus
        details.append(f"✓ Certifications: {len(certs)} found (+{bonus})")

    return {"score": min(score, 100), "details": details}


def compute_overall(scores: dict) -> int:
    base = (
        scores["summary"]    * 0.15 +
        scores["experience"] * 0.40 +
        scores["hard_skills"] * 0.45
    )
    # additional и soft_skills только бонус, не штрафуют
    additional_bonus = scores.get("additional", 0) * 0.05
    soft_bonus = scores.get("soft_skills", 0) * 0.05
    
    return min(round(base + additional_bonus + soft_bonus), 100)