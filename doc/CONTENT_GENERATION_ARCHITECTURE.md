# Content Generation Architecture
**FinAgent - Multi-Format Content Creation**

---

## Problem Statement

**Current State:** The LLM generates a 200-400 word educational explanation of finance events. This raw output cannot be posted directly to social media.

**What We Need:** Transform the raw LLM explanation into multiple platform-specific content formats:
- **Twitter Thread** (3-5 tweets, 280 chars each)
- **LinkedIn Post** (500-800 words, professional tone)
- **Newsletter Article** (Full HTML article with formatting)

---

## Architecture Overview

### Content Flow

```
Raw LLM Output (200-400 words)
         ↓
    EVALUATION
         ↓
      PASS ✅
         ↓
┌────────────────────────────────────┐
│   CONTENT GENERATION SERVICE       │
│   (Transforms into 3 formats)      │
└────────────────────────────────────┘
         ↓
    ┌────┴────┬────────────┐
    ↓         ↓            ↓
Twitter    LinkedIn    Newsletter
Thread      Post        Article
    ↓         ↓            ↓
APPROVAL  APPROVAL    APPROVAL
    ↓         ↓            ↓
SCHEDULE  SCHEDULE    SCHEDULE
    ↓         ↓            ↓
PUBLISH   PUBLISH     PUBLISH
```

---

## Content Types

### 1. Twitter Thread

**Format:** 3-5 tweets connected in a thread

**Structure:**
```
Tweet 1: Hook (attention grabber)
Tweet 2: Context (what happened)
Tweet 3: Impact (what it means)
Tweet 4: Education (explain concepts)
Tweet 5: CTA (link to website)
```

**Character Limits:**
- 280 chars per tweet
- Leave room for hashtags (2-3)
- Thread indicator (🧵, 👇, etc.)

**Example:**
```
Tweet 1:
🏦 RBI holds repo rate at 6.5% for the 5th time

Here's what this means for your money 🧵👇

---

Tweet 2:
The central bank's keeping borrowing costs steady while watching inflation (currently 5.5%, target: 4%)

---

Tweet 3:
What this means:
• Home loan EMIs stay same
• Savings rates unchanged
• No immediate changes to borrowing costs

---

Tweet 4:
The repo rate is the rate at which RBI lends to banks. When it goes up, loans become expensive. When it stays flat (like now), your EMIs don't change.

---

Tweet 5:
📖 Read full analysis: [link]
#RBI #MonetaryPolicy #Finance
```

### 2. LinkedIn Post

**Format:** Single post, 500-1000 words

**Structure:**
```
1. Headline with emoji
2. Quick summary (1-2 sentences)
3. Context (What happened?)
4. Impact (Bullet points)
5. Educational section (Explain concepts)
6. Bottom line
7. Hashtags (3-5)
8. Link to website
```

**Tone:** Professional, informative, calm

**Example:**
```
📊 RBI Holds Repo Rate Steady at 6.5%

The Reserve Bank of India maintained the repo rate at 6.5% for the fifth consecutive policy meeting. Here's a quick breakdown:

🎯 Why?
The RBI is prioritizing inflation control. While inflation has cooled to 5.5%, it's still above the 4% target. By keeping rates unchanged, the RBI is balancing growth concerns with price stability.

💼 What This Means for You:
• Home loan EMIs remain stable
• Savings account rates unchanged
• No immediate impact on borrowing costs
• Fixed deposit rates likely to stay steady

📈 The Bigger Picture:
This "pause" in rate hikes suggests the RBI believes past rate increases (from 4% to 6.5% since May 2022) are working. The central bank will closely monitor inflation trends before making the next move.

💡 Understanding the Repo Rate:
The repo rate is the interest rate at which RBI lends to commercial banks. When this rate increases, banks pass on higher costs to customers through increased loan rates. When it stays flat, your borrowing costs remain stable.

The key message: Patience. The RBI is waiting for inflation data to guide future decisions.

🔗 Read more: [link]

#Finance #RBI #InterestRates #MonetaryPolicy #IndianEconomy
```

### 3. Newsletter Article

**Format:** HTML email, 400-800 words

