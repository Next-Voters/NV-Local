import httpx
from dotenv import load_dotenv

from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from agents.legislation_finder import legislation_finder_agent
from utils.models import WriterOutput
from utils.typed_dicts import ChainData
from utils.prompts import writer_sys_prompt, note_taker_sys_prompt

load_dotenv()

model = ChatOpenAI(model="gpt-4o-mini")


def run_legislation_finder(inputs: ChainData) -> ChainData:
    """Run the legislation finder agent as a node."""
    city = inputs.get("city", "Unknown")
    agent_result = legislation_finder_agent.invoke({"city": city})
    legislation_sources = agent_result.get("reliable_legislation_sources", [])

    # Debug: print all messages from the agent
    messages = agent_result.get("messages", [])
    print(f"[DEBUG] Agent messages: {len(messages)}")
    for msg in messages[-5:]:  # Last 5 messages
        content = (
            msg.content[:200] if hasattr(msg, "content") and msg.content else str(msg)
        )
        print(f"[DEBUG] {type(msg).__name__}: {content}...")

    print(
        f"[DEBUG] Found {len(legislation_sources)} sources for {city}: {legislation_sources[:3]}..."
    )
    return {**inputs, "legislation_sources": legislation_sources}


def run_content_retrieval(inputs: ChainData) -> ChainData:
    """Fetch content from legislation sources."""
    legislation_sources = inputs.get("legislation_sources", [])
    print(f"[DEBUG] Fetching content from {len(legislation_sources)} sources")
    legislation_content = []

    for source in legislation_sources:
        # Handle both dict and string formats (defensive)
        url = source.get("url") if isinstance(source, dict) else source

        if not url:
            legislation_content.append(f"[Invalid source: {source}]")
            continue

        try:
            markdown_url = f"https://markdown.new/{url}"
            response = httpx.get(markdown_url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            legislation_content.append(response.text)
        except httpx.HTTPError as e:
            print(f"[DEBUG] Failed to fetch {url}: {e}")
            legislation_content.append(f"[Failed to fetch: {url}]")

    print(f"[DEBUG] Content retrieved: {len(legislation_content)} items")
    return {**inputs, "legislation_content": legislation_content}


def research_note_taker(inputs: ChainData) -> ChainData:
    raw_content_list = inputs.get("legislation_content", [])

    if not raw_content_list:
        return {**inputs, "notes": "No legislation content found."}

    raw_content = []

    for content in raw_content_list:
        raw_content.append(content + "\n")

    system_prompt = note_taker_sys_prompt.format(raw_content=raw_content)

    # Applying context compaction to ensure context window for LLM remains within bounds of good performance
    ai_generated_notes = model.invoke(
        [{"role": "system", "content": system_prompt}],
    )

    return {**inputs, "notes": str(ai_generated_notes.content)}


def research_summary_writer(inputs: ChainData) -> ChainData:
    """Generate final output using LLM with structured output."""
    notes = inputs.get("notes")
    print(f"[DEBUG] Notes length: {len(notes) if notes else 0}")

    system_prompt = writer_sys_prompt.format(notes=notes)

    structured_model = model.with_structured_output(WriterOutput)

    ai_generated_summary: WriterOutput = structured_model.invoke(
        [{"role": "system", "content": system_prompt}],
    )

    print(f"[DEBUG] Generated summary: {ai_generated_summary}")

    if ai_generated_summary is None:
        return {**inputs, "legislation_summary": None}

    title_lower = (
        ai_generated_summary.title.lower().strip() if ai_generated_summary.title else ""
    )
    no_title_patterns = ("no content", "no recent", "no legislation", "none", "")
    print(f"[DEBUG] Title: {ai_generated_summary.title}")
    print(f"[DEBUG] Title lower: '{title_lower}'")
    if (
        title_lower in no_title_patterns
        or title_lower.startswith("no ")
        or title_lower.startswith("n/a")
    ):
        print(f"[DEBUG] Filtering out - matched pattern")
        return {**inputs, "legislation_summary": None}

    print(f"[DEBUG] Returning legislation_summary: {ai_generated_summary}")
    return {**inputs, "legislation_summary": ai_generated_summary}


def run_politician_public_statement(inputs: ChainData) -> ChainData:
    """Run the politican public statement finder agent as a node."""
    return {**inputs, "politician_public_statements": []}


def report_formatter(inputs: ChainData) -> ChainData:
    """Format a final report using the legislative summary and the politician public statements."""
    legislation_summary = inputs.get("legislation_summary")
    public_statements = inputs.get("politician_public_statements")

    print(f"[DEBUG] report_formatter received: {legislation_summary}")

    if legislation_summary is None:
        return {
            **inputs,
            "markdown_report": "# No Legislation Found\n\nNo recent legislation was found for the specified city. Try a different city or check back later for updates.",
        }

    lines = [
        f"# {legislation_summary.title}",
        "",
        "## Summary",
        "",
        legislation_summary.summary,
        "",
        "## Full Report",
        "",
        legislation_summary.body,
        "",
        "---",
        "",
        "## Politician Public Statements",
        "",
    ]

    for politician in public_statements:
        lines.append(f"### {politician['name']}")
        lines.append("")
        for statement in politician["statement_summaries"]:
            lines.append(f"**Legislation Source Link:** {statement['source']}")
            lines.append("")
            lines.append(statement["summary"])
            lines.append("")

    markdown_report = "\n".join(lines)

    return {**inputs, "markdown_report": markdown_report}


chain = (
    RunnableLambda(run_legislation_finder)
    | RunnableLambda(run_content_retrieval)
    | RunnableLambda(research_note_taker)
    | RunnableLambda(research_summary_writer)
    | RunnableLambda(run_politician_public_statement)
    | RunnableLambda(report_formatter)
)


if __name__ == "__main__":
    city = str(input("What city would you like to find legislation in? "))

    result = chain.invoke({"city": city})

    print("\n=== NV Local Results ===\n")
    report = result.get("markdown_report")
    print(report)
