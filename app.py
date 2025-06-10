# import streamlit as st
# import pandas as pd
# from risk_taxonomy_poc import (
#     match_risk_category, match_mapped_hazard,
#     match_specific_hazard, match_outcomes_for_specific,
#     rc_to_mh, mh_to_sh, sh_to_outcomes
# )

# st.set_page_config(page_title="Risk Tagging POC")
# st.title("Risk Tagging POC")

# uploaded = st.file_uploader("Upload case CSV/Excel", type=['csv','xlsx'])
# if uploaded:
#     # Load DataFrame depending on extension
#     if uploaded.name.endswith('.csv'):
#         df = pd.read_csv(uploaded)
#     else:
#         df = pd.read_excel(uploaded)
#     st.write("Detected columns:", df.columns.tolist())

#     # Identify which columns correspond to the four text fields by substring matching
#     # You can adjust these substrings if your column names differ
#     keywords = {
#         'Description': ['description'],
#         'Determination': ['determination', 'cause'],  # matches "Determination of Causes..."
#         'Unsafe': ['unsafe conditions'],
#         'Sequence': ['sequence of events']
#     }
#     # Build a dict: field_key -> list of actual cols matching
#     matched_cols = {k: [] for k in keywords}
#     for col in df.columns:
#         low = col.lower()
#         for key, subs in keywords.items():
#             for sub in subs:
#                 if sub.lower() in low:
#                     matched_cols[key].append(col)
#                     break

#     st.write("Mapped text fields (will combine these):")
#     for key, cols in matched_cols.items():
#         st.write(f"- {key}: {cols}")

#     # Helper to combine fields for each row
#     def combine_case_text(row):
#         parts = []
#         for key, cols in matched_cols.items():
#             for col in cols:
#                 if col in row and pd.notna(row[col]):
#                     parts.append(str(row[col]))
#         return "\n".join(parts).strip()

#     tagged = []
#     for idx, row in df.iterrows():
#         st.markdown(f"---\n**Case {idx+1}**")
#         combined_text = combine_case_text(row)
#         if combined_text:
#             st.write(combined_text[:300] + ("..." if len(combined_text)>300 else ""))
#         else:
#             st.write("_No text found in the recognized fields for this row._")

#         # ========= Interactive tagging =========
#         # 1. Risk Category
#         if combined_text:
#             rc_preds = match_risk_category(combined_text, top_k=2)
#         else:
#             rc_preds = []
#         rc_options = [f"{d['risk_category']} (score {d['score']:.2f})" for d in rc_preds]
#         # Extract just labels for selectbox
#         rc_labels = [d['risk_category'] for d in rc_preds]
#         # If fewer than 2 predicted, add others for choice
#         if len(rc_labels) < 2:
#             extras = [rc for rc in rc_to_mh.keys() if rc not in rc_labels]
#             if extras:
#                 rc_labels.append(extras[0])
#                 rc_options.append(f"{extras[0]} (added)")
#         if rc_labels:
#             chosen_rc = st.selectbox(f"Risk Category (row {idx+1})", rc_labels, key=f"rc_{idx}")
#         else:
#             chosen_rc = None
#             st.write("No Risk Category predictions available")

#         # 2. Mapped Hazard
#         if combined_text and chosen_rc:
#             mh_preds = match_mapped_hazard(combined_text, chosen_rc, top_k=2)
#         else:
#             mh_preds = []
#         mh_labels = [d['mapped_hazard'] for d in mh_preds]
#         if len(mh_labels) < 2 and chosen_rc:
#             extras = [mh for mh in rc_to_mh.get(chosen_rc, []) if mh not in mh_labels]
#             if extras:
#                 mh_labels.append(extras[0])
#         if mh_labels:
#             chosen_mh = st.selectbox(f"Mapped Hazard (row {idx+1})", mh_labels, key=f"mh_{idx}")
#         else:
#             chosen_mh = None
#             st.write("No Mapped Hazard predictions available")

