# clarity_check.py
# POC Clarity Rules v2 – SIMPLE VERSION

def check_clarity(text):
    flags = []
    text_lower = text.lower()

    # RULE 1: Explain important terms
    important_terms = [
        "redemption",
        "regulation",
        "policy",
        "bond",
        "auction",
        "liquidity",
        "series"
    ]

    explanation_words = [
        "means",
        "refers to",
        "simply",
        "in simple terms"
    ]

    for term in important_terms:
        if term in text_lower:
            if not any(word in text_lower for word in explanation_words):
                flags.append(f"Term not explained: {term}")

    # RULE 2: What is this about?
    if not (
        text_lower.startswith("this is")
        or "this announcement" in text_lower
        or "this update" in text_lower
    ):
        flags.append("No clear context (what is this?)")

    # RULE 3: Why does it matter?
    if not (
        "this matters" in text_lower
        or "this means" in text_lower
        or "this affects" in text_lower
    ):
        flags.append("No impact explained (why it matters)")

    # RULE 4: Who is affected?
    audiences = [
        "investors",
        "businesses",
        "exporters",
        "importers",
        "banks",
        "general public"
    ]

    if not any(audience in text_lower for audience in audiences):
        flags.append("No audience mentioned")

    # RULE 5: Length check
    word_count = len(text.split())
    if word_count < 80:
        flags.append("Too short, lacks explanation")
    if word_count > 150:
        flags.append("Too long, hard to read")

    # FINAL RESULT
    if flags:
        return "FAIL", flags
    else:
        return "PASS", []


# -------- TEST THE FUNCTION --------
if __name__ == "__main__":
    sample_text = """
    What this was before
Sovereign Gold Bonds (SGBs) are government bonds linked to gold prices.
Normally, they mature after 8 years.
However, premature redemption is allowed after 5 years, but only on specific interest payment dates.
Many investors did not know:
When they are allowed to exit early
How the exit (redemption) price is calculated
2️⃣ What has changed now
RBI has announced the exact redemption price for a specific SGB tranche eligible for premature exit.
The price is calculated as:
Average of gold prices (999 purity) for the last 3 working days, published by an official bullion body.
For this event, RBI clearly states:
Which SGB series is eligible
Exact redemption date
Exact price per bond
No rules changed — clarity increased.
3️⃣ Who is affected
Individual investors who:
Bought SGBs around 2020–21
Are completing 5 years now
Especially useful for:
Long-term savers
People who don’t want to sell gold ETFs or physical gold in markets
4️⃣ What becomes easier
You can now answer before redeeming:
“How much money will I get per bond?”
“Is this price better than selling gold elsewhere?”
No guessing.
No market timing required.
No broker involved.
This improves trust and predictability for retail investors.
5️⃣ What does NOT change (important)
No new tax benefit is introduced
No interest rate is changed
No new redemption window is created
Gold price risk still exists
Capital gains tax rules remain the same
This is information disclosure, not a policy reform.
🧠 One-line takeaway (non-expert test)
RBI is telling SGB investors exactly how much they’ll get if they exit early, so they can decide calmly instead of guessing gold prices.
    """

    status, issues = check_clarity(sample_text)

    print("STATUS:", status)
    if issues:
        print("ISSUES:")
        for issue in issues:
            print("-", issue)
