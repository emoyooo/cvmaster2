from openai import OpenAI
from .config import OPENAI_API_KEY, EMBEDDING_MODEL, LLM_MODEL
import json
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_embedding(text: str):
    if not text: return None
    return client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL).data[0].embedding

def extract_target_job(cv_text: str):
    """ИИ определяет целевую или текущую профессию из текста CV"""
    prompt = f"Based on this CV text, identify the most likely target job title (just the title, 2-4 words): \n\n{cv_text[:2000]}"
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    return response.choices[0].message.content.strip()

def stream_llm_response(prompt: str):
    return client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": "You are a professional HR auditor."},
                  {"role": "user", "content": prompt}],
        stream=True
    )

def enrich_job_description(cv_text: str, job_title: str) -> str:
    """LLM генерирует развёрнутое описание профессии на основе CV"""
    prompt = f"""Based on this CV, the person works as: {job_title}

Describe this specific role in 3-5 sentences covering:
- Main responsibilities and daily tasks
- Key tools, technologies, methodologies used  
- Domain/industry context
- Type of outputs/deliverables

CV excerpt:
{cv_text[:3000]}

Return ONLY the description, no preamble."""
    
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    return response.choices[0].message.content.strip()

def extract_cv_facts(cv_text: str, years_experience: int = 0) -> dict:
    """LLM читает CV и возвращает только факты — без оценок"""
    prompt = f"""Read this CV and extract facts. Return ONLY valid JSON, no preamble. Note: hard_skills include anything under "Technical Skills", "Skills", "Tools", "Technologies", "Methods", "Languages" sections.

CV:
{cv_text[:4000]}

Return this exact JSON structure:
{{
  "has_contact_info": true/false,
  "has_summary": "true if CV has ANY of: Summary, About Me, Profile, Objective, Professional Summary sections",
  "summary_has_achievements": "true if that section mentions specific results, numbers, or accomplishments",
  "years_experience": number,
  "experience_is_chronological": true/false,
  "experience_has_dates": true/false,
  "experience_metrics_count": number (count of %, $, numbers in experience),
  "hard_skills_list": ["ALL technical skills, tools, languages, frameworks, methods, technologies found anywhere in CV. Include items from sections named: Technical Skills, Skills, Tools, Technologies, Methods, Languages, Abilities"],
  "soft_skills_list": ["soft/interpersonal skills only: communication, leadership, teamwork, problem-solving, adaptability etc. May be empty if CV has no explicit soft skills"],
  "has_portfolio": true/false,
  "has_achievements_section": true/false,
  "achievements_are_quantified": true/false,
  "languages": [{{"lang": "English", "level": "C1"}}, ...],
  "certifications": ["cert1", "cert2", ...],
  "education_level": "bachelor/master/phd/none"
}}"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    text = response.choices[0].message.content.strip()
    # Убираем markdown если есть
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def build_onet_to_terms(onet_skills: set, job_title: str) -> dict:
    """Динамически генерирует маппинг для конкретной профессии"""
    prompt = f"""For the job "{job_title}", map each abstract O*NET skill category to specific real-world tools/terms a candidate would write in their CV.

O*NET categories: {list(onet_skills)}

Return ONLY valid JSON, no preamble:
{{
  "programming": ["python", "sql", "r"],
  "mathematics": ["statistics", "regression"],
  ...
}}

Rules:
- Only map categories from the list above
- Terms must be specific (tools, technologies, methods) not abstract
- 3-7 terms per category"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    text = response.choices[0].message.content.strip().replace("```json","").replace("```","")
    try:
        return json.loads(text)
    except:
        return {}
    
