"""Statistics routes for dashboard."""

from fastapi import APIRouter
from sqlalchemy import func

from database.connection import get_db_session
from database.repository import RepositoryManager
from database.models import Output, Evaluation, ContentQueue
from api.schemas.schemas import (
    DashboardStats,
    EvaluationStats,
    EventTypeStats,
    SourceStats,
    FailureReasonStats,
    HITLMetrics,
    AgreementMetrics,
    DisagreementExample,
)
from utils.timezone import get_ist_now

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get comprehensive dashboard statistics.

    This is the main endpoint for the dashboard overview.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Evaluation stats
        eval_stats = repo.evaluations.get_stats()
        pending_count = repo.outputs.count() - eval_stats["total"]

        evaluation_stats = EvaluationStats(
            total=eval_stats["total"],
            pass_count=eval_stats["pass_count"],
            fail_count=eval_stats["fail_count"],
            pass_rate=eval_stats["pass_rate"],
            fail_rate=eval_stats["fail_rate"],
            pending_count=max(0, pending_count),
        )

        # Event type distribution
        event_type_counts = repo.outputs.count_by_event_type()
        total_outputs = sum(event_type_counts.values()) or 1
        event_types = [
            EventTypeStats(
                event_type=et,
                count=count,
                percentage=round(count / total_outputs * 100, 1),
            )
            for et, count in event_type_counts.items()
        ]

        # Source distribution
        source_counts = repo.events.count_by_source()
        total_events = sum(source_counts.values()) or 1
        sources = [
            SourceStats(
                source=src,
                count=count,
                percentage=round(count / total_events * 100, 1),
            )
            for src, count in source_counts.items()
        ]

        # Failure reasons
        failure_counts = repo.evaluations.get_failure_reasons()
        total_failures = sum(failure_counts.values()) or 1
        failure_reasons = [
            FailureReasonStats(
                reason=reason,
                count=count,
                percentage=round(count / total_failures * 100, 1),
            )
            for reason, count in failure_counts.items()
        ]

        # Recent activity (last 7 days)
        from datetime import datetime, timedelta
        from sqlalchemy import func

        seven_days_ago = get_ist_now() - timedelta(days=7)

        # Count events per day
        daily_events = (
            db.query(
                func.date(Output.created_at).label("date"),
                func.count(Output.id).label("count")
            )
            .filter(Output.created_at >= seven_days_ago)
            .group_by(func.date(Output.created_at))
            .all()
        )

        recent_activity = {
            "daily_outputs": {
                str(row.date): row.count for row in daily_events
            },
            "total_last_7_days": sum(row.count for row in daily_events),
        }

        return DashboardStats(
            evaluation=evaluation_stats,
            event_types=event_types,
            sources=sources,
            failure_reasons=failure_reasons,
            recent_activity=recent_activity,
        )


@router.get("/hitl-metrics", response_model=HITLMetrics)
async def get_hitl_metrics():
    """
    Get comprehensive HITL metrics for exit criteria tracking.

    Calculates real agreement rate between AI suggestions and human verdicts.
    Target: 90% agreement rate.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Get overall agreement metrics
        overall = repo.evaluations.get_agreement_metrics()

        # Get recent trending (last 30 evaluations)
        recent = repo.evaluations.get_recent_agreement_rate(last_n=30)

        # Get disagreement examples for pattern analysis
        disagreement_examples = repo.evaluations.get_disagreement_examples(limit=10)

        # Calculate status
        target_rate = 90.0
        current_rate = overall["agreement_rate"]

        if current_rate >= target_rate:
            status = "achieved"
        elif current_rate >= 85.0:
            status = "on_track"
        else:
            status = "needs_improvement"

        # Calculate progress percentage
        progress_percentage = min(100.0, round((current_rate / target_rate) * 100, 1))
        remaining_to_target = max(0, target_rate - current_rate)

        return HITLMetrics(
            overall_metrics=AgreementMetrics(
                total=overall["total"],
                agreements=overall["agreements"],
                disagreements=overall["disagreements"],
                agreement_rate=overall["agreement_rate"],
                false_positive_rate=overall["false_positive_rate"],
                confusion_matrix=overall["confusion_matrix"],
            ),
            recent_metrics=AgreementMetrics(
                total=recent["total"],
                agreements=recent["agreements"],
                disagreements=recent["total"] - recent["agreements"],
                agreement_rate=recent["agreement_rate"],
                false_positive_rate=0.0,  # Not calculated for recent
                confusion_matrix={},  # Not calculated for recent
            ),
            target_rate=target_rate,
            status=status,
            progress_percentage=progress_percentage,
            remaining_to_target=remaining_to_target,
            disagreement_examples=[
                DisagreementExample(**example) for example in disagreement_examples
            ],
        )


@router.get("/hitl-progress")
async def get_hitl_progress():
    """
    Get HITL exit criteria progress.

    Target: 90% agreement between AI and human evaluators.
    Now uses real agreement rate instead of pass rate.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Get real agreement metrics
        metrics = repo.evaluations.get_agreement_metrics()

        agreement_rate = metrics["agreement_rate"]
        target_rate = 90.0

        return {
            "total_evaluated": metrics["total"],
            "agreements": metrics["agreements"],
            "disagreements": metrics["disagreements"],
            "agreement_rate": round(agreement_rate, 2),
            "target_rate": target_rate,
            "progress": min(100, round(agreement_rate / target_rate * 100, 1)) if agreement_rate > 0 else 0,
            "status": "on_track" if agreement_rate >= 85 else "needs_improvement",
            "remaining_to_target": max(0, target_rate - agreement_rate),
        }


