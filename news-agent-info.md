# News Agent
### Purpose:
- Gathers detailed textual and analytical content about companies and markets to complement quantitative analysis.
### Data Sources:
- News APIs (e.g., NewsAPI)
- Web search engines
- Regulatory databases (e.g., SEC filings, MCA)
- Company websites and press rooms
### Capabilities:
- Issues automated search queries for relevant content
- Retrieves articles, press releases, earnings call transcripts, 10-K reports, etc.
- Uses AI-based parsers or knowledge bases to extract structured information
### Workflow:
- Collects and cleans raw textual content
- Forwards unstructured data to the Summarizer Agent for further processing
### Value:
- Keeps the system updated with qualitative insights not reflected in numerical data
- Adds context for interpreting price movements, analyst ratings, and market sentiment
### Sample Input:
- Company ticker symbol (e.g., INFY) or keyword (e.g., "AI regulation India")
### Sample Output:
- Set of relevant news articles, press releases, and filings and mark it if the news is positive or negative.
