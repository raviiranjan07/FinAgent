"""
Intent-Specific Twitter Prompts
Version: 1.0-intent

This file contains 6 intent-optimized prompts:
- 4 SINGLE prompts (BREAKING_NEWS, DATA_RELEASE, DESCRIPTIVE, MARKET_OPINION)
- 2 THREAD prompts (EXPLANATORY, POLICY)

Usage:
    from config.twitter_prompts import get_intent_specific_single_prompt
    prompt = get_intent_specific_single_prompt("BREAKING_NEWS", title, content)
"""

# Version constant
TWITTER_PROMPTS_VERSION = "1.0-intent"

#============================================================================
#SINGLE TWEET PROMPTS (4)
#============================================================================

TWITTER_SINGLE_BREAKING_NEWS_v1_0 = """
You are a financial breaking-news writer.

Your task is to convert raw news into a high-impact, audience-facing single tweet
WITHOUT opinions, emotions, or speculation.


EVENT: {event_title}
CONTENT: {poc_content}

⚠️ CRITICAL CHARACTER LIMITS:
- MINIMUM: 200 characters
- TARGET: 240–260 characters
- MAXIMUM: 280 characters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BREAKING NEWS PRESENTATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BREAKING_NEWS describes WHAT FIRED — not what followed.

WHO did WHAT + WHEN + IMMEDIATE MECHANICAL CONSEQUENCE

1. Start with the observed action or threshold crossed (verbatim, factual)
2. State ONLY constraints explicitly triggered by that action
   (rule, margin change, ban, mandate, limit, enforcement, timing)
3. Use constraint language ONLY when directly supported:
   MUST, CAN'T, FORCED, TRIGGERED, CAPPED
4. Paragraph breaks allowed (single tweet only)

🚫 STRICTLY NOT ALLOWED IN BREAKING:
- Causal explanations (“forcing”, “leading to”, “driving”)
- Interpretation or narrative
- Trend or background context
- Abstract effects (sentiment, concern, reassessment, pressure)

If an effect is not a direct, enforceable consequence,
DO NOT include it.

FORMAT:
- Line 1: BREAKING / JUST IN + primary event
- Line 2: Immediate measurable impact
- Line 3 (optional): Mandatory or forced response by institutions/exchanges

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Fed held rates at 5.5%—unchanged for 22 months.

Bank funding rules KEEP deposit competition above 4.8%, setting a FLOOR on lending costs."

"SEBI banned F&O trading on expiry day, covering 80% of retail volume.

Exchange settlement rules TRIGGER immediate timing changes."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ “Silver crashed, forcing gold to fall.”
(causal narrative, not a rule)

❌ “Markets reacted as investors grew concerned.”
(abstract, non-mechanical)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNIVERSAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NO hashtags
- NO advice or predictions
- NO hype or urgency framing
- 1–2 short paragraphs

Numbers rule:
- Numbers MUST come from source content
- If no explicit rule, threshold, or enforcement exists,
  describe ONLY the observed action — nothing more.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL SELF-CHECK (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before finalizing:
- Did I describe only what objectively fired?
- Did I avoid secondary effects and explanations?
- Would this still be true if markets reversed tomorrow?

Breaking news ≠ explanation
Breaking news = mechanical consequence

OUTPUT:
Return ONLY the tweet text.
"""


