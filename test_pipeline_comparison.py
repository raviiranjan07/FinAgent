"""
Pipeline Comparison Test - v1 vs v2
Shows sample outputs from both pipelines for the same RSS event.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.twitter_prompts import get_intent_specific_single_prompt

# Sample RSS Event
sample_event = {
    "title": "RBI announces repo rate unchanged at 6.5% for ninth consecutive meeting",
    "summary": "Reserve Bank of India maintains repo rate at 6.5% in December 2025 monetary policy review. Inflation remains at 5.1%, above the 4% target. RBI Governor emphasizes data-dependent approach while maintaining focus on bringing inflation to target range."
}

# Classification (same for both pipelines)
event_type = "FINANCE_POLICY"
intent = "BREAKING_NEWS"

print("=" * 100)
print("PIPELINE COMPARISON TEST - v1 vs v2")
print("=" * 100)
print()
print("RSS EVENT INPUT (Same for both pipelines):")
print("-" * 100)
print(f"Title: {sample_event['title']}")
print(f"Summary: {sample_event['summary']}")
print()
print(f"Classification: {event_type} | Intent: {intent}")
print()

# ============================================================================
# v1 PIPELINE OUTPUT
# ============================================================================
print("=" * 100)
print("v1 PIPELINE - Traditional Flow (400-word explanation -> Twitter)")
print("=" * 100)
print()

print("STEP 1: Generate 400-word explanation from RSS event")
print("-" * 100)

# Simulated v1 Step 1: 400-word explanation
v1_explanation = """The Reserve Bank of India (RBI) has maintained the repo rate at 6.5% for the ninth consecutive meeting in its December 2025 monetary policy review. This decision reflects the central bank's cautious stance amid persistent inflationary pressures and evolving economic conditions.

**Current Economic Landscape:**
India's inflation rate stands at 5.1%, which remains above the RBI's medium-term target of 4%. This elevated inflation level is a key concern for policymakers, as it impacts purchasing power and overall economic stability. The RBI's decision to hold rates steady indicates a balancing act between supporting economic growth and managing price stability.

**Policy Implications:**
By keeping the repo rate unchanged at 6.5%, the RBI is maintaining the cost of borrowing for banks. This directly affects lending rates across the economy. Commercial banks typically price their loans with a markup over the repo rate, meaning that with the repo rate at 6.5%, most retail and commercial lending happens at rates of 9% or higher.

**Structural Impact on Credit Markets:**
This rate decision creates a structural floor for lending rates in the Indian banking system. Banks cannot sustainably lend below this threshold given their own cost of funds and operational margins. This means that businesses seeking loans, home buyers, and other borrowers will continue to face relatively high borrowing costs in the near term.

**Governor's Data-Dependent Approach:**
RBI Governor emphasized a data-dependent approach to future policy decisions. This means that subsequent rate decisions will be based on incoming economic data, particularly inflation trends, GDP growth figures, and global economic conditions. The central bank is not committing to a predetermined path but rather maintaining flexibility to respond to evolving circumstances.

**Market and Economic Outlook:**
The unchanged repo rate signals that the RBI believes current monetary conditions are appropriate for achieving its dual mandate of price stability and supporting growth. The persistence of inflation above target suggests that rate cuts are not imminent, and the restrictive monetary stance may continue until inflation shows sustained moderation toward the 4% target."""

print(v1_explanation)
print()
print(f"Length: {len(v1_explanation)} chars (~400 words)")
print()

print("STEP 2: Extract Twitter content from 400-word explanation")
print("-" * 100)

# Simulated v1 Step 2: Twitter single tweet extracted from explanation
v1_tweet = """RBI held repo rate at 6.5% for ninth straight meeting as inflation stays at 5.1%, above the 4% target.

This keeps lending rates elevated - banks lend at 9%+ given their cost structure. Rate cuts unlikely until inflation moderates sustainably."""

print(v1_tweet)
print()
print(f"Character count: {len(v1_tweet)} chars")
print()
print("v1 CHARACTERISTICS:")
print("  - Generated from 400-word explanation (indirect)")
print("  - Information filtered through essay transformation")
print("  - May lose some numerical precision")
print("  - More explanatory tone")
print()

# ============================================================================
# v2 PIPELINE OUTPUT
# ============================================================================
print("=" * 100)
print("v2 PIPELINE - Direct Twitter Generation from RSS")
print("=" * 100)
print()

print("STEP 1: Generate Twitter content DIRECTLY from RSS event")
print("-" * 100)

# Get the actual prompt that would be used
prompt = get_intent_specific_single_prompt(
    intent=intent,
    event_title=sample_event['title'],
    poc_content=sample_event['summary']
)

print(f"Using intent-specific prompt: BREAKING_NEWS")
print(f"Prompt strategy: WHO did WHAT + Immediate Structural Impact")
print()

# Simulated v2 output: Direct tweet from RSS
v2_tweet = """RBI held repo rate at 6.5% - ninth straight meeting. Inflation at 5.1%, above the 4% target.

Banks MUST lend at 9%+ minimum. That's the structural FLOOR, not sentiment."""

print(v2_tweet)
print()
print(f"Character count: {len(v2_tweet)} chars")
print()
print("v2 CHARACTERISTICS:")
print("  - Generated DIRECTLY from RSS event (no intermediate step)")
print("  - Numbers prominently featured (6.5%, 5.1%, 9%)")
print("  - Structural language (MUST, FLOOR)")
print("  - More direct, punchy tone")
print()

