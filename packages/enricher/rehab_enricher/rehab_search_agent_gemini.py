from typing import List, Dict, Any, Optional, Literal, Callable 
from google import genai 
from google.genai import types   
from dataclasses import dataclass 
from pydantic import Field, BaseModel 
import os 
from dotenv import load_dotenv  
import asyncio  
import json 
from pathlib import Path 

here  = Path(__file__).parent  

env_path = here.parent / ".env"

load_dotenv(dotenv_path=env_path, override=True) 




client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))  

rehab_investigation_function = {
    "name": "rehab_investigation_result",
    "description": "Structured output describing the findings of a rehabilitation organization investigation.",
    "parameters": {
        "type": "object",
        "properties": {
            "official_name": {
                "type": "string",
                "description": "The verified official name of the rehabilitation organization.",
            },
            "official_url": {
                "type": "string",
                "nullable": True,
                "description": "The official website URL of the organization.",
            },
            "organization_description": {
                "type": "string",
                "description": "A concise description of the organization and its services.",
            },
            "other_important_urls": {
                "type": "array",
                "description": "Any additional URLs relevant to verification (profiles, listings, etc.)",
                "items": {"type": "string"},
            },
            "confidence_score": {
                "type": "integer",
                "description": "Confidence score from 1–10 based on verification strength.",
            },
            "google_maps_info": {
                "type": "object",
                "nullable": True,
                "description": "Optional structured Google Maps verification details.",
                "properties": {
                    "place_id": {
                        "type": "string",
                        "nullable": True,
                        "description": "Google Maps place_id if available.",
                    },
                    "maps_url": {
                        "type": "string",
                        "nullable": True,
                        "description": "Google Maps URL for the location.",
                    },
                    "verified_address": {
                        "type": "string",
                        "nullable": True,
                        "description": "Address verified through Google Maps.",
                    },
                    "verified_phone": {
                        "type": "string",
                        "nullable": True,
                        "description": "Phone number verified through Google Maps.",
                    },
                },
                "required": [],
            },
            "notes": {
                "type": "string",
                "description": "Any relevant notes (e.g., verification issues, inconsistencies, etc.).",
            },
        },
        "required": ["confidence_score"],
    },
}


rehab_function_decl = types.FunctionDeclaration(
    name=rehab_investigation_function["name"],
    description=rehab_investigation_function["description"],
    parameters=rehab_investigation_function["parameters"],
)

rehab_tool = types.Tool(
    function_declarations=[rehab_function_decl]
)



grounding_tool = types.Tool( 
    google_search=types.GoogleSearch()
) 

google_maps_tool = types.Tool( 
    google_maps=types.GoogleMaps()
)


config = types.GenerateContentConfig( 
    tools=[grounding_tool, google_maps_tool, rehab_tool]
) 

def create_prompt(rehab_organization) -> str:
    prompt = f"""
You are a Drug Rehabilitation Organization Investigator. Your job is to verify and summarize information about a rehabilitation organization using online sources and return a structured result via tools.

You have access to the following tools:
- `google_search` (via the web search tool) — use this to look up the organization, its website, and any authoritative references.
- `google_maps` (via the maps tool) — optionally use this to verify address, phone number, and place details.
- `rehab_investigation_result` — a function tool that you MUST call exactly once at the end of your investigation to report your final structured findings.

You will be given limited starting information: an organization name, an NPI number, a city, a state, a postal code, an address, and a phone number. Sometimes the provided location may belong to a larger parent organization. Your responsibilities are:

1. **Search and verification**
   - Use the `google_search` tool to determine whether this rehabilitation organization is legitimate, active, and currently in operation.
   - Use multiple queries that combine the organization name, address, city, state, phone number, and NPI (when helpful) to cross-check the information.
   - Prioritize authoritative sources: the official organization website, government/regulatory listings, accreditation bodies, and reputable medical/health directories over generic lead-generation or marketing sites.

2. **Optional maps verification**
   - Optionally use the `google_maps` tool to:
     - Confirm the correct address and phone number.
     - Retrieve a `place_id`, Google Maps URL, and any other structured location data.
   - If the maps data does not clearly correspond to the organization, you may leave the maps-related information empty and explain why in `notes`.

3. **Final structured result via tool call**
   - After you complete all searching and reasoning, you MUST call the `rehab_investigation_result` tool exactly once.
   - This call must be the **last thing you do** in your response.
   - You must populate its arguments as follows:
     - `official_name`: The best-verified official name of the organization (or an empty string if unknown).
     - `official_url`: The official website URL if one can be confidently identified, otherwise null.
     - `organization_description`: A concise description of the organization and its services based on the most authoritative sources you find.
     - `other_important_urls`: A list of additional URLs that meaningfully help verify the organization (e.g., government listings, accreditation, major directory profiles).
     - `confidence_score`: An integer from 1–10 indicating how confident you are in the overall correctness and verification of the organization’s identity and status.
       - If you cannot verify that the organization exists or is active, set `confidence_score` to a value **below 3** and clearly explain why in `notes`.
     - `google_maps_info` (optional):
       - Include this object only if you have reliable Google Maps data.
       - Fields:
         - `place_id`
         - `maps_url`
         - `verified_address`
         - `verified_phone`
       - If Google Maps data cannot be confidently matched to the organization, you may set this to null or omit it.
     - `notes`: Any relevant reasoning or caveats (e.g., conflicting information, multiple possible matches, data that appears outdated, or reasons for low confidence).

You must NOT return free-form natural language as the final answer.  
Instead, your final response must always conclude with a single call to the `rehab_investigation_result` tool with the appropriate arguments based on your investigation.

Here is the starting information for this organization:

<Organization Name>
{rehab_organization.organization_name}
</Organization Name>

<City>
{rehab_organization.city}
</City>

<State>
{rehab_organization.state}
</State>

<Postal Code>
{rehab_organization.postal_code}
</Postal Code>

<Address>
{rehab_organization.address}
</Address>

<Phone>
{rehab_organization.phone}
</Phone>

<NPI Number>
{rehab_organization.npi_number}
</NPI Number>
"""
    return prompt




