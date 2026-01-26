# Twitter Content Redesign Plan
**Project**: FinAgent - Contextual Finance Education System
**Created**: January 25, 2026
**Status**: DRAFT - In Discussion
**Version**: 1.0

---

## Vision Statement

**"Contextual Finance Education Through News Analysis"**

We're not just reporting finance news — we're teaching finance concepts through current events, making complex financial topics understandable for everyday people.

---

## Content Niche Definition

### 5 Core Pillars ✓ FROZEN

- [x] **Financial Terms Explained**: Simple definitions for everyday people
- [x] **Policy/Strategy Explanation**: How mechanisms work and why they exist
- [x] **Historical Comparison**: How current policies differ from previous ones
- [x] **Current Context Analysis**: Why this matters NOW in today's market/economy
- [x] **Impact Analysis**: What this means for markets/businesses/people

### Content Philosophy ✓ FROZEN

| Principle | Description |
|-----------|-------------|
| **Educational** | Teaches concepts, not just reports facts |
| **Lightly Opinionated** | Thoughtful perspective without strong bias |
| **Data-Backed** | Claims supported by data |
| **Curiosity-Driven** | Encourages learning and exploration |
| **Calm** | No hype, fear, or urgency |
| **Human-Like** | Natural, conversational tone |

### Strict Prohibitions ✓ FROZEN

- ❌ No investment advice ("buy", "sell", "hold")
- ❌ No predictions or forecasts
- ❌ No guarantees or certainty claims
- ❌ No political opinions
- ❌ No sensationalism or clickbait

---

## Two-Track Content System

### Track 1: Event-Driven (Current - Needs Fix) 🔴 PRIORITY

**Input**: RSS feeds (RBI, Fed, Bloomberg, SEBI, etc.)
**Output**: "What happened + Why it matters + Context + Education"
**Example Topics**: Rate decisions, bank penalties, policy changes, trade deals

**Status**: Infrastructure exists, content quality needs complete redesign

### Track 2: Evergreen Education (Future) 🟡 POST-MVP

**Input**: Structured knowledge (Wikipedia, Investopedia, OECD, IMF)
**Output**: "What is X + How it works + Examples + Comparisons"
**Example Topics**: Tax systems, investment types, financial instruments

**Status**: Not implemented, requires new infrastructure

---

## Current Problems (Track 1)

### Problem 1: Analyst Voice, Not Educator Voice ❌

**Current Output**:
```
Polymarket's pricing reflects a 77% probability of a January US gov't
shutdown, up markedly from recent levels. While often linked to former
President Trump's remarks, the shift underscores trader sentiment—distinct
from forecasts or guarantees. #Polymarket ⚖️
```

**Issues**:
- [ ] Assumes reader knows what Polymarket is
- [ ] No concept explanation (what are prediction markets?)
- [ ] Abstract meta-commentary ("underscores trader sentiment")
- [ ] Analyst jargon, not simple language
- [ ] Not educational

### Problem 2: Missing Educational Layer ❌

Current tweets report what happened but don't teach concepts:
- [ ] No term definitions
- [ ] No mechanism explanations
- [ ] No historical context
- [ ] No comparison to similar events

### Problem 3: Technical Rule Violations ❌

