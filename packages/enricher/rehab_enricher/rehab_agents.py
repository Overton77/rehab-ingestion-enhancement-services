from agents.extensions.memory import SQLAlchemySession  
from sqlalchemy.ext.asyncio import create_async_engine  
from agents import function_tool, RunContextWrapper, Agent, Runner, RunConfig 
from agents.tool import WebSearchTool, Tool  
from agents.mcp import MCPServerStdio, create_static_tool_filter 
from dataclasses import dataclass   
from pydantic import BaseModel, Field   
from .crawl_utils import return_markdown   
from .rehab_outputs import (  
    OrgInfoOutput, LocationsFacilitiesOutput, ProgramsCareOutput, AdmissionsFinancialOutput, RehabOrgEnrichmentOutput 
)
from .file_utils import ( 
    async_write_json, async_write_text 
)

from .url_utils import  fetch_sitemap  
from .output_types_and_mappers import URLCategoryItem, SiteMapCategorizationOutput 
from .agent_hooks import RehabRunHooks
import asyncio 
from uuid import uuid4

from typing import Optional, List, Any, Callable 
from dotenv import load_dotenv  
import os 
from pathlib import Path 

here = Path(__file__).parent   


env_path = here.parent / ".env" 

load_dotenv(dotenv_path=env_path, override=True)      

if not os.getenv("OPENAI_API_KEY"): 
    raise ValueError("Missing OpenAI API key ")

COMMON_SITEMAP_PATHS = [
    "sitemap.xml",
    "sitemap_index.xml",
    "sitemap/",
    "sitemap1.xml",
    "sitemap_index.xml"
] 

sessions_engine = create_async_engine( 
    os.getenv("REHAB_SESSIONS_DB")
) 


@dataclass 
class ProspectiveRehabContext: 
    organization_name: str  
    npi_number: str 
    address: str 
    city: str 
    state: str  
    country: str 
    postal_code: str 
    phone_number: str   


@dataclass
class SiteMapContext:
    """
    Context object holding the raw sitemap content as a string.
    This might be the full XML or a newline-delimited list of URLs,
    depending on your upstream processing.
    """
    sitemap_str: str  


rehab_confirmation_agent_tools = [WebSearchTool()] 

@function_tool 
async def return_markdown_tool(ctx: RunContextWrapper[Any], url: str) -> str: 
    """ 
     Args:  
         url: The url of the rehab organization to use to transform into markdown  

    Returns: 
          The markdown representation of the url 

    """ 

    markdown = await return_markdown(url) 

    return markdown 



class RehabConfirmationOutput(BaseModel):
    """
    Output model for confirming whether a rehab organization exists and establishing
    its canonical identity.
    """
    official_url: str = Field(
        None,
        description="The confirmed primary official website URL of the rehab organization."
    )
    other_important_urls: List[str] = Field(
        default_factory=list,
        description="Other authoritative URLs that support verification."
    )
    rehab_official_name: Optional[str] = Field(
        None,
        description="The official or legal name of the rehab organization as confirmed by multiple sources."
    )
    confidence_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Verification confidence score (1–5). Score of 2 is the minimum passing threshold."
    )
    parent_company_name: Optional[str] = Field(
        None,
        description="Optional: Parent company name if it can be reliably determined."
    )






def create_session():  

    rehab_agent_session = SQLAlchemySession(f"rehab_run_{uuid4()}", engine=sessions_engine, create_tables=True)  

    return rehab_agent_session 

def dynamic_confirmation_instructions(
    context: RunContextWrapper[ProspectiveRehabContext],
    agent: Agent[ProspectiveRehabContext]
) -> str:
    return f"""
You are a verification agent confirming whether a substance treatment facility exists
and establishing its canonical identity.

Use **web search heavily** and ensure that every claim is grounded in search results.

Your goals:

1. Confirm that the organization exists as described.
2. Identify its official website URL.
3. Collect any authoritative second-layer URLs (corporate pages, location pages, licensing pages).
4. Determine the official or legal name if possible.
5. Assign a confidence score from 1–5.
   - 1 = Highly uncertain
   - 2 = Minimum threshold (weak verification)
   - 3 = Adequate verification
   - 4 = Strong verification
   - 5 = Very strong verification

6. Identify the parent company only if confidently supported.

### INPUT DATA FROM CONTEXT

Organization Name: {context.context.organization_name}
NPI Number: {context.context.npi_number}
Address: {context.context.address}
City: {context.context.city}
State: {context.context.state}
Country: {context.context.country}
Postal Code: {context.context.postal_code}
Phone Number: {context.context.phone_number}

### OUTPUT FORMAT

Return data in the JSON structure defined by RehabConfirmationOutput ONLY.
No extra commentary.
""" 