**Structure:**
```html
<h1>Headline</h1>
<p><strong>Quick Summary</strong></p>
<h2>What Happened?</h2>
<h2>Why Is This Important?</h2>
<h2>What Does This Mean for You?</h2>
<h2>Understanding [Key Concept]</h2>
<h2>What's Next?</h2>
<p><strong>Bottom Line</strong></p>
<a href="link">Read more on website</a>
```

**Tone:** Educational, conversational, comprehensive

---

## Implementation: Content Generation Service

### Option A: LLM-Based Generation (Recommended)

Use the same LLM (llama3) with specialized prompts to transform raw output into each format.

**Pros:**
- Maintains consistent voice
- Adapts to content naturally
- Handles edge cases well
- Same safety validation applies

**Cons:**
- Additional LLM calls (3x)
- Slower processing (30-60 seconds)
- Need separate validation

### Option B: Template-Based Generation

Use Python templates to reformat raw output.

**Pros:**
- Fast (< 1 second)
- Deterministic output
- No additional LLM calls

**Cons:**
- Rigid formatting
- Poor handling of edge cases
- Requires manual template maintenance

### Recommendation: **Hybrid Approach**

1. Use templates for structure
2. Use LLM for content adaptation
3. Best of both worlds

---

## Backend Implementation

### New Database Table: `generated_content`

```python
class GeneratedContent(Base):
    """Platform-specific generated content."""

    __tablename__ = "generated_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    output_id = Column(UUID(as_uuid=True), ForeignKey("outputs.id"))
    platform = Column(String(50), nullable=False)  # twitter, linkedin, newsletter
    content_type = Column(String(50))  # thread, single_post, article
    content_data = Column(JSONB, nullable=False)  # Format-specific data

    # For Twitter threads
    # content_data = {
    #     "tweets": [
    #         {"order": 1, "text": "Tweet 1 content..."},
    #         {"order": 2, "text": "Tweet 2 content..."},
    #     ],
    #     "total_tweets": 5
    # }

    # For LinkedIn
    # content_data = {
    #     "text": "Full LinkedIn post...",
    #     "hashtags": ["Finance", "RBI"]
    # }

    # For Newsletter
    # content_data = {
    #     "html": "<html>...</html>",
    #     "subject": "Email subject",
    #     "preview_text": "Preview text"
    # }

    word_count = Column(Integer)
    char_count = Column(Integer)
    hashtags = Column(JSONB)

    # Validation
    validation_passed = Column(Boolean, default=False)
    validation_errors = Column(JSONB)

    # Status
    status = Column(String(20), default="generated")  # generated, approved, published

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    output = relationship("Output", back_populates="generated_contents")
```

### Content Generation Service

