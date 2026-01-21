"""
POC Evaluation Script - Human Review Tool

This script helps you review LLM outputs and mark them as PASS or FAIL.
Results are saved to logs/evaluations.jsonl for calculating POC success rate.

Usage:
    python evaluate.py           # Review all unevaluated events
    python evaluate.py --all     # Review all events (including already evaluated)
    python evaluate.py --stats   # Show current statistics only
"""

import json
import datetime
import sys
from pathlib import Path
from config.settings import EVENTS_LOG_FILE, EVALUATIONS_LOG_FILE


def load_events() -> list:
    """Load all events from events.jsonl."""
    events = []
    if Path(EVENTS_LOG_FILE).exists():
        with open(EVENTS_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    return events


def load_evaluations() -> dict:
    """Load existing evaluations as dict keyed by event_id."""
    evaluations = {}
    if Path(EVALUATIONS_LOG_FILE).exists():
        with open(EVALUATIONS_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    eval_record = json.loads(line)
                    evaluations[eval_record["event_id"]] = eval_record
    return evaluations


def save_evaluation(record: dict):
    """Append a single evaluation record to evaluations.jsonl."""
    with open(EVALUATIONS_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def clear_screen():
    """Clear terminal screen."""
    print("\n" * 50)


def show_event(event: dict, index: int, total: int):
    """Display a single event for review."""
    print("=" * 70)
    print(f"EVENT {index}/{total}")
    print("=" * 70)
    print(f"ID:        {event.get('event_id', 'N/A')[:8]}...")
    print(f"Source:    {event.get('source', 'N/A')}")
    print(f"Title:     {event.get('title', 'N/A')}")
    print(f"Type:      {event.get('event_type', 'N/A')}")
    print(f"Intent:    {event.get('intent', 'N/A')}")
    print(f"HITL:      {event.get('hitl', {}).get('risk_level', 'N/A')} - {event.get('hitl', {}).get('auto_action', 'N/A')}")

    clarity = event.get('clarity_issues', [])
    if clarity:
        print(f"Issues:    {clarity}")

    print("-" * 70)
    print("LLM OUTPUT:")
    print("-" * 70)

    llm_output = event.get('llm_output', 'No output')
    # Truncate if too long
    if len(llm_output) > 1500:
        print(llm_output[:1500])
        print(f"\n... [truncated, {len(llm_output)} chars total]")
    else:
        print(llm_output)

    print("-" * 70)


def get_comment() -> str:
    """Get optional comment from user for feedback/improvement notes."""
    print("\nCOMMENT (optional - for feedback/improvement notes):")
    print("  Press Enter to skip, or type your comment:")
    comment = input("  > ").strip()
    return comment if comment else None


def get_verdict() -> tuple:
    """Get PASS/FAIL verdict from user. Returns (verdict, reason, comment)."""
    print("\nEVALUATION OPTIONS:")
    print("  [P] PASS - Output is acceptable")
    print("  [F] FAIL - Output has problems")
    print("  [S] SKIP - Review later")
    print("  [Q] QUIT - Save and exit")
    print()

    while True:
        choice = input("Your verdict (P/F/S/Q): ").strip().upper()

        if choice == "P":
            comment = get_comment()
            return "PASS", None, comment
        elif choice == "F":
            print("\nFAILURE REASONS:")
            print("  [1] Investment advice detected")
            print("  [2] Prediction/forecast made")
            print("  [3] Factually incorrect")
            print("  [4] Too vague / unclear")
            print("  [5] Forbidden language used")
            print("  [6] LLM error / no output")
            print("  [7] Other (specify)")

            reason_choice = input("Reason (1-7): ").strip()
            reasons = {
                "1": "Investment advice detected",
                "2": "Prediction/forecast made",
                "3": "Factually incorrect",
                "4": "Too vague / unclear",
                "5": "Forbidden language used",
                "6": "LLM error / no output",
            }

            if reason_choice in reasons:
                reason = reasons[reason_choice]
            elif reason_choice == "7":
                custom = input("Enter reason: ").strip()
                reason = custom if custom else "Unspecified"
            else:
                print("Invalid choice, defaulting to 'Unspecified'")
                reason = "Unspecified"

            comment = get_comment()
            return "FAIL", reason, comment
        elif choice == "S":
            return "SKIP", None, None
        elif choice == "Q":
            return "QUIT", None, None
        else:
            print("Invalid choice. Enter P, F, S, or Q.")


def show_stats(events: list, evaluations: dict):
    """Show current evaluation statistics."""
    total = len(events)
    evaluated = len(evaluations)

    pass_count = sum(1 for e in evaluations.values() if e["verdict"] == "PASS")
    fail_count = sum(1 for e in evaluations.values() if e["verdict"] == "FAIL")

    print("\n" + "=" * 50)
    print("POC EVALUATION STATISTICS")
    print("=" * 50)
    print(f"Total events:      {total}")
    print(f"Evaluated:         {evaluated}")
    print(f"Remaining:         {total - evaluated}")
    print("-" * 50)
    print(f"PASS:              {pass_count}")
    print(f"FAIL:              {fail_count}")

    if evaluated > 0:
        failure_rate = (fail_count / evaluated) * 100
        print("-" * 50)
        print(f"FAILURE RATE:      {failure_rate:.1f}%")

        if failure_rate <= 15:
            print("STATUS:            POC PASS (<=15%)")
        elif failure_rate <= 25:
            print("STATUS:            CONDITIONAL (16-25%)")
        else:
            print("STATUS:            POC FAIL (>25%)")

    print("=" * 50)

    # Show failure breakdown
    if fail_count > 0:
        print("\nFAILURE BREAKDOWN:")
        reasons = {}
        for e in evaluations.values():
            if e["verdict"] == "FAIL":
                reason = e.get("failure_reason", "Unspecified")
                reasons[reason] = reasons.get(reason, 0) + 1

        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"  {count}x {reason}")


def main():
    """Main evaluation loop."""
    # Check for --stats flag
    if "--stats" in sys.argv:
        events = load_events()
        evaluations = load_evaluations()
        show_stats(events, evaluations)
        return

    # Check for --all flag
    review_all = "--all" in sys.argv

    # Load data
    events = load_events()
    evaluations = load_evaluations()

    if not events:
        print("No events found in events.jsonl")
        return

    # Filter to unevaluated events (unless --all)
    if review_all:
        to_review = events
    else:
        to_review = [e for e in events if e.get("event_id") not in evaluations]

    if not to_review:
        print("All events have been evaluated!")
        show_stats(events, evaluations)
        return

    print(f"\nFound {len(to_review)} events to review.\n")
    print("Press Enter to start...")
    input()

    reviewed = 0
    for i, event in enumerate(to_review, 1):
        clear_screen()
        show_event(event, i, len(to_review))

        verdict, reason, comment = get_verdict()

        if verdict == "QUIT":
            print("\nSaving and exiting...")
            break
        elif verdict == "SKIP":
            print("Skipped.")
            continue
        else:
            # Save evaluation
            record = {
                "event_id": event["event_id"],
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "verdict": verdict,
                "failure_reason": reason,
                "comment": comment,  # Human feedback for improvement
                "event_type": event.get("event_type"),
                "intent": event.get("intent"),
                "source": event.get("source")
            }
            save_evaluation(record)
            evaluations[event["event_id"]] = record
            reviewed += 1
            print(f"\nRecorded: {verdict}")

        # Show progress
        if i < len(to_review):
            input("\nPress Enter for next event...")

    # Final stats
    print(f"\n\nSession complete. Reviewed {reviewed} events.")
    show_stats(events, evaluations)


if __name__ == "__main__":
    main()
