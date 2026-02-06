from pydantic import BaseModel, Field, conlist


class ContentBlueprint(BaseModel):
    title: str
    summary: str
    key_points: conlist(str, min_length=8, max_length=12)
    hooks: conlist(str, min_length=10, max_length=20)
    quotes: conlist(str, min_length=10, max_length=20)
    ctas: conlist(str, min_length=8, max_length=12)
    do_not_say: conlist(str, min_length=5, max_length=10)


class LinkedinPost(BaseModel):
    id: str
    hook: str
    body: str
    cta: str
    hashtags: list[str]


class XThread(BaseModel):
    id: str
    tweets: conlist(str, min_length=3)
    closing_cta: str


class BlogOutline(BaseModel):
    id: str
    title: str
    audience: str
    goal: str
    outline: conlist(str, min_length=3)
    key_takeaways: conlist(str, min_length=3)


class IGStory(BaseModel):
    id: str
    slides: conlist(str, min_length=3)


class DraftsSchema(BaseModel):
    linkedin_posts: list[LinkedinPost]
    x_threads: list[XThread]
    blog_outlines: list[BlogOutline]
    ig_stories: list[IGStory]


class QuickBundle(BaseModel):
    summary: str
    linkedin_posts: conlist(LinkedinPost, min_length=1, max_length=1)
    x_threads: conlist(XThread, min_length=2, max_length=2)
    blog_outlines: list[BlogOutline] = Field(default_factory=list)
    ig_stories: conlist(IGStory, min_length=1, max_length=1)


class VisualSection(BaseModel):
    icon: str
    text: str


class VisualBlueprint(BaseModel):
    title: str
    subtitle: str
    sections: conlist(VisualSection, min_length=3, max_length=4)
    visual_hint: str


class Drafts(BaseModel):
    linkedin_posts: list[str] = Field(default_factory=list)
    x_threads: list[str] = Field(default_factory=list)
    blog_outlines: list[str] = Field(default_factory=list)
    ig_stories: list[str] = Field(default_factory=list)
