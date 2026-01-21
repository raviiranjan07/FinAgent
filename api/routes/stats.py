"""Statistics routes for dashboard."""

from fastapi import APIRouter
from sqlalchemy import func

from database.connection import get_db_session
from database.repository import RepositoryManager
from database.models import Output, Evaluation
from api.schemas.schemas import (
    DashboardStats,
    EvaluationStats,
    EventTypeStats,
    SourceStats,
    FailureReasonStats,
)

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

        seven_days_ago = datetime.utcnow() - timedelta(days=7)

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


@router.get("/hitl-progress")
async def get_hitl_progress():
    """
    Get HITL exit criteria progress.

    Target: 90% agreement between AI and human evaluators.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        stats = repo.evaluations.get_stats()

        # For now, we track pass rate as a proxy for agreement
        # In the future, this could compare AI confidence vs human verdict
        return {
            "total_evaluated": stats["total"],
            "pass_count": stats["pass_count"],
            "fail_count": stats["fail_count"],
            "pass_rate": round(stats["pass_rate"], 2),
            "target_rate": 90.0,
            "progress": min(100, round(stats["pass_rate"] / 90 * 100, 1)) if stats["pass_rate"] > 0 else 0,
            "status": "on_track" if stats["pass_rate"] >= 85 else "needs_improvement",
            "remaining_to_target": max(0, 90 - stats["pass_rate"]),
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