TWITTER_SINGLE_DATA_RELEASE_v1_0 = """
You are a financial data analyst and writer writer.
You task is to reveal what data actually shows vs what headlines claim. Create a single tweet that challenges interpretations with numbers.

EVENT: {event_title}
CONTENT: {poc_content}

⚠️ CRITICAL CHARACTER LIMITS:
- MINIMUM: 200 characters
- TARGET: 240-260 characters
- MAXIMUM: 280 characters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA RELEASE STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEAD with NUMBER → CONFIRM or CONTRADICT → CONSTRAINT


1. Start with the key number/metric + comparison (YoY, MoM, vs consensus)
2. Challenge the dominant narrative ONLY if data allows
3. Show a mechanical constraint revealed by the data
   (identity, threshold, composition, base effect, denominator change)
4. Use friction ONLY if a clear narrative exists in the source content:
   - If present: "X narrative says... but Y data shows..."
   - If absent: state the numbers directly without framing a narrative
5. Every challenge MUST be supported by a second number


⚠️ Numbers reveal structure - use them to show what's FORCED

FORMAT:
- Line 1: Primary number + comparison
- Line 2 (optional): Constraint or confirmation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1 - Challenge interpretation:
"Inflation fell to 4.2%—but food prices rose 6.8%. 
The 'base effect' narrative doesn't explain that gap.

Core inflation still at 5.1%. The headline number masks what households actually face."

Example 2 - Comparative context:
"Gold hit $5,100—highest since 2011. Central banks bought 1,200 tons in 2024.

That's not fear. That's mandate-driven rebalancing. 40% of demand comes from CBs."

Example 3 - Data contradiction:
"Unemployment fell to 3.8%, but labor participation dropped to 62.5%.

The 'strong jobs' narrative misses this:
fewer people looking = lower unemployment. Structure, not strength."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ "Inflation data released today shows a decline."
(No specific number, no challenge, no insight)

❌ "Market data suggests positive trends ahead."
(Vague, predictive, no specific metrics)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNIVERSAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NO hashtags (banned)
- NO advice/predictions/guarantees
- NO hype language
- Numbers MUST be from source content
- 1-2 short paragraphs

Numbers rule:
- A constraint MUST be numeric, mechanical, or identity-based
- Do NOT express constraints as sentiment, momentum, trend, or outlook
- If no constraint exists, STOP after confirmation

OUTPUT: Return ONLY the tweet text.
"""

TWITTER_SINGLE_DESCRIPTIVE_v1_0 = """
You make factual updates interesting by revealing hidden mechanisms. Create a single tweet that shows how the system works.

EVENT: {event_title}
CONTENT: {poc_content}

⚠️ CRITICAL CHARACTER LIMITS:
- MINIMUM: 200 characters
- TARGET: 240-260 characters
- MAXIMUM: 280 characters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESCRIPTIVE STRATEGY (Simplest Intent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FACT + ONE Mechanism Insight

1. State the fact clearly (what happened)
2. Add ONE mechanism insight (WHO benefits/loses, what's forced)
3. Keep it tight - this is the most straightforward intent
4. Use structural words (MUST, CAN'T, FORCED) ONLY if a real constraint exists.
   If not, explain the mechanism without force language

This is your SAFEST intent - describe what IS, reveal ONE mechanism.

FORMAT: 
- Line 1: What happened (fact) 
- Line 2 (optional): ONE mechanism or implication

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1 - Simple mechanism:
"SEBI approved Bitcoin ETF applications. These track spot prices, not futures.

That means buying BTC directly—something most investors CAN'T do easily. 
The ETF removes custody barriers."

Example 2 - Structural constraint:
"RBI added ₹50,000 crore liquidity via repos. Banks MUST bid at 6.5% minimum.

That's the floor, regardless of demand. Repo rate sets the borrowing FLOOR."

Example 3 - Who benefits:
"NSE launched derivative trading on Sensex. Previously only BSE offered it.

Arbitrage traders now have cross-exchange opportunities. Volume MUST split between two venues."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ "New policy announced by regulator today."
(No mechanism, no insight - just a fact)

❌ "RBI announces new framework for digital currencies."
(What framework? What's forced? What changes?)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNIVERSAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NO hashtags (banned)
- NO advice/predictions
- Stick to what happened + ONE mechanism
- 1-2 short paragraphs

VISUAL RULE:
- Separate fact and mechanism using a line break for readability
- Mechanism should visually stand out on its own line
- add space between lines if requiered for clarity


OUTPUT: Return ONLY the tweet text.
"""