# ============================================================================
# SIDE-BY-SIDE COMPARISON
# ============================================================================
print("=" * 100)
print("SIDE-BY-SIDE COMPARISON")
print("=" * 100)
print()

comparison_table = f"""
+------------------------+----------------------------------+----------------------------------+
| ASPECT                 | v1 (Traditional)                 | v2 (Direct)                      |
+------------------------+----------------------------------+----------------------------------+
| LLM Calls              | 2 (Explanation + Twitter)        | 1 (Direct Twitter)               |
+------------------------+----------------------------------+----------------------------------+
| Character Count        | {len(v1_tweet)} chars                          | {len(v2_tweet)} chars                          |
+------------------------+----------------------------------+----------------------------------+
| Number Prominence      | Medium (filtered through essay) | High (direct from RSS)           |
+------------------------+----------------------------------+----------------------------------+
| Structural Language    | Moderate ("keeps", "unlikely")  | Strong ("MUST", "FLOOR")         |
+------------------------+----------------------------------+----------------------------------+
| Tone                   | Explanatory                      | Direct, punchy                   |
+------------------------+----------------------------------+----------------------------------+
| Information Loss       | Possible (2-step transformation)| Minimal (direct extraction)      |
+------------------------+----------------------------------+----------------------------------+
| Cost                   | 2x LLM calls                     | 1x LLM call (50% savings)        |
+------------------------+----------------------------------+----------------------------------+
| Speed                  | Slower (sequential)              | Faster (single call)             |
+------------------------+----------------------------------+----------------------------------+
"""

print(comparison_table)
print()

# ============================================================================
# DETAILED CONTENT COMPARISON
# ============================================================================
print("=" * 100)
print("DETAILED CONTENT ANALYSIS")
print("=" * 100)
print()

print("v1 OUTPUT:")
print("-" * 100)
print(v1_tweet)
print()
print("Analysis:")
print("  [+] Complete information")
print("  [+] Clear narrative flow")
print("  [-] Less punchy impact")
print("  [-] Numbers less prominent")
print("  [-] Weaker structural framing ('keeps', 'unlikely')")
print()

print("v2 OUTPUT:")
print("-" * 100)
print(v2_tweet)
print()
print("Analysis:")
print("  [+] Immediate impact (MUST, FLOOR)")
print("  [+] Numbers front and center (6.5%, 5.1%, 9%)")
print("  [+] Structural constraints clear")
print("  [+] More Twitter-native style")
print("  [-] Slightly more compact (may need more context for some readers)")
print()

# ============================================================================
# EXAMPLE 2: DATA_RELEASE Intent
# ============================================================================
print("=" * 100)
print("EXAMPLE 2 - DATA_RELEASE Intent")
print("=" * 100)
print()

example2_event = {
    "title": "India's GDP growth slows to 6.2% in Q3 FY2025",
    "summary": "India's GDP growth rate declined to 6.2% in Q3 FY2025 from 7.8% in Q2. Manufacturing sector contracted 1.2% while services grew 8.1%. Private consumption remained weak at 3.5% growth."
}

print("RSS EVENT:")
print(f"Title: {example2_event['title']}")
print(f"Summary: {example2_event['summary']}")
print()

v1_example2 = """India's GDP growth slowed to 6.2% in Q3 FY2025, down from 7.8% in the previous quarter.

The slowdown was driven by manufacturing contraction at -1.2%, while services grew 8.1%. Private consumption growth remained weak at 3.5%, indicating continued demand challenges."""

v2_example2 = """GDP: 6.2% in Q3 (down from 7.8% in Q2).

Manufacturing FELL 1.2%. Services grew 8.1%.

Private consumption at 3.5% - demand is the STRUCTURAL drag, not just sentiment."""

print("v1 OUTPUT (via 400-word explanation):")
print("-" * 100)
print(v1_example2)
print(f"({len(v1_example2)} chars)")
print()

print("v2 OUTPUT (direct from RSS):")
print("-" * 100)
print(v2_example2)
print(f"({len(v2_example2)} chars)")
print()

print("COMPARISON:")
print("  v1: More narrative, explanatory")
print("  v2: More data-forward, structural framing (FELL, STRUCTURAL drag)")
print()

# ============================================================================
# SUMMARY & RECOMMENDATIONS
# ============================================================================
print("=" * 100)
print("KEY INSIGHTS")
print("=" * 100)
print()

print("WHEN v1 MIGHT WIN:")
print("  - Complex topics needing more context")
print("  - Readers prefer explanatory style")
print("  - Multi-faceted events with many angles")
print()

print("WHEN v2 MIGHT WIN:")
print("  - Breaking news requiring immediate impact")
print("  - Data releases with clear numbers")
print("  - Events with structural/mechanical implications")
print("  - Twitter-native audience preferring punchy content")
print()

print("RECOMMENDATION:")
print("  Run BOTH pipelines on 20-30 real events and compare:")
print("  1. Focus (does it highlight key facts?)")
print("  2. Accuracy (numbers correct?)")
print("  3. Impact (does it grab attention?)")
print("  4. Safety (no advice/predictions?)")
print()

print("=" * 100)
print("NEXT STEPS")
print("=" * 100)
print()
print("1. Run real comparison test:")
print("   python scripts/run_pipeline.py --pipeline both")
print()
print("2. Review in dashboard:")
print("   http://localhost:5173/generated-content")
print("   Filter by pipeline_version: 'v1' vs 'v2'")
print()
print("3. Evaluate 20-30 events and decide which pipeline to keep")
print()
print("=" * 100)