def add_citations(response):
    text = response.text
    supports = response.candidates[0].grounding_metadata.grounding_supports
    chunks = response.candidates[0].grounding_metadata.grounding_chunks

    # Sort supports by end_index in descending order to avoid shifting issues when inserting.
    sorted_supports = sorted(supports, key=lambda s: s.segment.end_index, reverse=True)

    for support in sorted_supports:
        end_index = support.segment.end_index
        if support.grounding_chunk_indices:
            # Create citation string like [1](link1)[2](link2)
            citation_links = []
            for i in support.grounding_chunk_indices:
                if i < len(chunks):
                    uri = chunks[i].web.uri
                    citation_links.append(f"[{i + 1}]({uri})")

            citation_string = ", ".join(citation_links)
            text = text[:end_index] + citation_string + text[end_index:]

    return text





class RehabOrganization(BaseModel):
    npi_number: str
    organization_name: str
    address: str
    city: str
    state: str
    postal_code: str
    phone: str 



rehab_organization = RehabOrganization(
    npi_number="1245699099",
    organization_name="BOCA DETOX CENTER LLC",
    address="899 MEADOWS RD",
    city="BOCA RATON",
    state="FL",
    postal_code="334862338",
    phone="5619214769"
) 



class GoogleMapsInfo(BaseModel):
    place_id: Optional[str] = None
    maps_url: Optional[str] = None
    verified_address: Optional[str] = None
    verified_phone: Optional[str] = None


class RehabInvestigationResult(BaseModel):
    official_name: Optional[str] = ""
    official_url: Optional[str] = None
    organization_description: Optional[str] = ""
    other_important_urls: List[str] = []
    confidence_score: int
    google_maps_info: Optional[GoogleMapsInfo] = None
    notes: Optional[str] = "" 

def rehab_investigation_result(
    official_name: Optional[str] = "",
    official_url: Optional[str] = None,
    organization_description: Optional[str] = "",
    other_important_urls: Optional[List[str]] = None,
    confidence_score: int = 0,
    google_maps_info: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = ""
) -> RehabInvestigationResult:

    # Convert google_maps_info dict into GoogleMapsInfo model if provided
    gmaps_obj = GoogleMapsInfo(**google_maps_info) if google_maps_info else None

    return RehabInvestigationResult(
        official_name=official_name or "",
        official_url=official_url,
        organization_description=organization_description or "",
        other_important_urls=other_important_urls or [],
        confidence_score=confidence_score,
        google_maps_info=gmaps_obj,
        notes=notes or ""
    )


# Put the function into a dictionary under the correct key
tool_function_map = {
    "rehab_investigation_result": rehab_investigation_result
}

async def run_model(
    prompt_function: Callable,
    rehab_model: RehabOrganization,
) -> Dict[str, Any]:

    prompt = await asyncio.to_thread(prompt_function, rehab_model)

    response = await client.aio.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=config,
    )

    web_citations = await asyncio.to_thread(add_citations, response)

    rehab_investigation: Optional[RehabInvestigationResult] = None

    candidate = response.candidates[0]
    parts = candidate.content.parts

    function_call_part = next(
        (p for p in parts if getattr(p, "function_call", None)),
        None,
    )

    if function_call_part:
        function_call = function_call_part.function_call
        function_to_call = tool_function_map.get(function_call.name)

        if function_to_call:
            args = function_call.args
            if isinstance(args, str):
                args = json.loads(args)

            result = function_to_call(**args)

            if isinstance(result, RehabInvestigationResult):
                rehab_investigation = result

    return {
        "rehab_results": rehab_investigation,
        "citations": web_citations,
        "full_response": response,
    }

        


async def main(): 
    results_dict = await run_model(create_prompt, rehab_organization)
    return results_dict   
    
    


# if __name__ == "__main__": 
#     final_results = asyncio.run(main()) 

#     print(final_results)