@router.get("/summary")
async def get_summary():
    """Quick summary for dashboard header."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        total_events = repo.events.count()
        total_outputs = repo.outputs.count()
        eval_stats = repo.evaluations.get_stats()
        pending = total_outputs - eval_stats["total"]

        return {
            "total_events": total_events,
            "total_outputs": total_outputs,
            "total_evaluated": eval_stats["total"],
            "pending_evaluation": max(0, pending),
            "pass_rate": round(eval_stats["pass_rate"], 1),
        }


@router.get("/publishing-analytics")
async def get_publishing_analytics(days: int = 30):
    """
    Get daily publishing analytics with format breakdown.

    Returns:
    - Daily tweet counts grouped by format (SINGLE vs THREAD)
    - Total counts by format
    - Publishing trend over specified days

    Args:
        days: Number of days to include in analysis (default: 30)
    """
    from datetime import datetime, timedelta
    from collections import defaultdict

    with get_db_session() as db:
        # Calculate date range (all in IST - DB stores naive IST timestamps)
        end_date = get_ist_now()
        start_date_ist = end_date - timedelta(days=days)

        # Database stores naive IST timestamps, extract date directly
        ist_date = func.date(ContentQueue.published_at)

        # Query published content with date grouping (include all published)
        published_items = (
            db.query(
                ist_date.label("date"),
                ContentQueue.format,
                func.count(ContentQueue.id).label("count")
            )
            .filter(
                ContentQueue.status == "published",
                ContentQueue.published_at.isnot(None),
                ContentQueue.published_at >= start_date_ist,
            )
            .group_by(ist_date, ContentQueue.format)
            .order_by(ist_date)
            .all()
        )

        # Get total counts by format (include all published)
        total_by_format = (
            db.query(
                ContentQueue.format,
                func.count(ContentQueue.id).label("count")
            )
            .filter(
                ContentQueue.status == "published",
                ContentQueue.published_at.isnot(None),
            )
            .group_by(ContentQueue.format)
            .all()
        )

        # Get overall total published (include all)
        total_published = (
            db.query(func.count(ContentQueue.id))
            .filter(
                ContentQueue.status == "published",
                ContentQueue.published_at.isnot(None),
            )
            .scalar() or 0
        )

        # Get dry run count separately
        dry_run_count = (
            db.query(func.count(ContentQueue.id))
            .filter(
                ContentQueue.status == "published",
                ContentQueue.published_at.isnot(None),
                ContentQueue.twitter_post_id.isnot(None),
                ContentQueue.twitter_post_id.startswith("dry_run_")
            )
            .scalar() or 0
        )

        # Get live (real) published count
        live_count = total_published - dry_run_count

        # Build daily stats structure with ALL dates in range (fill missing with 0)
        daily_stats = {}

        # First, create entries for ALL dates in the range (using IST dates)
        current_date = start_date_ist
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_stats[date_str] = {
                "date": date_str,
                "single_count": 0,
                "thread_count": 0,
                "total_count": 0
            }
            current_date += timedelta(days=1)

        # Then, fill in the actual counts from database
        for row in published_items:
            date_str = str(row.date)
            if date_str in daily_stats:  # Should always be true
                if row.format == "SINGLE":
                    daily_stats[date_str]["single_count"] = row.count
                elif row.format == "THREAD":
                    daily_stats[date_str]["thread_count"] = row.count

                daily_stats[date_str]["total_count"] += row.count

        # Convert to sorted list
        daily_stats_list = sorted(daily_stats.values(), key=lambda x: x["date"])

        # Build format summary
        format_summary = {}
        for row in total_by_format:
            format_summary[row.format] = row.count

        return {
            "daily_stats": daily_stats_list,
            "total_published": total_published,
            "live_count": live_count,
            "dry_run_count": dry_run_count,
            "by_format": format_summary,
            "date_range": {
                "start": start_date_ist.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days": days
            }
        }
