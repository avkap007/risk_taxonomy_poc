import pandas as pd
from sentence_transformers import SentenceTransformer, util
import numpy as np

# 1. Load taxonomy
tax_df = pd.read_excel("risk_mapping_poc_enhanced.xlsx", sheet_name="Sheet1")
# or: tax_df = pd.read_csv("risk_mapping_poc.csv")

# 2. Build hierarchical mappings
rc_to_mh = (
    tax_df[['Risk_Category','mapped_hazard']]
    .drop_duplicates()
    .groupby('Risk_Category')['mapped_hazard']
    .apply(list)
    .to_dict()
)
mh_to_sh = (
    tax_df[['mapped_hazard','specific_hazard']]
    .drop_duplicates()
    .groupby('mapped_hazard')['specific_hazard']
    .apply(list)
    .to_dict()
)

# 3. Build specific hazard -> outcome phrases mapping
sh_to_outcomes = {}
for _, row in tax_df.iterrows():
    sh = row['specific_hazard']
    acute = row.get('acute_outcome_description', "")
    chronic = row.get('chronic_outcome_description', "")
    phrases = []
    for desc in [acute, chronic]:
        if pd.notna(desc):
            parts = [p.strip() for p in str(desc).split(',') if p.strip()]
            phrases.extend(parts)
    unique = list(dict.fromkeys(phrases))
    if sh in sh_to_outcomes:
        existing = sh_to_outcomes[sh]
        combined = existing + [p for p in unique if p not in existing]
        sh_to_outcomes[sh] = combined
    else:
        sh_to_outcomes[sh] = unique

# 4. Initialize SBERT model and precompute embeddings for Risk/ MH/ SH labels
model = SentenceTransformer('all-MiniLM-L6-v2')

# 4.1. Risk categories
risk_cats = list(rc_to_mh.keys())
risk_cat_embeddings = model.encode(risk_cats, convert_to_tensor=True)

# 4.2. Mapped hazards
mapped_hazards = list({mh for lst in rc_to_mh.values() for mh in lst})
mh_to_idx = {mh:i for i,mh in enumerate(mapped_hazards)}
mapped_hazard_embeddings = model.encode(mapped_hazards, convert_to_tensor=True)

# 4.3. Specific hazards
specific_hazards = list({sh for lst in mh_to_sh.values() for sh in lst})
sh_to_idx = {sh:i for i,sh in enumerate(specific_hazards)}
specific_hazard_embeddings = model.encode(specific_hazards, convert_to_tensor=True)

# 5. Matching functions (as above)
def match_risk_category(case_text, top_k=2):
    emb = model.encode(case_text, convert_to_tensor=True)
    cos_scores = util.cos_sim(emb, risk_cat_embeddings)[0]
    arr = cos_scores.cpu().numpy()
    top_idxs = np.argpartition(-arr, range(min(top_k, len(arr))))[:top_k]
    results = [{'risk_category': risk_cats[i], 'score': float(arr[i])} for i in top_idxs]
    return sorted(results, key=lambda x: -x['score'])

def match_mapped_hazard(case_text, risk_category, top_k=2):
    emb = model.encode(case_text, convert_to_tensor=True)
    candidates = rc_to_mh.get(risk_category, [])
    idxs = [mh_to_idx[mh] for mh in candidates if mh in mh_to_idx]
    if not idxs:
        return []
    mh_embs = mapped_hazard_embeddings[idxs]
    cos_scores = util.cos_sim(emb, mh_embs)[0]
    arr = cos_scores.cpu().numpy()
    top_local = np.argpartition(-arr, range(min(top_k, len(arr))))[:top_k]
    results = [{'mapped_hazard': candidates[i], 'score': float(arr[i])} for i in top_local]
    return sorted(results, key=lambda x: -x['score'])

def match_specific_hazard(case_text, mapped_hazard, top_k=2):
    emb = model.encode(case_text, convert_to_tensor=True)
    candidates = mh_to_sh.get(mapped_hazard, [])
    idxs = [sh_to_idx[sh] for sh in candidates if sh in sh_to_idx]
    if not idxs:
        return []
    sh_embs = specific_hazard_embeddings[idxs]
    cos_scores = util.cos_sim(emb, sh_embs)[0]
    arr = cos_scores.cpu().numpy()
    top_local = np.argpartition(-arr, range(min(top_k, len(arr))))[:top_k]
    results = [{'specific_hazard': candidates[i], 'score': float(arr[i])} for i in top_local]
    return sorted(results, key=lambda x: -x['score'])

def match_outcomes_for_specific(case_outcome_text, specific_hazard, top_k=2, threshold=0.3):
    """
    If you have a case-level outcome text field, auto-match it to the taxonomy phrases.
    """
    candidates = sh_to_outcomes.get(specific_hazard, [])
    if not candidates:
        return []
    cand_embs = model.encode(candidates, convert_to_tensor=True)
    emb = model.encode(case_outcome_text, convert_to_tensor=True)
    cos_scores = util.cos_sim(emb, cand_embs)[0]
    arr = cos_scores.cpu().numpy()
    sorted_idxs = np.argsort(-arr)
    results = []
    for idx in sorted_idxs[:top_k]:
        score = float(arr[idx])
        if score < threshold and results:
            break
        results.append({'outcome': candidates[idx], 'score': score})
    if not results:
        idx = sorted_idxs[0]
        results.append({'outcome': candidates[idx], 'score': float(arr[idx])})
    return results