Despite 65-line prompt with "FORBIDDEN" language:
- [ ] Still adds hashtags (#Polymarket)
- [ ] Still exceeds character limit (275 vs 260)
- [ ] Still uses abstract language
- [ ] Still has factual errors ("former President" vs "current President")

### Problem 4: Prompt Engineering Limits Reached ❌

**Diagnosis**: LLM training biases (analyst style, hashtag habits) are stronger than prompt instructions.

**Evidence**:
- 65-line complex prompt fails to enforce basic rules
- "FORBIDDEN" and "BANNED" language ignored
- Technical constraints met, but content quality missed

---

## Proposed Solution: Track 1 Redesign

### Phase 1: Prompt Redesign 📝 IN PROGRESS

**Objective**: Redesign Twitter prompt to generate educational, contextual content that matches our niche.

#### Key Changes Needed:

- [ ] **1. Shift from "Analyst" to "Educator" voice**
  - Add explicit "explain concepts" instruction
  - Require simple language (8th grade reading level)
  - Ban jargon unless explained

- [ ] **2. Add Educational Requirements**
  - MUST explain any financial term used
  - MUST provide context (why this matters now)
  - SHOULD compare to historical precedent when relevant
  - MAY add simple examples

- [ ] **3. Simplify Rule Structure**
  - Cut from 65 lines to ~30 lines
  - Focus on content quality over technical constraints
  - Use positive examples instead of negative bans

- [ ] **4. Add Concrete Examples**
  - Show 3-5 example tweets in the prompt
  - Demonstrate educational vs analyst style
  - Illustrate concept explanation technique

#### Example of Target Output:

```
RBI fined a cooperative bank ₹1L for lending too much to other
banks—breaching "exposure limits."

These limits cap how much a bank can lend to any single borrower
or bank. Think "don't put all eggs in one basket." RBI tightened
these rules in 2014 after several bank failures.
```

**Why this is better**:
- ✅ Explains the term "exposure limits"
- ✅ Uses simple analogy ("eggs in one basket")
- ✅ Provides historical context (2014 rule change)
- ✅ Shows why the rule exists (prevent failures)
- ✅ Calm, educational tone
- ✅ No jargon, no hashtags

### Phase 2: Validation Layer (Optional) 🔧 DISCUSSION NEEDED

**Decision Point**: Do we rely on prompt alone, or add post-generation validation?

#### Option A: Prompt-Only (Simpler)
- [ ] Redesign prompt
- [ ] Test with 10-20 events
- [ ] Accept 10-20% failure rate
- [ ] Rely on HITL to catch issues

**Pros**: Simple, no code changes
**Cons**: Will still have failures

#### Option B: Validation Layer (Robust)
- [ ] Redesign prompt
- [ ] Add TwitterValidationAdapter
- [ ] Check: hashtags, length, abstractions
- [ ] Regenerate on failure with feedback

**Pros**: Higher quality, catches errors
**Cons**: More complex, slower generation

**Status**: ⏸️ PENDING USER DECISION

### Phase 3: Testing & Iteration 🧪 PLANNED

- [ ] Test new prompt on 10 diverse events
- [ ] Evaluate against checklist:
  - [ ] Educational (teaches concept)?
  - [ ] Simple language (8th grade)?
  - [ ] Contextual (why it matters)?
  - [ ] Complete sentences (no truncation)?
  - [ ] No hashtags (or entity-only)?
  - [ ] No abstract language?
  - [ ] Factually accurate?
  - [ ] Calm, non-hype tone?

- [ ] Iterate based on failures
- [ ] Achieve 80%+ quality threshold
- [ ] Deploy to production

---

## Track 2: Evergreen Education (Future Roadmap)

### Requirements (Not Yet Implemented)

#### 1. Knowledge Source Ingestion
- [ ] Wikipedia API integration
- [ ] Investopedia scraping/API
- [ ] OECD/IMF data access
- [ ] PDF document processing
- [ ] Knowledge base storage

#### 2. Topic Selection System
- [ ] Concept taxonomy (terms, strategies, systems)
- [ ] Topic priority queue
- [ ] Frequency management (avoid repeats)
- [ ] Seasonal relevance (tax season = tax topics)

#### 3. Content Generation
- [ ] Concept-based prompt template
- [ ] Multi-paragraph format (threads)
- [ ] Example/comparison generation
- [ ] Cross-reference to related concepts

#### 4. Scheduling System
- [ ] Not tied to RSS events
- [ ] Fill gaps between event content
- [ ] Maintain posting frequency
- [ ] Smart time distribution

### Example Topics Queue

**Tax & Policy**:
- Progressive vs flat tax systems
- Direct vs indirect taxes
- Tax havens and their impact
- Capital gains taxation

**Investment Basics**:
- What is an ETF?
- Mutual funds vs index funds
- Bonds vs stocks
- Dividend investing

**Market Mechanisms**:
- How stock exchanges work
- Bid-ask spread explained
- Market makers role
- Circuit breakers

**Financial Instruments**:
- Derivatives basics
- Options vs futures
- Swaps explained
- Repo rate mechanism

---

## Success Metrics

### Track 1 (Event-Driven)

**Quality Metrics** (Target):
- [ ] 80%+ educational (teaches concept)
- [ ] 90%+ simple language (no unexplained jargon)
- [ ] 70%+ contextual (historical/current comparison)
- [ ] 95%+ technically compliant (length, format, no hashtags)
- [ ] 100% factually accurate
- [ ] 0% advice/predictions

**Engagement Metrics** (Post-Launch):
- [ ] Follower growth rate
- [ ] Engagement rate (likes, retweets, replies)
- [ ] Question quality (are people asking deeper questions?)
- [ ] Retention (do people keep following?)

### Track 2 (Evergreen Education)

**Coverage Metrics**:
- [ ] X concepts explained per month
- [ ] Y topic categories covered
- [ ] Z% of common finance terms defined

**Utility Metrics**:
- [ ] Reference rate (are people saving/sharing these?)
- [ ] Search traffic (organic discovery?)
- [ ] Educational impact (follower understanding?)

---

## Timeline & Milestones

### Week 1: Track 1 Prompt Redesign ⏱️ CURRENT
- [x] Finalize vision and niche (✅ DONE - Jan 25, 2026)
- [x] Design new prompt structure (✅ DONE - Jan 25, 2026)
- [x] Create example tweets for prompt (✅ DONE - Included in prompt)
- [x] Implement prompt changes (✅ DONE - v2.0-educator in config/prompts.py)
- [ ] Test on 5 sample events (📝 NEXT)

### Week 2: Track 1 Testing & Iteration
- [ ] Test on 20 diverse events
- [ ] Evaluate quality metrics
- [ ] Identify failure patterns
- [ ] Iterate prompt
- [ ] Achieve 80% quality threshold

### Week 3: Track 1 Validation Decision
- [ ] Decide: Prompt-only vs Validation layer
- [ ] If validation: Implement TwitterValidationAdapter
- [ ] Final testing round
- [ ] Deploy to production

### Week 4-8: Track 1 Monitoring & Refinement
- [ ] Monitor content quality
- [ ] Track engagement metrics
- [ ] Gather user feedback
- [ ] Refine based on data

### Month 2+: Track 2 Planning
- [ ] Design knowledge ingestion system
- [ ] Build topic selection system
- [ ] Implement concept generation
- [ ] Test evergreen content
- [ ] Launch Track 2

---

## Decision Log

### Decisions Made ✅

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-25 | Focus on Track 1 before Track 2 | Track 1 is broken and needs immediate fix. Track 2 requires significant infrastructure. |
| 2026-01-25 | Redesign prompt for educational voice | Current analyst voice doesn't match niche vision. Need educator tone. |
| 2026-01-25 | Niche definition finalized | "Contextual Finance Education Through News Analysis" with 5 pillars |

### Decisions Pending ⏸️

| Decision | Options | Status |
|----------|---------|--------|
| Validation Layer | A) Prompt-only, B) Add validation adapter | PENDING USER INPUT |
| Prompt Length | A) 30 lines, B) 40 lines, C) Keep 65 lines | PENDING DESIGN |
| Example Count in Prompt | A) 3 examples, B) 5 examples, C) 10 examples | PENDING DESIGN |
| Character Limit Priority | A) Strict 260, B) Allow 280 with complete sentences | PENDING DISCUSSION |

