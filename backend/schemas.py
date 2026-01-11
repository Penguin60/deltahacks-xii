"""
Pydantic models for the incident triage pipeline.
Implements the JSON spec from backend-JSON-spec.md
"""
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Literal
import re


class IncidentType(str, Enum):
    """Incident type classification"""
    PUBLIC_NUISANCE = "Public Nuisance"
    BREAK_IN = "Break In"
    ARMED_ROBBERY = "Armed Robbery"
    CAR_THEFT = "Car Theft"
    THEFT = "Theft"
    PICKPOCKET = "PickPocket"
    FIRE = "Fire"
    MASS_FIRE = "Mass Fire"
    CROWD_STAMPEDE = "Crowd Stampede"
    TERRORIST_ATTACK = "Terrorist Attack"
    OTHER = "Other"


class SuggestedAction(str, Enum):
    """Suggested action for dispatcher"""
    CONSOLE = "console"
    ASK_FOR_MORE_DETAILS = "ask for more details"
    DISPATCH_OFFICER = "dispatch officer"
    DISPATCH_FIRST_AIDERS = "dispatch first-aiders"
    DISPATCH_FIREFIGHTERS = "dispatch firefighters"


class TranscriptIn(BaseModel):
    """Input transcript JSON from speech-to-text API"""
    text: str
    time: str # this should be HH:MM 24-hour format
    location: str  # May be nonsense, call_agent will extract/normalize
    duration: str  # minutes and seconds


class CallIncident(BaseModel):
    """call_agent (agent1) output: extracted core incident fields"""
    id: str  # ULID
    incidentType: IncidentType
    location: str  # Canadian postal code: L#L#L# format
    date: str  # month/day/year format
    time: str  # HH:MM 24-hour format
    duration: str  # minutes and seconds
    message: str  # Original message from transcript
    
    @field_validator('location')
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        """Validate and normalize Canadian postal code format"""
        # Remove spaces and convert to uppercase
        normalized = v.replace(' ', '').upper()
        # Check format: L#L#L#; where L=letter, #=digit
        if not re.match(r'^[A-Z]\d[A-Z]\d[A-Z]\d$', normalized):
            # Allow through for now, LLM might produce invalid format
            # Log warning but don't fail validation
            pass
        return normalized
    
    @field_validator('incidentType', mode='before')
    @classmethod
    def coerce_incident_type(cls, v) -> str:
        """Coerce/normalize incident type strings"""
        if isinstance(v, str):
            # Normalize spacing and capitalization
            v_normalized = ' '.join(v.split()).title()
            # Try to match against enum values
            for incident_type in IncidentType:
                if incident_type.value.lower() == v.lower():
                    return incident_type.value
            # Handle special cases
            if 'pick' in v.lower() and 'pocket' in v.lower():
                return IncidentType.PICKPOCKET.value
        return v


class AssessmentIncident(CallIncident):
    """assessment_agent (agent2) output: adds description and suggested action"""
    desc: str  # AI-generated one-line description
    suggested_actions: SuggestedAction
    status: Literal["called"] = "called"  # Hard-coded by code
    severity_level: Literal["none"] = "none"  # Hard-coded by code
    
    @field_validator('suggested_actions', mode='before')
    @classmethod
    def coerce_suggested_action(cls, v) -> str:
        """Coerce/normalize suggested action strings"""
        if isinstance(v, str):
            v_lower = v.lower().strip()
            for action in SuggestedAction:
                if action.value.lower() == v_lower:
                    return action.value
        return v


class TriageIncident(BaseModel):
    """triage_agent (agent3) output: final incident for Redis queue"""
    id: str  # ULID
    incidentType: IncidentType
    location: str  # Canadian postal code
    date: str  # month/day/year
    time: str  # HH:MM 24-hour
    duration: str  # minutes and seconds
    message: str
    desc: str
    suggested_actions: SuggestedAction
    status: Literal["in progress"] = "in progress"  # Hard-coded by code
    severity_level: Literal["1", "2", "3"]  # Set by agent3
    
    @field_validator('severity_level', mode='before')
    @classmethod
    def validate_severity(cls, v) -> str:
        """Ensure severity is one of the allowed values"""
        if isinstance(v, int):
            v = str(v)
        if v not in ["1", "2", "3"]:
            # Default to "2" if invalid
            return "2"
        return v
