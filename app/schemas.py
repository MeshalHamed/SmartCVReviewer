from pydantic import BaseModel, Field


class JobRole(BaseModel):
    title: str
    why: str
    fit_score: int = Field(ge=0, le=100)
    keywords: list[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    review_id: str = ""
    language: str
    executive_summary: str
    ats_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    recommended_roles: list[JobRole] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    evidence_notes: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    source_type: str
    rag: dict


class ErrorResponse(BaseModel):
    detail: str


class ExperienceItem(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str = ""
    technologies: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    location: str = ""
    dates: str = ""
    notes: list[str] = Field(default_factory=list)


class OptimizedCV(BaseModel):
    language: str
    full_name: str = ""
    target_title: str = ""
    contact_line: str = ""
    location: str = ""
    links: list[str] = Field(default_factory=list)
    summary: str = ""
    core_skills: list[str] = Field(default_factory=list)
    technical_skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    additional_sections: list[ExperienceItem] = Field(default_factory=list)
