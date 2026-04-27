import streamlit as st
from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_data
def get_scales_reference():
    res = supabase.table("scales_reference").select("*").execute()
    return {item['Scale ID']: item for item in res.data}

@st.cache_data
def get_category_descriptions():
    res = supabase.table("exp_categories").select("*").execute()
    return {(item['Element ID'], str(item['Category'])): item['Category Description'] for item in res.data}



def search_occupations(cv_embedding, count=1):
    return supabase.rpc("match_occupations", {
        "query_embedding": cv_embedding,
        "match_threshold": 0.3,
        "match_count": count
    }).execute().data

def search_ats_keywords(cv_embedding, count=20):
    return supabase.rpc("match_ats_keywords", {
        "query_embedding": cv_embedding,
        "match_threshold": 0.3,
        "match_count": count
    }).execute().data



def get_raw_table_data(table_name: str, onet_code: str):
    res = supabase.table(table_name).select("*").eq('"O*NET-SOC Code"', onet_code).execute()
    print(f"Table: {table_name}, Code: {onet_code}, Rows: {len(res.data)}")
    return res.data if res.data else []
def get_normalized_metrics(table_name: str, onet_code: str):
    raw_data = get_raw_table_data(table_name, onet_code)
    scales_ref = get_scales_reference()
    
    normalized_results = []
    for row in raw_data:
        scale_id = row.get('Scale ID')
        val = float(row.get('Data Value', 0))
        scale_meta = scales_ref.get(scale_id)
        
        if scale_meta:
            min_v = float(scale_meta['Minimum'])
            max_v = float(scale_meta['Maximum'])
            if max_v != min_v:
                norm_score = ((val - min_v) / (max_v - min_v)) * 100
                row['normalized_score'] = round(norm_score, 2)
            else:
                row['normalized_score'] = 0.0
        else:
            row['normalized_score'] = None
        normalized_results.append(row)
    return normalized_results

def get_job_benchmarks(onet_code: str):
    q_code = '"O*NET-SOC Code"'
    
    res_exp = supabase.table("exp").select("*").eq(q_code, onet_code).execute()
    
    res_cats = supabase.table("exp_categories").select("*").execute()
    
    if not res_exp.data: 
        return "No experience benchmark data available for this role."

    cats_map = {
        (c['Element ID'], str(c['Category'])): c['Category Description'] 
        for c in res_cats.data
    }

    benchmarks = {}
    for item in res_exp.data:
        elem_name = item['Element Name']
        elem_id = item['Element ID']
        cat_id = str(item['Category'])
        
        if elem_name not in benchmarks: 
            benchmarks[elem_name] = []
        
        description = cats_map.get((elem_id, cat_id), f"Category {cat_id}")
        
        benchmarks[elem_name].append({
            "desc": description,
            "pct": float(item.get('Data Value', 0))
        })
    
    output = []
    for name, options in benchmarks.items():
        if options:
            best = max(options, key=lambda x: x['pct'])
            if best['pct'] > 0: 
                output.append(f"- {name}: Target requirement is '{best['desc']}' (Expert Consensus: {best['pct']}% )")
    
    return "\n".join(output) if output else "Benchmarks found but no significant consensus."


def get_everything_else(onet_code: str):
    q_code = '"O*NET-SOC Code"'
    data = {}
    
    data['tasks'] = supabase.table("tasks").select("Task, \"Task Type\"").eq(q_code, onet_code).execute().data
    data['new_tasks'] = supabase.table("new_tasks").select("Task").eq(q_code, onet_code).execute().data
    
    data['tech_skills'] = supabase.table("tech_skills").select("*").eq(q_code, onet_code).execute().data
    
    data['iwa'] = supabase.table("iwa_refs").select("*").execute().data
    
    return data

def rerank_occupations(cv_text: str, job_title: str, candidates: list) -> dict:
    from openai import OpenAI
    from .config import OPENAI_API_KEY, LLM_MODEL
    client_local = OpenAI(api_key=OPENAI_API_KEY)

    candidates_text = "\n".join([
        f"{i+1}. {c['Title']}\n   {c['Description'][:400]}"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""You are an expert career classifier. Read the full CV and pick the single best-matching occupation.

CANDIDATE CV:
{cv_text[:3000]}

CANDIDATE'S STATED TITLE: "{job_title}"

OCCUPATION OPTIONS:
{candidates_text}

Think step by step:
1. What does this person ACTUALLY do day-to-day based on the CV?
2. What tools, methods, outputs are described?
3. Which occupation description matches the ACTUAL WORK, not just the title?

Reply with ONLY the number (1-{len(candidates)}), nothing else."""

    response = client_local.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    try:
        idx = int(response.choices[0].message.content.strip()) - 1
        return candidates[idx]
    except:
        return candidates[0]

