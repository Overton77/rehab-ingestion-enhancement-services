from typing import Literal, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# Condensed URL Category System (8 categories total)
# -------------------------------------------------------------------

UrlCategoryLiteral = Literal[
    "ORG_INFO",             # about, mission, overview, FAQs
    "PROGRAMS_CARE",        # programs, levels, detox, MAT, clinical modalities
    "ADMISSIONS_FINANCIAL", # admissions, insurance, payment options
    "LOCATIONS_FACILITIES", # campuses, locations, amenities, visitor info
  
]

# -------------------------------------------------------------------
# Bucket Literal (mapped directly to the final JSON needs)
# -------------------------------------------------------------------

BucketLiteral = Literal[
    "org_info",
    "programs_care",
    "admissions_financial",
    "locations_facilities",
   
]


# -------------------------------------------------------------------
# Individual URL Category Item
# -------------------------------------------------------------------

class URLCategoryItem(BaseModel):
    """
    A single URL and its assigned condensed semantic category.
    """
    url: str = Field(..., description="The URL found in the sitemap.")
    category: UrlCategoryLiteral = Field(
        ...,
        description="The condensed semantic category assigned to this URL."
    )

    notes: Optional[str] = Field(
        None,
        description="Optional note explaining why the URL was categorized this way."
    )


# -------------------------------------------------------------------
# Categorization Output Grouped into Major Buckets
# -------------------------------------------------------------------

class SiteMapCategorizationOutput(BaseModel):
    """
    Sitemap categorization grouped into the 8 major buckets
    used by the rehab enrichment pipeline.
    """
    org_info: List[URLCategoryItem] = Field(
        default_factory=list,
        description="About, mission, overview, FAQs"
    )
    programs_care: List[URLCategoryItem] = Field(
        default_factory=list,
        description="Programs, levels of care, detox, MAT, clinical modalities"
    )
    admissions_financial: List[URLCategoryItem] = Field(
        default_factory=list,
        description="Admissions, insurance, payment options"
    )
    locations_facilities: List[URLCategoryItem] = Field(
        default_factory=list,
        description="Locations, campuses, amenities, visitor info"
    )
