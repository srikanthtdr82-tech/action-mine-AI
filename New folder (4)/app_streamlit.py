"""
app_streamlit.py
Streamlit Alternative Interface for AI Meeting Action-Item Extractor.
Run with: streamlit run app_streamlit.py
"""

import sys
import json
from pathlib import Path
from datetime import date
import pandas as pd
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extractor import extract_action_items_from_text
from src.evaluator import evaluate_predictions

st.set_page_config(
    page_title="AI Meeting Action-Item Extractor",
    page_icon="📋",
    layout="wide"
)

st.title("📋 AI Meeting Action-Item Extractor")
st.markdown(
    "**Constraint:** *The Zero-Guessing Rule is strictly enforced. "
    "If an owner or deadline is missing or unclear, it is flagged as **Needs review** rather than guessed.*"
)

# Load Sample Transcripts
samples_file = PROJECT_ROOT / "data" / "sample_transcripts.json"
samples_data = []
if samples_file.exists():
    with open(samples_file, "r", encoding="utf-8") as f:
        samples_data = json.load(f)

# Sidebar
st.sidebar.header("⚙️ Configuration")
meeting_date = st.sidebar.date_input("Meeting Reference Date", value=date.today())

sample_names = ["-- Select a Sample --"] + [s["title"] for s in samples_data]
chosen_sample = st.sidebar.selectbox("Load Sample Transcript", sample_names)

initial_text = ""
if chosen_sample != "-- Select a Sample --":
    for s in samples_data:
        if s["title"] == chosen_sample:
            initial_text = s["transcript"]
            break

# Input Area
transcript_text = st.text_area(
    "Meeting Transcript Input:",
    value=initial_text,
    height=200,
    placeholder="Paste meeting transcript here...\nCarlos: I will update the API authentication documentation by tomorrow at 3 PM.\nPriya: We really need to redesign the user onboarding illustrations before the marketing push next Friday."
)

col_btn, _ = st.columns([1, 4])
with col_btn:
    extract_clicked = st.button("🚀 Extract Action Items", type="primary", use_container_width=True)

if extract_clicked and transcript_text.strip():
    with st.spinner("Parsing dialogue turns and enforcing No-Guessing safety rules..."):
        items = extract_action_items_from_text(transcript_text)
        st.session_state["extracted_items"] = items

if "extracted_items" in st.session_state:
    items = st.session_state["extracted_items"]
    if not items:
        st.info("ℹ️ No action items detected in this transcript.")
    else:
        df = pd.DataFrame(items)

        # Metrics
        m1, m2, m3 = st.columns(3)
        total = len(df)
        confirmed = len(df[df["review_status"] == "Confirmed"])
        needs_review = total - confirmed

        m1.metric("Total Items Found", total)
        m2.metric("✅ Confirmed Items", confirmed)
        m3.metric("⚠️ Needs Review", needs_review)

        st.subheader("Interactive Action Items Table")
        st.caption("You can edit any cell directly (e.g. assigning owners or setting deadlines).")

        edited_df = st.data_editor(
            df,
            column_config={
                "task": st.column_config.TextColumn("Task Description", width="large"),
                "owner": st.column_config.TextColumn("Owner", width="medium"),
                "deadline": st.column_config.TextColumn("Deadline", width="medium"),
                "confidence": st.column_config.TextColumn("Confidence", width="small", disabled=True),
                "review_status": st.column_config.SelectboxColumn(
                    "Review Status",
                    options=["Confirmed", "Needs review"],
                    width="medium"
                ),
                "review_reason": st.column_config.TextColumn("Review Reason", width="medium", disabled=True),
                "source_quote": st.column_config.TextColumn("Source Quote", width="large", disabled=True),
            },
            use_container_width=True,
            num_rows="dynamic"
        )

        # Downloads
        csv_data = edited_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Verified Action Items (CSV)",
            data=csv_data,
            file_name=f"action_items_{meeting_date}.csv",
            mime="text/csv"
        )
