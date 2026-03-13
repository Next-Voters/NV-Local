import operator

from typing import Annotated

from utils.agents import BaseAgentState, BaseReActAgent
from utils.prompts import scraper_builder_sys_prompt
from tools.scraper_builder import code_generator, python_repl, debugger


# === STATE DEFINITION ===


class ScraperBuilderState(BaseAgentState):
    """Agent specific state for the scraper builder agent."""

    final_legislation_sources: Annotated[list[str], operator.add]
    code_generated: Annotated[list[str], operator.add]


# === AGENT CONSTRUCTION ===

_agent = BaseReActAgent(
    state_schema=ScraperBuilderState,
    tools=[code_generator, python_repl, debugger],
    system_prompt=scraper_builder_sys_prompt,
)

scraper_builder_agent = _agent.build()