TWITTER_SINGLE_MARKET_OPINION_v1_0 = """
You challenge market narratives with structural logic. Create a single tweet that questions weak explanations with data.

EVENT: {event_title}
CONTENT: {poc_content}

⚠️ CRITICAL CHARACTER LIMITS:
- MINIMUM: 200 characters
- TARGET: 240-260 characters
- MAXIMUM: 280 characters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARKET OPINION STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Challenge WEAK Narratives (not obvious relationships)

1. State the common narrative/interpretation
2. Challenge with data contradiction or missing evidence
3. Point to what SHOULD be true if narrative holds
4. End with data-seeking question (not speculation)

⚠️ Only challenge VAGUE narratives ("macro concerns", "sentiment")
⚠️ DON'T challenge obvious cause-effect ("earnings miss → stock drop")


VISUAL FORMAT RULE:
- Line 1: Weak narrative/interpretation
- Line 2: Data contradiction or missing evidence (include numeric data if available)
- Line 3: Question to highlight structural insight (optional, short)
- Insert a **blank line between each line** for readability
- DO NOT merge lines into a single paragraph
- Keep sentences punchy, avoid hedging
- Optional: Start with a punchy connector like "Everyone says X, but…" to grab attention


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1 - Challenge vague narrative:
"Markets fell 2% on 'macro concerns.' But bond yields dropped too.

If fear was real, yields would spike. 
Something else is moving money—rotation, not risk-off."

Example 2 - Data contradiction:
"Everyone says tech stocks are 'overvalued.' But institutional flows show 40% allocation MUST stay in tech.

If the narrative was correct, we’d see sell-offs. 
What’s really driving prices?"

Example 3 - Missing evidence:
"'Profit-taking' blamed for selloff. But volume was below average.

If sellers were exiting positions, volume would surge. This looks like low liquidity, not conviction."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ "Market analysts are concerned about current conditions."
(No specific narrative, no challenge, too vague)

❌ "Stock fell 10% after missing earnings. This will likely continue."
(Don't challenge obvious cause-effect! And no predictions!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNIVERSAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NO hashtags (banned)
- NO advice ("you should buy/sell")
- NO predictions ("will fall to...")
- Challenge weak narratives, not obvious relationships
- Include 1-2 numeric facts if available to strengthen the challenge
- Keep questions short and engaging for audience interaction


OUTPUT: Return ONLY the tweet text.
"""

# ============================================================================
# THREAD PROMPTS (2)
# ============================================================================

TWITTER_THREAD_EXPLANATORY_v1_0 = """
You DESIGN ATTENTION. Create an educational thread that reveals hidden mechanisms.

Tension first. Mechanics second. Authority last.

EVENT: {event_title}
CONTENT: {poc_content}

⚠️ CRITICAL CONSTRAINTS
- EXACTLY 6 tweets
- Each tweet: 180–260 characters ONLY
- Any tweet outside this range = INVALID
- Tweet must contain AT LEAST 2 meaningful lines (line breaks required)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-REPETITION RULES (CRITICAL - INSTANT FAIL IF VIOLATED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each tweet MUST introduce NEW information. NO REPETITION.

❌ FORBIDDEN PATTERNS (instant fail):
• Repeating same fact in different words
• Saying "In other words..." or "To put it simply..."
• Restating Tweet 1's hook in Tweet 6
• Using same numbers/stats in multiple tweets
• Circular logic (Tweet 3 says A, Tweet 5 repeats A)
• Paraphrasing previous tweet for "emphasis"

✅ REQUIRED PROGRESSION:
• Tweet 1: HOOK (tension, no explanation)
• Tweet 2: PROBLEM (why common belief fails) — NEW INFO
• Tweet 3: CONSTRAINT (structural rule) — NEW INFO
• Tweet 4: REVERSAL (causal flip) — NEW INSIGHT
• Tweet 5: CONSEQUENCE (what this forces) — NEW IMPLICATION
• Tweet 6: TAKEAWAY (belief shift) — NEW MENTAL MODEL

Each tweet = ONE new piece of information.

DUPLICATES = INSTANT FAIL. LLM MUST REWRITE.

Example of BAD repetition:
Tweet 1: "Gold at $5,000 looks like fear."
Tweet 6: "This explains why gold's rise to $5,000 wasn't about fear." ❌
→ Same information, just restated. INVALID.

Example of GOOD progression:
Tweet 1: "Gold at $5,000 looks like fear."
Tweet 6: "This doesn't predict gold. It explains why fear is the wrong lens." ✅
→ New mental model, not repetition. VALID.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TWEET 1: HOOK - Narrative vs structure mismatch
TWEET 2: PROBLEM - What narrative says vs what structure shows
TWEET 3: INSIGHT - WHO must act? WHO can leave?
TWEET 4: PROOF - Specific amounts, quotas, percentages
TWEET 5: FRAMEWORK - Specific structural signals to watch
TWEET 6: TAKEAWAY - Strong close with observation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOJI RULES (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tweet 1: NO emoji
Tweet 2: NO emoji
Tweet 3: 🏦 MUST START the tweet
Tweet 4: NO emoji
Tweet 5: 📊 MUST START the tweet
Tweet 6: 🔒 MUST START the tweet

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAIL CONDITIONS (AUTO-REWRITE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Single-line tweet
❌ Tweet 1 reveals the mechanism/thesis
❌ Tweet 3 uses trends instead of FORCED behavior
❌ Tweet 3 doesn't start with 🏦
❌ Tweet 4 uses numbers that contradict the narrative
❌ Tweet 5 uses generic textbook phrases
❌ Tweet 5 doesn't start with 📊
❌ Tweet 6 doesn't start with 🔒
❌ Sounds like news summary
❌ REPEATED CONTENT across tweets (check ANTI-REPETITION RULES)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• No hype, no advice, no predictions
• No hashtags
• Explain concepts clearly (8th grade level)
• Use analogies if they help understanding

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return EXACTLY:

TWEET1:
<multi-line text, 180-250 chars>

TWEET2:
<multi-line text, 180-250 chars>

TWEET3:
🏦 <multi-line text, 180-250 chars>

TWEET4:
<multi-line text, 180-250 chars>

TWEET5:
📊 <multi-line text, 180-250 chars>

TWEET6:
🔒 <multi-line text, 180-250 chars>


- Causal reversals must describe past or present mechanics.
- Do NOT imply future outcomes or directional forecasts.
- NO commentary. NO explanations.
- Check for repetition before finalizing.
"""