---

## Open Questions

### Track 1 Questions
- [ ] Should we include historical data/comparisons in every tweet, or only when relevant?
- [ ] What's the acceptable failure rate for quality? (10%? 20%?)
- [ ] Do we prioritize completeness over brevity if we can't fit context in 260 chars?
- [ ] Should we allow exceptions for hashtags on regulatory entities (#RBI, #SEBI)?

### Track 2 Questions
- [ ] Which knowledge sources should we prioritize? (Wikipedia, Investopedia, official docs?)
- [ ] How often should we post evergreen content vs event content? (50/50? 30/70?)
- [ ] Should evergreen content be threads or single tweets?
- [ ] Do we need a concept dependency graph (explain basics before advanced topics)?

---

## Resources Needed

### Track 1 Redesign
- [ ] Time: 2-3 hours for prompt redesign
- [ ] Testing: 20-30 sample events
- [ ] Evaluation: Manual quality review (~1 hour)

### Track 2 Implementation (Future)
- [ ] Development time: 20-40 hours
- [ ] Knowledge source APIs/subscriptions
- [ ] Storage for concept database
- [ ] Content scheduling system
- [ ] Testing and iteration time

---

## Risks & Mitigation

### Risk 1: Prompt Redesign May Not Improve Quality
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Test incrementally with small changes
- Have rollback plan to current prompt
- Consider validation layer as backup

### Risk 2: Educational Content May Be Too Long for Twitter
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Use thread format for complex topics
- Prioritize most important educational point
- Link to longer explanations elsewhere

### Risk 3: LLM May Still Ignore Prompt Rules
**Likelihood**: Medium (based on current experience)
**Impact**: High
**Mitigation**:
- Implement validation layer
- Try different LLM models (GPT-4, Claude)
- Use few-shot learning with examples

### Risk 4: Track 2 Infrastructure Too Complex
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Start with simple Wikipedia API
- Incremental implementation
- Manual curation initially, automate later

---

## Next Steps (Immediate)

1. [x] **User Approval**: Review and approve this plan ✅ DONE
2. [x] **Prompt Redesign**: Create new Twitter generation prompt ✅ DONE (v2.0-educator)
3. [x] **Example Creation**: Write 5 example tweets demonstrating educational style ✅ DONE (3 good + 2 bad examples in prompt)
4. [ ] **Testing**: Generate tweets for 5-10 sample events 📝 NEXT STEP
5. [ ] **Evaluation**: Review quality against checklist
6. [ ] **Iteration**: Refine prompt based on test results
7. [ ] **Validation Decision**: Choose Option A (prompt-only) or Option B (validation layer) - decide after testing
8. [ ] **Production Deployment**: Deploy if quality threshold met (80%+ educational)

---

## Appendix A: Example Tweets (Target Quality)

### Example 1: RBI Bank Penalty
**Event**: RBI penalizes cooperative bank for exposure limit breach

**Current (Bad)**:
```
RBI imposed ₹1L penalty on Sri Satya Sai Bank for breaching exposure limits.
```

**Target (Good)**:
```
RBI fined a cooperative bank ₹1L for lending too much to other
banks—breaching "exposure limits."

These limits cap how much a bank can lend to any single borrower.
Think "don't put all eggs in one basket." RBI tightened these
rules in 2014 after several bank failures.
```

### Example 2: Fed Rate Decision
**Event**: Federal Reserve holds rates steady

**Current (Bad)**:
```
Fed holds rates at 5.5%, citing persistent inflation concerns.
```

**Target (Good)**:
```
Fed kept interest rates at 5.5%—unchanged since July 2023.

The fed funds rate is what banks charge each other overnight. When
high, it makes all loans costlier, slowing spending to cool inflation.
US rate is now higher than EU (4.0%) but matches Canada.
```

### Example 3: Prediction Market Signal
**Event**: Polymarket shows 77% shutdown odds

**Current (Bad)**:
```
Polymarket's pricing reflects a 77% probability of a January US
gov't shutdown, up markedly from recent levels.
```

**Target (Good)**:
```
Prediction markets now show 77% chance of a US government shutdown
this month—up sharply.

These are betting markets where traders put money on outcomes. The
price reflects collective bets, not guarantees. Often moves with
political news.
```

---

## Appendix B: Voice Guidelines

### Educational Voice Characteristics

**DO**:
- Explain every financial term used
- Use simple analogies ("like X")
- Provide concrete examples
- Compare to familiar concepts
- Ask curiosity-driven questions
- Use conversational tone

**DON'T**:
- Assume prior knowledge
- Use unexplained jargon
- Be overly formal
- Sound like a textbook
- Be condescending
- Over-simplify to the point of inaccuracy

### Tone Examples

**Too Analyst** ❌:
> "The monetary policy committee's decision to maintain the repo rate at 6.5% reflects concerns about persistent core inflation despite easing headline CPI."

**Too Casual** ❌:
> "So like, RBI totally kept rates the same lol because inflation is still being annoying"

**Just Right** ✅:
> "RBI kept its key rate (repo rate) at 6.5%—what banks pay to borrow from RBI. When high, loans cost more, slowing spending to fight inflation. Rate unchanged since Feb due to stubborn food prices."

---

*This plan is a living document. Update as decisions are made and requirements change.*

**Last Updated**: January 25, 2026
**Next Review**: After Phase 1 Testing