```python
# services/content_generator.py

from typing import Dict, List
from uuid import UUID
from models.output import Output
from models.generated_content import GeneratedContent
from llm.client import LLMClient

class ContentGeneratorService:
    """Generates platform-specific content from raw LLM output."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_all_formats(self, output: Output) -> Dict[str, GeneratedContent]:
        """Generate content for all platforms."""
        return {
            "twitter": self.generate_twitter_thread(output),
            "linkedin": self.generate_linkedin_post(output),
            "newsletter": self.generate_newsletter_article(output)
        }

    def generate_twitter_thread(self, output: Output) -> GeneratedContent:
        """Generate a Twitter thread (3-5 tweets)."""

        prompt = f"""
Transform the following finance explanation into a Twitter thread.

Original Content:
{output.llm_output}

Requirements:
- Create 3-5 tweets
- Each tweet max 260 characters (leave room for hashtags)
- Tweet 1: Hook with emoji (grab attention)
- Tweet 2: Context (what happened)
- Tweet 3: Impact (what it means - bullet points)
- Tweet 4: Education (explain key concept simply)
- Tweet 5: CTA (link placeholder)
- Use 2-3 relevant hashtags in last tweet only
- Add thread indicator (🧵 or 👇) in first tweet
- Keep same calm, educational tone
- NO advice, NO predictions

Output as JSON:
{{
  "tweets": [
    {{"order": 1, "text": "Tweet 1 text here"}},
    {{"order": 2, "text": "Tweet 2 text here"}},
    ...
  ],
  "hashtags": ["Finance", "RBI"]
}}
"""

        response = self.llm.generate(prompt)
        content_data = self._parse_json_response(response)

        # Validate thread
        self._validate_twitter_thread(content_data)

        return GeneratedContent(
            output_id=output.id,
            platform="twitter",
            content_type="thread",
            content_data=content_data,
            validation_passed=True,
            char_count=sum(len(t["text"]) for t in content_data["tweets"]),
            hashtags=content_data.get("hashtags", [])
        )

    def generate_linkedin_post(self, output: Output) -> GeneratedContent:
        """Generate a LinkedIn post (500-800 words)."""

        prompt = f"""
Transform the following finance explanation into a LinkedIn post.

Original Content:
{output.llm_output}

Requirements:
- Professional tone, informative
- 500-800 words
- Start with headline + emoji
- Use sections with emoji headers
- Include "What This Means for You" with bullet points
- Explain key concepts in simple terms
- End with bottom line summary
- Add 3-5 relevant hashtags at end
- Add link placeholder
- Keep calm, educational tone
- NO advice, NO predictions

Format as single post text.
"""

        response = self.llm.generate(prompt)

        # Extract hashtags
        hashtags = self._extract_hashtags(response)

        return GeneratedContent(
            output_id=output.id,
            platform="linkedin",
            content_type="single_post",
            content_data={"text": response, "hashtags": hashtags},
            validation_passed=True,
            word_count=len(response.split()),
            char_count=len(response),
            hashtags=hashtags
        )

    def generate_newsletter_article(self, output: Output) -> GeneratedContent:
        """Generate newsletter article (HTML)."""

        prompt = f"""
Transform the following finance explanation into a newsletter article.

Original Content:
{output.llm_output}

Requirements:
- Comprehensive, 400-800 words
- HTML format with proper tags (h1, h2, p, ul, li, strong)
- Structure:
  * <h1>Headline</h1>
  * <p><strong>Quick Summary</strong> (1-2 sentences)</p>
  * <h2>What Happened?</h2>
  * <h2>Why Is This Important?</h2>
  * <h2>What Does This Mean for You?</h2> (with bullet list)
  * <h2>Understanding [Key Concept]</h2>
  * <h2>What's Next?</h2>
  * <p><strong>Bottom Line</strong></p>
- Use simple language
- Explain all concepts
- NO advice, NO predictions
- Include link placeholder at end

Also generate:
- Email subject line (max 60 chars)
- Preview text (max 100 chars)

Output as JSON:
{{
  "html": "HTML content here",
  "subject": "Subject line",
  "preview_text": "Preview text"
}}
"""

        response = self.llm.generate(prompt)
        content_data = self._parse_json_response(response)

        return GeneratedContent(
            output_id=output.id,
            platform="newsletter",
            content_type="article",
            content_data=content_data,
            validation_passed=True,
            word_count=len(content_data["html"].split()),
            char_count=len(content_data["html"])
        )

    def _validate_twitter_thread(self, content_data: Dict):
        """Validate Twitter thread meets requirements."""
        tweets = content_data.get("tweets", [])

        if len(tweets) < 3 or len(tweets) > 5:
            raise ValueError(f"Thread must have 3-5 tweets, got {len(tweets)}")

        for tweet in tweets:
            text = tweet.get("text", "")
            if len(text) > 280:
                raise ValueError(f"Tweet {tweet['order']} exceeds 280 chars: {len(text)}")

        # Check for forbidden language
        forbidden = ["buy", "sell", "should invest", "guaranteed"]
        for tweet in tweets:
            text = tweet.get("text", "").lower()
            for word in forbidden:
                if word in text:
                    raise ValueError(f"Forbidden word '{word}' in tweet {tweet['order']}")

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        import re
        return re.findall(r'#(\w+)', text)

    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response."""
        import json
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return json.loads(response.strip())
```

### API Endpoints

