"""Political commentary agent for NV Local.

This module defines the political_commentry_agent that finds political figures
and their blog commentary for a given city. It uses the BaseReActAgent template
with political figure finder, blog search, and social media tools.

The agent helps voters identify relevant political figures and their publicly
available commentary on local issues. When more context is needed to be fair
and holistic, it can also search their official social media accounts.
"""

from agents.base_agent_template import BaseReActAgent
from tools.political_commentry_finder import (
    political_figure_finder,
    search_political_commentary,
    search_political_social_media,
)

from utils.schemas import PoliticalCommentaryState

# === AGENT CONSTRUCTION ===

_agent = BaseReActAgent(
    state_schema=PoliticalCommentaryState,
    tools=[
        political_figure_finder,
        search_political_commentary,
        search_political_social_media,
    ],
    system_prompt="""You are a political commentary agent that helps find and analyze political figures and their public statements.

Your goal is to help voters understand what their elected representatives have said about local issues.

IMPORTANT: When searching for additional context from social media, only use this when 
NECESSARY for fairness and holistic understanding. Do not use social media to find 
negative information or to amplify any particular viewpoint. Use it only when you 
need more context to provide a balanced, complete picture to voters.""",
)

political_commentry_agent = _agent.build()
