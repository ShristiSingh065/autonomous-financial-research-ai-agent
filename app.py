import streamlit as st
from backend import generate_research_report
st.set_page_config(
    page_title="Autonomous Financial Research Agent",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Autonomous Financial Research Agent")
st.markdown(
    """
    An Agentic AI system that autonomously plans, researches,
    synthesizes evidence from multiple sources, and generates
    professional research reports.
    """
)

query = st.text_input(
    "Enter a research topic:",
    placeholder="Example: Impact of AI on Financial Markets"
)

if st.button("🚀 Run Research"):

    if query.strip() == "":
        st.warning("Please enter a research topic.")
    else:

        with st.spinner("Planner Agent working..."):
            pass

        with st.spinner("Running ReAct reasoning..."):
            pass

        with st.spinner("Collecting research data..."):
            report = generate_research_report(query)

        st.success("Research completed!")

        st.subheader("📄 Final Research Report")

        st.markdown(report)

        st.download_button(
            label="⬇ Download Report",
            data=report,
            file_name="research_report.txt",
            mime="text/plain"
        )