def dynamic_sitemap_categories_instructions(
    context: RunContextWrapper[SiteMapContext],
    agent: Agent[SiteMapContext]
) -> str:
    return f"""
You are a master URL categorizer and a critical step in a rehab information
enrichment pipeline.

You are given an entire sitemap for a rehab treatment organization. This may
be raw XML, a list of <loc> entries, or a newline-delimited list of URLs.

Your job is to:
1. Inspect all URLs in the sitemap.
2. Assign each relevant URL to one of the fine-grained categories:
   - ORG_OVERVIEW – about, mission, leadership, "About Us", "Why Us"
   - PROGRAMS – levels of care, treatment programs, detox, IOP, residential, MAT
   - ADMISSIONS – admissions process, insurance-related admissions steps,
                  how to get started, verify benefits
   - FAQ – general FAQs, what to bring, how long is treatment, common questions

   - CLINICAL_CARE – treatment philosophy, therapies, clinical modalities,
                     medical/clinical model descriptions
   - STAFF – bios pages for providers, leadership, clinical team, staff
   - ACCREDITATION_LICENSURE – JCAHO, CARF, state licenses, certifications,
                                regulatory compliance
   - OUTCOMES_RESEARCH – outcomes data, clinical studies, quality metrics,
                         evidence of effectiveness

   - LOCATIONS_INDEX – “Our Locations” listing pages aggregating multiple facilities
   - CAMPUS_DETAIL – individual campus/facility detail pages, maps, photos, directions
   - AMENITIES_FACILITY – amenities, facilities, tours, photos of the environment
   - VISITOR_INFO – visiting hours, travel info, family visit guidance

   - INSURANCE – accepted providers, in-network lists, insurance education
   - PAYMENT_OPTIONS – self-pay, financing, cost information, sliding scale, etc.

   - TESTIMONIALS – alumni stories, patient testimonials, success stories
   - REVIEWS_EXTERNAL – pages that embed or link to Google reviews or other review sites
   - STORIES_BLOG – blog posts, educational articles, resource content
   - NEWS_PRESS – press releases, media coverage, announcements

   - CONTACT – contact pages, forms, phone/email contact
   - LEGAL_PRIVACY – privacy policy, HIPAA notices, terms & conditions
   - JOBS – careers, employment, hiring pages
   - OTHER – any page that does not clearly fit into the above categories or is low-signal
             for the rehab enrichment use case

3. Group the categorized URLs into the broader logical buckets:
   - core_org
   - clinical_and_operational
   - financial_insurance
   - campuses_locations_facilities
   - social_proof_and_content
   - legal_misc_and_other

4. For each URL, provide:
   - url
   - category (one of the fine-grained labels above)
   - confidence (0.0–1.0)
   - optional short notes if useful

You MUST respond using ONLY the JSON structure defined by SiteMapCategorizationOutput.

### RAW SITEMAP INPUT

The sitemap content is:

{context.context.sitemap_str}

### IMPORTANT

- Ignore assets like images, JS, CSS unless they are clearly meaningful content pages.
- Do not include duplicate URLs.
- Do not add commentary outside the JSON output.
"""



def create_rehab_confirmation_agent(
    dynamic_instructions: Callable,
    tools: List[Tool], 
    output_type: type[RehabConfirmationOutput],  
):
    rehab_confirmation_agent = Agent(
        name="rehab_confirmation",
        tools=tools,
        output_type=output_type, 
        instructions=dynamic_instructions, 
    
    )

    return rehab_confirmation_agent  

def create_sitemap_categories_agent(
    dynamic_instructions, 

    output_type: type[SiteMapCategorizationOutput],        


):
    return Agent(
        name="sitemap_categories",
        instructions=dynamic_instructions, 
        output_type=output_type, 
    
    
                          # <── SAME session for all agents
    )


async def run_category_agent(
    agent: Agent,
    urls: List[str],
    session: SQLAlchemySession,
    run_hooks,
    prospective_context,
    model: str = "gpt-4.1",
    max_turns: int = 4,
) -> BaseModel:
    """
    Generic helper that:
    - Sends the category URL list to an Agent
    - Lets the Agent call `return_markdown` as needed
    - Returns the Agent's structured output
    """
    if not urls:
        # Let the agent still try to infer from context if possible
        urls_payload = []
    else:
        urls_payload = urls

    user_input = (
        "You are an enrichment agent for a single rehab organization.\n"
        "You are given a list of URLs that all belong to the same organization "
        "and the same semantic category (e.g. org_info, programs_care, etc.).\n\n"
        "Instructions:\n"
        "- Use the `return_markdown` tool on any URL when you need page content.\n"
        "- You may call the tool multiple times across multiple turns.\n"
        "- Infer as many fields of your structured output model as possible.\n"
        "- Only output valid JSON compatible with your configured output_type.\n\n"
        f"Category URLs (JSON array): {urls_payload}"
    )

    category_run = await Runner.run(
        starting_agent=agent,
        input=user_input,
        session=session,
        context=prospective_context,
        hooks=run_hooks,
        run_config=RunConfig(model=model),
        max_turns=max_turns,
    )

    return category_run.final_output


