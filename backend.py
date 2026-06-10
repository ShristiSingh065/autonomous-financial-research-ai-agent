from exa_py import Exa
import re
import chromadb
import uuid
import arxiv
import yfinance as yf
from groq import Groq
from newsapi import NewsApiClient
from sec_edgar_downloader import Downloader
from dotenv import load_dotenv
import os

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")

newsapi = NewsApiClient(
    api_key=os.getenv("NEWS_API_KEY")
)
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

exa = Exa(
    api_key=EXA_API_KEY
)
client_db = chromadb.PersistentClient(
    path="./research_memory"
)

collection = client_db.get_or_create_collection(
    name="research"
)
TOOLS = {
    "web_search": None,
    "news_search": None,
    "memory_search": None,
    "company_fundamentals": None,
    "financial_ratios": None,
    "stock_performance": None,
    "sec_edgar": None
}
def paper_search_tool(query):

    search = arxiv.Search(
        query=query,
        max_results=3
    )

    papers = []

    for result in search.results():

        papers.append({
            "title": result.title,
            "summary": result.summary[:500]
        })

    return papers
def news_search_tool(query):
    news = newsapi.get_everything(
        q=query,
        language="en",
        page_size=5
    )

    articles = []

    for article in news["articles"]:

        articles.append({
            "title": article["title"],
            "description": article["description"],
            "url": article["url"]
        })

    return articles

def company_fundamentals_tool(ticker):

    stock = yf.Ticker(ticker)

    info = stock.info

    return {
        "Company": info.get("longName"),
        "Sector": info.get("sector"),
        "Market Cap": info.get("marketCap"),
        "Revenue": info.get("totalRevenue"),
        "Net Income": info.get("netIncomeToCommon"),
        "Employees": info.get("fullTimeEmployees")
    }
def financial_ratios_tool(ticker):

    stock = yf.Ticker(ticker)

    info = stock.info

    return {
        "PE Ratio": info.get("trailingPE"),
        "Forward PE": info.get("forwardPE"),
        "Profit Margin": info.get("profitMargins"),
        "ROE": info.get("returnOnEquity"),
        "Debt To Equity": info.get("debtToEquity")
    }
def stock_performance_tool(ticker):

    stock = yf.Ticker(ticker)

    hist = stock.history(period="6mo")

    return {
        "Current Price": stock.info.get("currentPrice"),
        "52 Week High": stock.info.get("fiftyTwoWeekHigh"),
        "52 Week Low": stock.info.get("fiftyTwoWeekLow")
    }
def web_search_tool(query):
    return exa.search(query, num_results=3)
def memory_search_tool(query):

    try:
        results = collection.query(
            query_texts=[query],
            n_results=3
        )

        return results["documents"]

    except:
        return []
def sec_edgar_tool(ticker):
    try:
        dl = Downloader("sec_data")
        dl.get(
            "10-K",
            ticker,
            limit=1
        )
        return f"Latest 10-K downloaded for {ticker}"
    except Exception as e:

        return str(e)
def ask_llm(prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content
def react_agent(question):

    scratchpad = ""

    for step in range(3):

        prompt = f"""
        You are a ReAct research agent.

        Question:
        {question}

        Previous observations:
        {scratchpad}

        Decide next action.

        Available tools:

        1. WEB_SEARCH
        2. NEWS_SEARCH
        3. MEMORY_SEARCH

        Format:

        THOUGHT:

        ACTION:
        TOOL_NAME | query
        """

        response = ask_llm(prompt)

        print(response)
        action_line = response.split("ACTION:")[-1].strip()
        if "WEB_SEARCH" in action_line:
            query = action_line.split("|")[1].strip()
            results = web_search_tool(query)
            scratchpad += f"\nOBSERVATION:\nSearch completed successfully.\n"
        elif "NEWS_SEARCH" in action_line:
            query = action_line.split("|")[1].strip()
            results = news_search_tool(query)
            scratchpad += f"\nOBSERVATION:\nSearch completed successfully.\n"
        elif "MEMORY_SEARCH" in action_line:
            query = action_line.split("|")[1].strip()
            results = memory_search_tool(query)
            scratchpad += f"\nOBSERVATION:\nSearch completed successfully.\n"
        elif "COMPANY_FUNDAMENTALS" in action_line:
            ticker = action_line.split("|")[1].strip()
            results = company_fundamentals_tool(ticker)
            scratchpad += f"\nOBSERVATION:\n{results}\n"
        elif "FINANCIAL_RATIOS" in action_line:
            ticker = action_line.split("|")[1].strip()
            results = financial_ratios_tool(ticker)
            scratchpad += f"\nOBSERVATION:\n{results}\n"
        elif "STOCK_PERFORMANCE" in action_line:
            ticker = action_line.split("|")[1].strip()
            results = stock_performance_tool(ticker)
            scratchpad += f"\nOBSERVATION:\n{results}\n"
        elif "SEC_EDGAR" in action_line:
            ticker = action_line.split("|")[1].strip()
            results = sec_edgar_tool(ticker)
            scratchpad += f"\nOBSERVATION:\n{results}\n"
    return scratchpad

def generate_research_report(query):
    """
    Main pipeline function.
    Takes a research topic and returns the final report.
    """

    print("\n[PLANNER AGENT WORKING...]\n")

    planner_text = ask_llm(
        f"""
        You are a research planner.

        Create 5 search queries to thoroughly research:

        {query}

        Return only the queries.
        One per line.
        """
    )

    print("\n[REACT AGENT WORKING...]\n")
    react_results = react_agent(query)

    queries = []

    for line in planner_text.split("\n"):
        line = line.strip()

        if not line:
            continue

        line = re.sub(r"^\d+\.\s*", "", line)
        line = line.replace('"', "")

        queries.append(line)

    all_summaries = []

    print("\n[RESEARCH AGENT WORKING...]\n")

    for q in queries:

        print(f"\nSearching: {q}")

        response = exa.search(
            q,
            num_results=1
        )

        for result in response.results:

            article_text = (result.text or "")[:1500]

            researcher = ask_llm(
                f"""
                You are a research analyst.

                Analyze this source.

                Provide:

                1. Main Idea
                2. Key Findings
                3. Important Statistics
                4. Limitations
                5. Short Summary

                Article:

                {article_text}
                """
            )

            all_summaries.append(researcher)

            collection.add(
                documents=[researcher],
                ids=[str(uuid.uuid4())]
            )

    combined_text = "\n\n".join(all_summaries)

    synthesis = ask_llm(
        f"""
        You are a senior research analyst.

        Below are findings from:

        1. Web sources
        2. News sources
        3. Memory sources

        Tasks:

        - Merge overlapping information
        - Identify conflicts
        - Determine most reliable evidence
        - Explain disagreements
        - Produce unified conclusions

        Data:

        REACT FINDINGS:
        {react_results}

        SOURCE SUMMARIES:
        {combined_text}
        """
    )

    critic_notes = ask_llm(
        f"""
        You are a critical reviewer.

        Review the collected research.

        Identify:

        1. Weak evidence
        2. Missing perspectives
        3. Contradictions
        4. Potential bias
        5. Research gaps

        Research:
        {synthesis}
        """
    )

    final_report = ask_llm(
        f"""
        Create a professional research report.

        Topic:
        {query}

        Research Findings:
        {synthesis}

        Critic Review:
        {critic_notes}

        Generate:

        1. Executive Summary

        2. Major Trends

        3. Key Findings

        4. Challenges

        5. Risks and Limitations

        6. Future Outlook

        7. Research Gaps

        8. Conclusion

        Write professionally.
        """
    )

    return final_report