```python
# api/routes/content_generation.py

@router.post("/generate/{output_id}")
async def generate_content(output_id: str):
    """Generate content for all platforms from a PASS evaluation."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Get output
        output = repo.outputs.get_by_id(UUID(output_id))
        if not output:
            raise HTTPException(404, "Output not found")

        # Check if already generated
        existing = repo.generated_content.get_by_output_id(output.id)
        if existing:
            return {"message": "Already generated", "content": existing}

        # Generate content
        generator = ContentGeneratorService(llm_client)
        generated = generator.generate_all_formats(output)

        # Save to database
        for platform, content in generated.items():
            db.add(content)
        db.commit()

        return {
            "message": "Content generated",
            "twitter": generated["twitter"].to_dict(),
            "linkedin": generated["linkedin"].to_dict(),
            "newsletter": generated["newsletter"].to_dict()
        }

@router.get("/preview/{generated_content_id}")
async def preview_content(generated_content_id: str):
    """Preview generated content."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        content = repo.generated_content.get_by_id(UUID(generated_content_id))

        if not content:
            raise HTTPException(404, "Content not found")

        return content.to_dict()

@router.put("/edit/{generated_content_id}")
async def edit_content(
    generated_content_id: str,
    new_content_data: dict
):
    """Edit generated content before approval."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        content = repo.generated_content.get_by_id(UUID(generated_content_id))

        if not content:
            raise HTTPException(404, "Content not found")

        # Update content
        content.content_data = new_content_data
        content.updated_at = datetime.utcnow()

        # Re-validate
        if content.platform == "twitter":
            ContentGeneratorService._validate_twitter_thread(new_content_data)

        db.commit()

        return {"message": "Content updated", "content": content.to_dict()}
```

---

## Frontend Implementation

### Content Preview Component

```typescript
// dashboard/src/components/ContentPreview.tsx

import { GeneratedContent } from "@/api/client"

interface Props {
  content: GeneratedContent
}

export function ContentPreview({ content }: Props) {
  if (content.platform === "twitter") {
    return <TwitterThreadPreview tweets={content.content_data.tweets} />
  }

  if (content.platform === "linkedin") {
    return <LinkedInPostPreview text={content.content_data.text} />
  }

  if (content.platform === "newsletter") {
    return <NewsletterPreview html={content.content_data.html} />
  }

  return null
}

function TwitterThreadPreview({ tweets }) {
  return (
    <div className="space-y-3">
      {tweets.map((tweet, idx) => (
        <div key={idx} className="border rounded-lg p-4 bg-white shadow-sm">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
              FA
            </div>
            <div className="flex-1">
              <div className="font-bold">FinAgent</div>
              <div className="text-sm text-gray-500">@finagent_ai</div>
              <div className="mt-2 whitespace-pre-wrap">{tweet.text}</div>
              <div className="mt-2 text-xs text-gray-400">
                {tweet.text.length}/280 characters
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function LinkedInPostPreview({ text }) {
  return (
    <div className="border rounded-lg p-6 bg-white shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded bg-blue-700 flex items-center justify-center text-white font-bold">
          FA
        </div>
        <div className="flex-1">
          <div className="font-bold">FinAgent</div>
          <div className="text-sm text-gray-500">Finance Education Platform</div>
          <div className="mt-4 whitespace-pre-wrap">{text}</div>
          <div className="mt-4 text-xs text-gray-400">
            {text.split(' ').length} words · {text.length} characters
          </div>
        </div>
      </div>
    </div>
  )
}

function NewsletterPreview({ html }) {
  return (
    <div className="border rounded-lg p-6 bg-white shadow-sm">
      <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}
```

### Updated Approval Workflow

