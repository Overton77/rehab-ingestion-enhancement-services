from rehab_common.rehab_sdk import create_rehab_org_with_connect_or_create  
from dotenv import load_dotenv    
from typing_extensions import TypedDict, Any 
import asyncio 
from graphql_client.input_types import CreateRehabOrgInput    
from agents import Agent, WebSearchTool, Runner, SQLiteSession, RunContextWrapper, ModelSettings, function_tool 
from dataclasses import dataclass  
from typing import List, Optional
from pydantic import BaseModel, Field 
from openai.types.shared import Reasoning


from pathlib import Path 

here = Path(__file__).parent.parent  
load_dotenv(dotenv_path=here / ".env", override=True)     

@dataclass 
class ProspectiveRehab: 
    npi_number: str 
    organization_name: str  
    address: str  
    city: str   
    state: str   
    postal_code: str  
    phone: str   


class RehabDiscoveryResult(BaseModel):
    """
    First-pass discovery / validation of a rehab organization.

    This is *not* the full DB schema – it's just to confirm existence
    and capture foundational facts that are easy to fetch from the web.
    """

    rehab_organization_name: str = Field(
        ...,
        description="Canonical / best-guess name of the rehab organization."
    )

    official_website_url: Optional[str] = Field(
        None,
        description="The primary official website URL for the rehab, if it exists."
    )

    important_urls: List[str] = Field(
        default_factory=list,
        description=(
            "Other important URLs such as directory listings, Google Maps, "
            "state/official listings, or alternate sites clearly tied to this rehab."
        ),
    )

    confidence_score: int = Field(
        ...,
        ge=1,
        le=5,
        description=(
            "1–5 confidence that this rehab exists *and* you found the right entity. "
            "1 = almost certainly does not exist / wrong match; "
            "2 = very low confidence; "
            "3 = medium; 4 = high; 5 = very high confidence."
        ),
    )

    active: bool = Field(
        ...,
        description=(
            "True if the rehab appears to be currently operating and accepting patients. "
            "False if it appears closed, permanently inactive, or clearly not operating."
        ),
    )

    short_summary: str = Field(
        ...,
        description=(
            "2–4 sentence, plain-language summary of what this rehab is, "
            "who it serves, and any key identifying details (location, level of care, etc)."
        ),
    )

 
async def dynamic_rehab_instructions(
    context: RunContextWrapper[ProspectiveRehab],
    agent: Agent[ProspectiveRehab],
) -> str:
    pr = context.context

    return f"""
You are a rehabilitation organization existence-confirmation agent with access to a web search tool.

You will be given an organization from the NPI database (name, address, city, state, zip, phone).
Your job is to:
- Confirm whether this organization exists as a real rehab provider.
- Judge whether it appears to be currently active.
- Identify its canonical rehab organization name and official website if possible.
- Collect a small set of other important URLs (maps, major directories, gov/official listings).
- Produce a short, clear summary of what this rehab is.

Use web search aggressively to cross-check the NPI information against what is actually on the web.

NPI rehab organization details:
- Organization Name: {pr.organization_name}
- Address: {pr.address}
- City: {pr.city}
- State: {pr.state}
- Zip Code: {pr.postal_code}
- Phone Number: {pr.phone}

Structured output (RehabDiscoveryResult):
- rehab_organization_name: canonical/best-guess name you find online.
- official_website_url: single main official site URL, or null.
- important_urls: 1–5 key related URLs (maps, directories, gov listings, alternate domains).
- confidence_score: integer 1–5 for how confident you are this is a real, currently existing rehab match.
- active: True if it appears currently operating; False if clearly closed/inactive.
- short_summary: 2–4 sentences on what this rehab is, who it serves, and any key identifying details.

Always return a **single** RehabDiscoveryResult object consistent with the above fields.
If you cannot confidently verify the rehab, set a low confidence_score (1–2), active = False,
and explain the uncertainty in short_summary.
"""

rehab_existence_agent = Agent[ProspectiveRehab](
    name="rehab_existence_agent",
    instructions=dynamic_rehab_instructions,
    tools=[WebSearchTool()],
    model="gpt-5-nano",
    model_settings=ModelSettings(
        reasoning=Reasoning(effort="minimal"),
        verbosity="low",
    ),
    output_type=RehabDiscoveryResult,
)


async def run_rehab_existence_check(user_prompt: str) -> RehabDiscoveryResult | Any:
    prospective = ProspectiveRehab(
        npi_number="1234567890",
        organization_name="Sunrise Recovery Center",
        address="123 Main St",
        city="Austin",
        state="TX",
        postal_code="78701",
        phone="555-123-4567",
    )
 

    run_result = await Runner.run(
        rehab_existence_agent,
        context=prospective,
        input=user_prompt,
    )  

    final_output = run_result.final_output  

    return final_output 



# Conditionally end or continue the ingestion process 


# Start simple  by using the sitemap or another search to categorize types of urls 

# for each type parallelize the processing of the urls and each url in parallel   

# Gather the results in each parallel branch  

# Aggregate the results of the parallel branches 

# Run the graphql client to create the rehab org 