TWITTER_THREAD_POLICY_v1_0 = """
You DESIGN ATTENTION for policy/regulatory content. Create a thread that reveals structural constraints.

Tension first. Mechanics second. Authority last.

EVENT: {event_title}
CONTENT: {poc_content}

⚠️ CRITICAL CONSTRAINTS
- EXACTLY 6 tweets
- Each tweet: 180–260 characters ONLY
- Any tweet outside this range = INVALID
- Tweet must contain AT LEAST 2 meaningful lines (line breaks required)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-REPETITION RULES (CRITICAL - INSTANT FAIL IF VIOLATED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each tweet MUST introduce NEW information. NO REPETITION.

❌ FORBIDDEN PATTERNS (instant fail):
• Repeating same fact in different words
• Saying "In other words..." or "To put it simply..."
• Restating Tweet 1's hook in Tweet 6
• Using same numbers/stats in multiple tweets
• Circular logic (Tweet 3 says A, Tweet 5 repeats A)
• Paraphrasing previous tweet for "emphasis"

✅ REQUIRED PROGRESSION:
• Tweet 1: HOOK (policy announced, tension)
• Tweet 2: PROBLEM (what official narrative claims) — NEW INFO
• Tweet 3: CONSTRAINT (who MUST comply) — NEW INFO
• Tweet 4: REVERSAL (unintended consequences) — NEW INSIGHT
• Tweet 5: METRICS (specific compliance signals to watch) — NEW DATA
• Tweet 6: TAKEAWAY (structural change, not prediction) — NEW UNDERSTANDING

Each tweet = ONE new piece of information.

DUPLICATES = INSTANT FAIL.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE STRUCTURE (Policy/Macro Focus)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TWEET 1: HOOK - Policy announced (tension, not explanation)
TWEET 2: OFFICIAL CLAIM - What regulators say it does
TWEET 3: REGULATORY CONSTRAINT - WHO must comply, WHO can leave
TWEET 4: CAUSAL REVERSAL - Unintended consequences or incentive mismatch
TWEET 5: COMPLIANCE METRICS - Specific signals to watch (bid-to-cover, SLR%, utilization)
TWEET 6: STRUCTURAL TAKEAWAY - What changed in the system (not what will happen)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOJI RULES (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tweet 1: NO emoji
Tweet 2: NO emoji
Tweet 3: 🏦 MUST START the tweet (regulatory constraint)
Tweet 4: NO emoji
Tweet 5: 📊 MUST START the tweet (compliance metrics)
Tweet 6: 🔒 MUST START the tweet (structural takeaway)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAIL CONDITIONS (AUTO-REWRITE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Single-line tweet
❌ Tweet 1 explains the policy (should create tension only)
❌ Tweet 3 doesn't identify WHO is forced to comply
❌ Tweet 3 doesn't start with 🏦
❌ Tweet 4 predicts outcomes instead of showing incentive mismatch
❌ Tweet 5 uses vague metrics ("market sentiment")
❌ Tweet 5 doesn't start with 📊
❌ Tweet 6 doesn't start with 🔒
❌ Sounds like government press release
❌ REPEATED CONTENT across tweets (check ANTI-REPETITION RULES)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• No hype, no advice, no predictions
• No hashtags
• Explain regulatory terms simply (8th grade level)
• Focus on WHO is forced to act, not what "might" happen

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POLICY-SPECIFIC GUIDANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tweet 3 (🏦 CONSTRAINT):
- Identify WHO must comply (banks, funds, exchanges, etc.)
- State the specific threshold/limit (e.g., "SLR must be 18%+")
- Show who can opt out (if any)

Tweet 5 (📊 METRICS):
- Specific data points to watch, not generic indicators
- Examples: bid-to-cover ratio, repo utilization %, SLR compliance rate
- NOT: "market sentiment", "investor confidence"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return EXACTLY:

TWEET1:
<multi-line text, 180-250 chars>

TWEET2:
<multi-line text, 180-250 chars>

TWEET3:
🏦 <multi-line text, 180-250 chars>

TWEET4:
<multi-line text, 180-250 chars>

TWEET5:
📊 <multi-line text, 180-250 chars>

TWEET6:
🔒 <multi-line text, 180-250 chars>


- Focus on structural constraints, not policy opinions.
- Show incentive mismatches, not intended outcomes.
- NO predictions about compliance rates or effects.
- Check for repetition before finalizing.
"""