#         # 3. Specific Hazard
#         if combined_text and chosen_mh:
#             sh_preds = match_specific_hazard(combined_text, chosen_mh, top_k=2)
#         else:
#             sh_preds = []
#         sh_labels = [d['specific_hazard'] for d in sh_preds]
#         if len(sh_labels) < 2 and chosen_mh:
#             extras = [sh for sh in mh_to_sh.get(chosen_mh, []) if sh not in sh_labels]
#             if extras:
#                 sh_labels.append(extras[0])
#         if sh_labels:
#             chosen_sh = st.selectbox(f"Specific Hazard (row {idx+1})", sh_labels, key=f"sh_{idx}")
#         else:
#             chosen_sh = None
#             st.write("No Specific Hazard predictions available")

#         # 4. Outcomes
#         # If your case data has a column with outcome text you want to auto-match, detect it similarly:
#         outcome_text_cols = [col for col in df.columns if 'outcome' in col.lower()]
#         auto_defaults = []
#         if outcome_text_cols and chosen_sh:
#             # Pick first non-null outcome text column
#             for oc in outcome_text_cols:
#                 if pd.notna(row.get(oc, None)):
#                     case_outcome_text = str(row[oc])
#                     auto = match_outcomes_for_specific(case_outcome_text, chosen_sh, top_k=2, threshold=0.3)
#                     auto_defaults = [d['outcome'] for d in auto]
#                     st.write(f"Auto outcome match from '{oc}': {auto_defaults}")
#                     break
#         # Otherwise default to all taxonomy phrases for chosen_sh
#         if not auto_defaults and chosen_s
# app.py
import streamlit as st
from risk_taxonomy_poc import (
    match_risk_category, match_mapped_hazard,
    match_specific_hazard, match_outcomes_for_specific,
    rc_to_mh, mh_to_sh, sh_to_outcomes
)

st.set_page_config(page_title="Risk Tagging POC")
st.title("🧠 Risk Tagging POC")

st.markdown("Paste in the case details below:")

# 4 Input Fields
desc = st.text_area("📝 Description", height=150)
cause = st.text_area("🔍 Determination of Causes of Incident (EIIR)", height=100)
unsafe = st.text_area("⚠️ Unsafe Conditions that Contributed to the Incident (EIIR)", height=100)
sequence = st.text_area("⏱️ Sequence of Events (EIIR)", height=100)

# Combine inputs
full_text = "\n".join([desc, cause, unsafe, sequence]).strip()

if st.button("🔍 Tag this Case") and full_text:
    # 1. Risk Category
    rc_preds = match_risk_category(full_text, top_k=1)
    chosen_rc = rc_preds[0]['risk_category'] if rc_preds else None
    st.markdown(f"**🧩 Risk Category:** `{chosen_rc}`")

    # 2. Mapped Hazard
    if chosen_rc:
        mh_preds = match_mapped_hazard(full_text, chosen_rc, top_k=1)
        chosen_mh = mh_preds[0]['mapped_hazard'] if mh_preds else None
        st.markdown(f"**🧪 Mapped Hazard:** `{chosen_mh}`")
    else:
        chosen_mh = None

    # 3. Specific Hazard
    if chosen_mh:
        sh_preds = match_specific_hazard(full_text, chosen_mh, top_k=1)
        chosen_sh = sh_preds[0]['specific_hazard'] if sh_preds else None
        st.markdown(f"**🔎 Specific Hazard:** `{chosen_sh}`")
    else:
        chosen_sh = None

    # 4. Outcome Tags
    if chosen_sh:
        outcome_preds = match_outcomes_for_specific(full_text, chosen_sh, top_k=2, threshold=0.3)
        if outcome_preds:
            outcomes = [o['outcome'] for o in outcome_preds]
            st.markdown("**💥 Suggested Outcomes:**")
            for o in outcomes:
                st.write(f"- {o}")
        else:
            st.write("No outcome matches found.")
else:
    st.info("Fill in the fields above and click 'Tag this Case'.")