# -------------------------------------------------------------------
# Category-specific Agents
# -------------------------------------------------------------------

def create_org_info_agent() -> Agent:
    return Agent(
        name="org_info_enrichment_agent",
        instructions=(
            "Extract top-level organization metadata (name, legalName, websiteUrl, "
            "phones, description, parent company, etc.) for a single rehab provider. "
            "Use only authoritative pages for source-of-truth. When uncertain, leave "
            "fields null instead of guessing. Use return_markdown to inspect pages."
        ),
        tools=[return_markdown_tool],
        output_type=OrgInfoOutput,
    )


def create_locations_facilities_agent() -> Agent:
    return Agent(
        name="locations_facilities_enrichment_agent",
        instructions=(
            "Extract all known facility campuses/locations for this rehab provider. "
            "Populate CampusOutput objects including slug, address, phone, timeZone, "
            "and other metadata if available. Use return_markdown to read location and "
            "contact pages. If multiple campuses share details, still create "
            "distinct campus entries."
        ),
        tools=[return_markdown_tool],
        output_type=LocationsFacilitiesOutput,
    )


def create_programs_care_agent() -> Agent:
    return Agent(
        name="programs_care_enrichment_agent",
        instructions=(
            "Extract program features (levels of care, modalities, services) offered "
            "by this rehab provider. Normalize into ProgramFeatureOutput objects, "
            "using canonical slugs where possible, such as: medical_detox, "
            "inpatient_rehab, outpatient_programs, medication_assisted_treatment, "
            "aftercare_and_relapse_prevention, etc."
        ),
        tools=[return_markdown_tool],
        output_type=ProgramsCareOutput,
    )


def create_admissions_financial_agent() -> Agent:
    return Agent(
        name="admissions_financial_enrichment_agent",
        instructions=(
            "Extract admissions and financial information focusing on insurance "
            "payers. Produce a list of InsurancePayerOutput objects with payer names "
            "like 'Aetna', 'Blue Cross Blue Shield', 'Cigna', etc."
        ),
        tools=[return_markdown_tool],
        output_type=AdmissionsFinancialOutput,
    )



