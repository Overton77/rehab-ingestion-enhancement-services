from typing import List, Optional
from pydantic import BaseModel, Field


class ParentCompanyOutput(BaseModel):
    slug: Optional[str] = Field(
        None,
        description="Slug identifier for the parent company."
    )
    name: Optional[str] = Field(
        None,
        description="Name of the parent company."
    )
    websiteUrl: Optional[str] = Field(
        None,
        description="Website URL of the parent company."
    )
    description: Optional[str] = Field(
        None,
        description="Short description of the parent company."
    )
    verifiedExists: Optional[bool] = Field(
        None,
        description="Whether the parent company is verified to exist."
    )
    headquartersCity: Optional[str] = None
    headquartersState: Optional[str] = None
    headquartersCountry: Optional[str] = None
    headquartersPostalCode: Optional[str] = None
    headquartersStreet: Optional[str] = None


class CampusCreateOutput(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    displayName: Optional[str] = None
    description: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    timeZone: Optional[str] = None
    visitingHours: Optional[str] = None
    directionsSummary: Optional[str] = None
    bedsTotal: Optional[int] = None
    bedsDetox: Optional[int] = None
    bedsResidential: Optional[int] = None
    acceptsWalkIns: Optional[bool] = None
    hasOnsiteMD: Optional[bool] = None
    hasTwentyFourHourNursing: Optional[bool] = None
    heroImageUrl: Optional[str] = None
    galleryImageUrls: List[str] = Field(default_factory=list)
    primaryEnvironmentSlug: Optional[str] = None
    primarySettingStyleSlug: Optional[str] = None
    primaryLuxuryTierSlug: Optional[str] = None


class CampusOutput(BaseModel):
    slug: str = Field(..., description="Unique slug for this campus.")
    create: CampusCreateOutput = Field(
        ...,
        description="Payload to create this campus in the downstream system."
    )


class ProgramFeatureOutput(BaseModel):
    slug: str = Field(..., description="Canonical slug for this feature.")
    displayName: str = Field(..., description="Human-readable label.")


class InsurancePayerOutput(BaseModel):
    name: str = Field(..., description="Payer/insurer name, e.g., 'Aetna'.")


class OrgInfoOutput(BaseModel):
    """
    Top-level organization metadata inferred primarily from org_info URLs.
    """
    name: Optional[str] = None
    slug: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    legalName: Optional[str] = None
    npi_number: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    websiteUrl: Optional[str] = None
    mainPhone: Optional[str] = None
    mainEmail: Optional[str] = None
    heroImageUrl: Optional[str] = None
    galleryImageUrls: List[str] = Field(default_factory=list)
    yearFounded: Optional[int] = None
    isNonProfit: Optional[bool] = None
    verifiedExists: Optional[bool] = None
    primarySourceUrl: Optional[str] = None
    otherSourceUrls: List[str] = Field(default_factory=list)
    baseCurrency: Optional[str] = None
    fullPrivatePrice: Optional[float] = None
    defaultTimeZone: Optional[str] = None
    parentCompany: Optional[ParentCompanyOutput] = None


class LocationsFacilitiesOutput(BaseModel):
    """
    Campus and location metadata inferred from locations_facilities URLs.
    """
    campuses: List[CampusOutput] = Field(
        default_factory=list,
        description="All known campuses / facility locations."
    )


class ProgramsCareOutput(BaseModel):
    """
    Program features / modalities inferred from programs_care URLs.
    """
    programFeatures: List[ProgramFeatureOutput] = Field(
        default_factory=list,
        description="Program features like detox, MAT, IOP, PHP, etc."
    )


class AdmissionsFinancialOutput(BaseModel):
    """
    Admissions + insurance details inferred from admissions_financial URLs.
    """
    insurancePayers: List[InsurancePayerOutput] = Field(
        default_factory=list,
        description="Accepted insurance payers."
    )


class RehabOrgEnrichmentOutput(BaseModel):
    """
    Final combined enrichment payload for a single rehab organization.
    Each sub-model is primarily fed by its sitemap category.
    """
    org_info: OrgInfoOutput
    locations_facilities: LocationsFacilitiesOutput
    programs_care: ProgramsCareOutput
    admissions_financial: AdmissionsFinancialOutput