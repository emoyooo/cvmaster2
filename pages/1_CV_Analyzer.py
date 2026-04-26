import streamlit as st
import pandas as pd
import json
from utils.db import (
    search_occupations, get_normalized_metrics,
    get_job_benchmarks, get_everything_else, search_ats_keywords, rerank_occupations
)
from utils.ai import (generate_embedding, extract_target_job,
                       stream_llm_response, enrich_job_description, 
                       extract_cv_facts, build_onet_to_terms)
from utils.scoring import (score_summary, score_experience, score_hard_skills,
                            score_soft_skills, score_additional, compute_overall,
                            aggregate_by_element)

st.set_page_config(page_title="Professional CV Analysis", layout="wide")
st.title("CV Content & Structure Audit")

if not st.session_state.get("cv_text"):
    st.warning("Please upload your CV on the Home page first.")
    if st.button("Go to Home"):
        st.switch_page("app.py")
    st.stop()

if "analysis_raw" not in st.session_state:

        # 1. Определяем профессию
        job_title = extract_target_job(st.session_state.cv_text)
        enriched_description = enrich_job_description(st.session_state.cv_text, job_title)
        enriched_embedding = generate_embedding(f"{job_title}. {enriched_description}")
        job_candidates = search_occupations(enriched_embedding, count=5)
        if not job_candidates:
            st.error("Could not find matching occupation.")
            st.stop()
        best_match = rerank_occupations(st.session_state.cv_text, job_title, job_candidates)
        onet_code = best_match['O*NET-SOC Code']
        st.session_state['detected_job'] = best_match['Title']

        # 2. Собираем O*NET данные
        metric_tables = ["skills", "knowledge", "abilities", "work_styles", "work_activities"]
        metrics_context = {}
        for table in metric_tables:
            metrics_context[table] = get_normalized_metrics(table, onet_code)

        benchmarks = get_job_benchmarks(onet_code)
        other_data = get_everything_else(onet_code)
        ats_keywords = search_ats_keywords(generate_embedding(st.session_state.cv_text))
        ats_list = [k['keyword'] for k in ats_keywords]

        # 3. Извлекаем факты из CV через LLM
        cv_facts = extract_cv_facts(st.session_state.cv_text)
        st.write(cv_facts)
        # 4. Строим динамический маппинг O*NET → термины для этой профессии
        top_onet_skills = aggregate_by_element(metrics_context.get("skills", []), min_score=60)
        top_onet_skills |= aggregate_by_element(metrics_context.get("knowledge", []), min_score=60)
        onet_to_terms = build_onet_to_terms(top_onet_skills, st.session_state['detected_job'])
        st.write("onet_to_terms:", onet_to_terms)
        st.write("top_onet_skills:", top_onet_skills)
        st.write("metrics skills count:", len(metrics_context.get("skills", [])))
        st.write("sample:", metrics_context.get("skills", [])[:2])
        st.write("soft_skills:", cv_facts.get("soft_skills_list"))
        st.write("ats_list sample:", ats_list[:5])
        # 5. Считаем scores в Python
        s_summary    = score_summary(cv_facts)
        s_experience = score_experience(cv_facts, benchmarks)
        s_hard       = score_hard_skills(cv_facts, metrics_context, ats_list,
                                          cv_text=st.session_state.cv_text,
                                          onet_to_terms=onet_to_terms)
        s_soft       = score_soft_skills(cv_facts, metrics_context)
        s_additional = score_additional(cv_facts)

        scores = {
            "summary":     s_summary["score"],
            "experience":  s_experience["score"],
            "hard_skills": s_hard["score"],
            "soft_skills": s_soft["score"],
            "additional":  s_additional["score"],
        }
        overall = compute_overall(scores)

        st.session_state["cv_scores"] = scores
        st.session_state["cv_score_details"] = {
            "summary":     s_summary["details"],
            "experience":  s_experience["details"],
            "hard_skills": s_hard["details"],
            "soft_skills": s_soft["details"],
            "additional":  s_additional["details"],
}
        st.session_state["overall_score"] = overall
        st.session_state["cv_facts"] = cv_facts

        # 6. LLM пишет только текстовый анализ
        prompt = f"""
You are an HR Auditor. Write qualitative feedback based on this pre-computed analysis.
DO NOT invent scores — scores are already calculated by the system.

Occupation: {st.session_state['detected_job']}

CANDIDATE CV:
{st.session_state.cv_text[:3000]}

PRE-COMPUTED SECTION SCORES:
- Summary: {scores['summary']}% | Details: {s_summary['details']}
- Experience: {scores['experience']}% | Details: {s_experience['details']}
- Hard Skills: {scores['hard_skills']}% | Details: {s_hard['details']}
- Soft Skills: {scores['soft_skills']}% | Details: {s_soft['details']}
- Additional: {scores['additional']}% | Details: {s_additional['details']}

O*NET CONTEXT:
- CORE TASKS: {other_data['tasks'][:1000]}
- MISSING ATS KEYWORDS: {[k for k in ats_list if k.lower() not in st.session_state.cv_text.lower()][:15]}

Write in Markdown:
1. For each section: what's good, what's missing, specific rewrite suggestions
2. List missing ATS keywords
3. Informal → professional language replacements
4. Do NOT mention any scores or numbers — just qualitative feedback
"""
        full_response = ""
        for chunk in stream_llm_response(prompt):
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content

        st.session_state["analysis_raw"] = full_response

# --- ОТОБРАЖЕНИЕ ---
if "cv_scores" in st.session_state:
    scores  = st.session_state["cv_scores"]
    overall = st.session_state["overall_score"]
    details = st.session_state["cv_score_details"]

    st.header(f"Report for: {st.session_state.get('detected_job')}")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Overall Success Rate", f"{overall}%")
        st.progress(overall / 100)
        core_sections = ["summary", "experience", "hard_skills"]
        weak = [k for k, v in scores.items() if v < 70 and k in core_sections]
        if weak:
            st.error(f"⚠️ Weak: {', '.join(weak)}")

    with col2:
        scores_display = {
            "summary":     scores["summary"],
            "experience":  scores["experience"],
            "hard skills": scores["hard_skills"],
            "additional":  scores["additional"],
        }
        if scores.get("soft_skills", 0) > 0:
            scores_display["soft skills (bonus)"] = scores["soft_skills"]
        chart_data = pd.DataFrame({
            'Section': list(scores_display.keys()),
            'Score (%)': list(scores_display.values())
        })
        st.bar_chart(chart_data, x='Section', y='Score (%)', color="#29b5e8")

    with st.expander("📊 Score Breakdown"):
        for section, detail_list in details.items():
            section_score = scores.get(section, "—")
            score_label = f"{section_score}%" if isinstance(section_score, int) else section_score
            st.markdown(f"**{section.replace('_', ' ').title()} — {score_label}**")
            for d in detail_list:
                st.markdown(f"  {d}")

    st.divider()
    st.markdown(st.session_state["analysis_raw"])

    st.divider()
    if st.button("Prepare for Interview"):
        st.switch_page("pages/2_Interview_Preparation.py")