async def run_agent(confirmation_max_turns: int = 2, sitemap_max_turns: int = 1):
    # 1. Create a shared session for this run
    session = create_session()

    run_hooks = RehabRunHooks()

    # 2. Build the ProspectiveRehabContext from your CSV-like row:
    # "1245699099,BOCA DETOX CENTER LLC,2019-06-05 00:00:00,,899 MEADOWS RD,BOCA RATON,FL,334862338, 5619214769"
    prospective_context = ProspectiveRehabContext(
        npi_number="1245699099",
        organization_name="BOCA DETOX CENTER LLC",
        address="899 MEADOWS RD",
        city="BOCA RATON",
        state="FL",
        country="USA",
        postal_code="334862338",
        phone_number="5619214769",
    )

    # 3. Create and run the rehab confirmation agent
    rehab_confirmation_agent = create_rehab_confirmation_agent(
        dynamic_instructions=dynamic_confirmation_instructions,
        tools=rehab_confirmation_agent_tools,
        output_type=RehabConfirmationOutput,
    )

    print("Running rehab_confirmation agent...")
    confirmation_run = await Runner.run(
        starting_agent=rehab_confirmation_agent,
        input="",  # no additional user text; everything is in context
        session=session,
        run_config=RunConfig(model="gpt-5-nano"),
        context=prospective_context,
        hooks=run_hooks,
        max_turns=confirmation_max_turns,
    )

    confirmation_output: RehabConfirmationOutput = confirmation_run.final_output
    print("RehabConfirmationOutput:", confirmation_output)

    # Persist confirmation output
    await async_write_json(
        f"rehab_confirmation_{prospective_context.npi_number}.json",
        confirmation_output.model_dump(),
    )

    if not confirmation_output or not confirmation_output.official_url:
        print("No official URL found. Exiting.")
        return

    official_url = confirmation_output.official_url
    print(f"Official URL: {official_url}")

    # 4. Fetch sitemap for the official URL
    print("Fetching sitemap...")
    sitemap_xml = await fetch_sitemap(official_url)

    if not sitemap_xml:
        print("No sitemap found for this URL. Exiting.")
        return

    # Save raw sitemap
    await async_write_text(
        f"sitemap_raw_{prospective_context.npi_number}.xml",
        sitemap_xml,
    )

    # 5. Create and run the sitemap categories agent
    sitemap_context = SiteMapContext(sitemap_str=sitemap_xml)

    sitemap_categories_agent = create_sitemap_categories_agent(
        dynamic_instructions=dynamic_sitemap_categories_instructions,
        output_type=SiteMapCategorizationOutput,
    )

    print("Running sitemap_categories agent...")
    sitemap_run = await Runner.run(
        starting_agent=sitemap_categories_agent,
        input="",  # again, instructions + context only
        session=session,
        run_config=RunConfig(model="gpt-4.1"),
        context=sitemap_context,
        hooks=run_hooks,
        max_turns=sitemap_max_turns,
    )

    sitemap_output: SiteMapCategorizationOutput = sitemap_run.final_output
    print("SiteMapCategorizationOutput received.")

    # Persist categorized sitemap output
    await async_write_json(
        f"sitemap_categories_{prospective_context.npi_number}.json",
        sitemap_output.model_dump(),
    )

    # ----------------------------------------------------------------
    # 6. Collect URLs per bucket (unique within each category)
    # ----------------------------------------------------------------
    def dedupe_urls(items: List[URLCategoryItem]) -> List[str]:
        _seen = set()
        _urls: List[str] = []
        for it in items:
            u = str(it.url)
            if u not in _seen:
                _seen.add(u)
                _urls.append(u)
        return _urls

    org_info_urls = dedupe_urls(sitemap_output.org_info)
    programs_care_urls = dedupe_urls(sitemap_output.programs_care)
    admissions_financial_urls = dedupe_urls(sitemap_output.admissions_financial)
    locations_facilities_urls = dedupe_urls(sitemap_output.locations_facilities)

    print(f"org_info URLs: {len(org_info_urls)}")
    print(f"programs_care URLs: {len(programs_care_urls)}")
    print(f"admissions_financial URLs: {len(admissions_financial_urls)}")
    print(f"locations_facilities URLs: {len(locations_facilities_urls)}")

    # ----------------------------------------------------------------
    # 7. Create category-specific agents (with return_markdown tool)
    # ----------------------------------------------------------------
    org_info_agent = create_org_info_agent()
    locations_facilities_agent = create_locations_facilities_agent()
    programs_care_agent = create_programs_care_agent()
    admissions_financial_agent = create_admissions_financial_agent()

    # ----------------------------------------------------------------
    # 8. Run each agent in a loop until it fulfills its structured output
    #    (max_turns controls the inner tool-using loop per category)
    # ----------------------------------------------------------------
    category_max_turns = 4

    print("Running org_info enrichment agent...")
    org_info_output: OrgInfoOutput = await run_category_agent(
        agent=org_info_agent,
        urls=org_info_urls,
        session=session,
        run_hooks=run_hooks,
        prospective_context=prospective_context,
        model="gpt-4.1",
        max_turns=category_max_turns,
    )
    print("OrgInfoOutput:", org_info_output)

    print("Running locations_facilities enrichment agent...")
    locations_facilities_output: LocationsFacilitiesOutput = await run_category_agent(
        agent=locations_facilities_agent,
        urls=locations_facilities_urls,
        session=session,
        run_hooks=run_hooks,
        prospective_context=prospective_context,
        model="gpt-4.1",
        max_turns=category_max_turns,
    )
    print("LocationsFacilitiesOutput:", locations_facilities_output)

    print("Running programs_care enrichment agent...")
    programs_care_output: ProgramsCareOutput = await run_category_agent(
        agent=programs_care_agent,
        urls=programs_care_urls,
        session=session,
        run_hooks=run_hooks,
        prospective_context=prospective_context,
        model="gpt-4.1",
        max_turns=category_max_turns,
    )
    print("ProgramsCareOutput:", programs_care_output)

    print("Running admissions_financial enrichment agent...")
    admissions_financial_output: AdmissionsFinancialOutput = await run_category_agent(
        agent=admissions_financial_agent,
        urls=admissions_financial_urls,
        session=session,
        run_hooks=run_hooks,
        prospective_context=prospective_context,
        model="gpt-4.1",
        max_turns=category_max_turns,
    )
    print("AdmissionsFinancialOutput:", admissions_financial_output)

    # ----------------------------------------------------------------
    # 9. Combine everything into a single enrichment payload & persist
    # ----------------------------------------------------------------
    combined_enrichment = RehabOrgEnrichmentOutput(
        org_info=org_info_output,
        locations_facilities=locations_facilities_output,
        programs_care=programs_care_output,
        admissions_financial=admissions_financial_output,
    )

    await async_write_json(
        f"rehab_enrichment_{prospective_context.npi_number}.json",
        combined_enrichment.model_dump(),
    )

    print("RehabOrgEnrichmentOutput persisted.")


if __name__ == "__main__":  
    asyncio.run(run_agent())
    