```typescript
// dashboard/src/pages/Outputs.tsx (Enhanced)

// After evaluation PASS, generate content
const handleApprove = async (outputId: string) => {
  // Generate content for all platforms
  await contentApi.generate(outputId)

  // Show content preview modal
  setShowContentPreview(true)
}

// In modal, show generated content for all 3 platforms
<Tabs>
  <TabsList>
    <TabsTrigger value="twitter">Twitter Thread</TabsTrigger>
    <TabsTrigger value="linkedin">LinkedIn Post</TabsTrigger>
    <TabsTrigger value="newsletter">Newsletter</TabsTrigger>
  </TabsList>

  <TabsContent value="twitter">
    <ContentPreview content={generatedContent.twitter} />
    <Button onClick={() => approveForPlatform("twitter")}>
      Approve for Twitter
    </Button>
  </TabsContent>

  <TabsContent value="linkedin">
    <ContentPreview content={generatedContent.linkedin} />
    <Button onClick={() => approveForPlatform("linkedin")}>
      Approve for LinkedIn
    </Button>
  </TabsContent>

  <TabsContent value="newsletter">
    <ContentPreview content={generatedContent.newsletter} />
    <Button onClick={() => approveForPlatform("newsletter")}>
      Approve for Newsletter
    </Button>
  </TabsContent>
</Tabs>
```

---

## Workflow Integration

### Updated MVP Flow

```
1. RSS Event → LLM → Raw Explanation (200-400 words)
2. Human Evaluation → PASS ✅
3. [NEW] Content Generation → Generate 3 formats
4. [NEW] Content Preview → Show all 3 formats to editor
5. [NEW] Platform Selection → Editor chooses which platforms to publish
6. [NEW] Content Editing (optional) → Edit individual platform content
7. Approval → Editor approves each platform version
8. Scheduling → Schedule each platform independently
9. Publishing → Publish to selected platforms
```

### Approval Options

Editor can:
1. **Approve All** - Approve all 3 platform versions at once
2. **Approve Selected** - Choose specific platforms (e.g., only Twitter + LinkedIn)
3. **Edit & Approve** - Edit content for specific platform, then approve
4. **Reject** - Reject all versions, go back to evaluation

---

## Testing Strategy

### Unit Tests

```python
def test_twitter_thread_generation():
    output = create_test_output()
    content = generator.generate_twitter_thread(output)

    assert content.platform == "twitter"
    assert len(content.content_data["tweets"]) >= 3
    assert len(content.content_data["tweets"]) <= 5

    for tweet in content.content_data["tweets"]:
        assert len(tweet["text"]) <= 280

def test_forbidden_language_detection():
    output = create_test_output_with_advice()

    with pytest.raises(ValueError, match="Forbidden word"):
        generator.generate_twitter_thread(output)
```

### Integration Tests

- Generate content from real PASS evaluation
- Verify all 3 formats generated
- Validate format constraints
- Test editing workflow
- Test approval workflow

---

## Performance Considerations

### LLM Call Optimization

**Problem:** 3 LLM calls per content piece (Twitter, LinkedIn, Newsletter)

**Solutions:**
1. **Parallel Generation** - Generate all 3 formats simultaneously
2. **Caching** - Cache generated content, regenerate only on edit
3. **Background Processing** - Generate async, notify when ready

### Estimated Timing

- Raw LLM generation: ~20 seconds
- Content generation (3 formats): ~60 seconds (parallel) or ~180 seconds (sequential)
- **Recommendation:** Run in background, notify editor when ready

---

## Content Quality Assurance

### Validation Checks

Before allowing approval:
- ✅ Character limits respected
- ✅ No forbidden language (advice, predictions)
- ✅ Required sections present
- ✅ Hashtags within limits (2-5)
- ✅ Links properly formatted
- ✅ Emojis appropriate and minimal
- ✅ Tone matches brand voice

### Human Review Points

Editors should check:
1. **Accuracy** - Facts correctly represented
2. **Clarity** - Concepts explained simply
3. **Tone** - Calm, educational, non-alarmist
4. **Platform Fit** - Content appropriate for each platform
5. **Engagement** - Hook compelling, CTA clear

---

## Next Steps

1. **Implement `GeneratedContent` table** - Database migration
2. **Build Content Generator Service** - LLM-based generation
3. **Create API endpoints** - Generate, preview, edit
4. **Build frontend components** - Preview UI for each platform
5. **Update approval workflow** - Integrate content generation step
6. **Test with real data** - Generate content from 40 PASS evaluations
7. **Iterate on prompts** - Refine based on output quality

---

**End of Content Generation Architecture**

*Created: January 21, 2026*
*Version: 1.0*