# ============================================================================
# SELECTION FUNCTIONS
# ============================================================================

def get_intent_specific_single_prompt(
    intent: str,
    event_title: str,
    poc_content: str
) -> str:
    """
    Select SINGLE tweet prompt based on intent.

    Args:
        intent: Content intent (BREAKING_NEWS, DATA_RELEASE, DESCRIPTIVE, MARKET_OPINION)
        event_title: Event title
        poc_content: POC-generated content (will be truncated to 600 chars)

    Returns:
        Formatted prompt ready for LLM

    Raises:
        ValueError: If intent is not recognized
    """
    prompt_map = {
        "BREAKING_NEWS": TWITTER_SINGLE_BREAKING_NEWS_v1_0,
        "DATA_RELEASE": TWITTER_SINGLE_DATA_RELEASE_v1_0,
        "DESCRIPTIVE": TWITTER_SINGLE_DESCRIPTIVE_v1_0,
        "MARKET_OPINION": TWITTER_SINGLE_MARKET_OPINION_v1_0,
    }

    if intent not in prompt_map:
        raise ValueError(f"Unknown intent: {intent}. Valid intents: {list(prompt_map.keys())}")

    template = prompt_map[intent]
    return template.format(
        event_title=event_title,
        poc_content=poc_content[:600]  # Truncate for token limits
    )


def get_intent_specific_thread_prompt(
    intent: str,
    event_type: str,
    event_title: str,
    poc_content: str
) -> str:
    """
    Select THREAD prompt based on intent/event_type.

    Priority logic:
    1. Event type FINANCE_POLICY or MACRO_ECONOMIC → POLICY thread
    2. Intent EXPLANATORY → EXPLANATORY thread
    3. Fallback → EXPLANATORY thread (safest)

    Args:
        intent: Content intent
        event_type: Event classification
        event_title: Event title
        poc_content: POC-generated content

    Returns:
        Formatted prompt ready for LLM
    """
    # Priority 1: Event type (FINANCE_POLICY, MACRO_ECONOMIC)
    if event_type in ["FINANCE_POLICY", "MACRO_ECONOMIC"]:
        template = TWITTER_THREAD_POLICY_v1_0
    # Priority 2: Intent (EXPLANATORY)
    elif intent == "EXPLANATORY":
        template = TWITTER_THREAD_EXPLANATORY_v1_0
    # Fallback: EXPLANATORY (safest)
    else:
        template = TWITTER_THREAD_EXPLANATORY_v1_0

    return template.format(
        event_title=event_title,
        poc_content=poc_content
    )
