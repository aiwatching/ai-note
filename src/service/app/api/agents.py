"""Agent management API routes."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from ..agents.scheduler import get_scheduler
from ..agents.event_bus import get_event_bus

router = APIRouter()


@router.get("/status")
async def get_agents_status() -> Dict[str, Any]:
    """
    Get status of the agent system.

    Returns the master scheduler status and all registered agents.
    """
    scheduler = get_scheduler()
    return scheduler.get_status()


@router.post("/start")
async def start_agents() -> Dict[str, str]:
    """
    Start the agent system.

    This will start the master scheduler and all registered agents.
    """
    scheduler = get_scheduler()

    if scheduler.is_running:
        return {"message": "Agent system is already running"}

    await scheduler.start()
    return {"message": "Agent system started"}


@router.post("/stop")
async def stop_agents() -> Dict[str, str]:
    """
    Stop the agent system.

    This will stop the master scheduler and all registered agents.
    """
    scheduler = get_scheduler()

    if not scheduler.is_running:
        return {"message": "Agent system is not running"}

    await scheduler.stop()
    return {"message": "Agent system stopped"}


@router.post("/agents/{agent_name}/start")
async def start_agent(agent_name: str) -> Dict[str, str]:
    """
    Start a specific agent.

    Args:
        agent_name: Name of the agent to start
    """
    scheduler = get_scheduler()
    agent = scheduler.get_agent(agent_name)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    success = await scheduler.start_agent(agent_name)
    if success:
        return {"message": f"Agent '{agent_name}' started"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to start agent '{agent_name}'")


@router.post("/agents/{agent_name}/stop")
async def stop_agent(agent_name: str) -> Dict[str, str]:
    """
    Stop a specific agent.

    Args:
        agent_name: Name of the agent to stop
    """
    scheduler = get_scheduler()
    agent = scheduler.get_agent(agent_name)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    success = await scheduler.stop_agent(agent_name)
    if success:
        return {"message": f"Agent '{agent_name}' stopped"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to stop agent '{agent_name}'")


@router.get("/agents/{agent_name}/status")
async def get_agent_status(agent_name: str) -> Dict[str, Any]:
    """
    Get status of a specific agent.

    Args:
        agent_name: Name of the agent
    """
    scheduler = get_scheduler()
    agent = scheduler.get_agent(agent_name)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    return agent.get_status()


@router.get("/events/history")
async def get_event_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent event history.

    Args:
        limit: Maximum number of events to return
    """
    event_bus = get_event_bus()
    events = event_bus.get_history(limit=limit)
    return [e.to_dict() for e in events]


# Schedule Agent specific endpoints

@router.get("/schedule/upcoming")
async def get_upcoming_schedules(hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get upcoming schedules within the specified hours.

    Args:
        hours: Number of hours to look ahead
    """
    scheduler = get_scheduler()
    schedule_agent = scheduler.get_agent("schedule_agent")

    if not schedule_agent:
        raise HTTPException(status_code=404, detail="Schedule agent not found")

    return await schedule_agent.get_upcoming_reminders(hours)


@router.get("/schedule/suggest-time")
async def suggest_time_slot(duration_minutes: int = 60) -> List[Dict[str, Any]]:
    """
    Suggest available time slots.

    Args:
        duration_minutes: Required duration in minutes
    """
    scheduler = get_scheduler()
    schedule_agent = scheduler.get_agent("schedule_agent")

    if not schedule_agent:
        raise HTTPException(status_code=404, detail="Schedule agent not found")

    return await schedule_agent.suggest_time_slot(duration_minutes)


# Content Agent specific endpoints

@router.get("/content/related/{note_id}")
async def get_related_notes(note_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get notes related to the specified note.

    Args:
        note_id: ID of the note
        limit: Maximum number of related notes
    """
    scheduler = get_scheduler()
    content_agent = scheduler.get_agent("content_agent")

    if not content_agent:
        raise HTTPException(status_code=404, detail="Content agent not found")

    return await content_agent.get_related_notes(note_id, limit)


@router.get("/content/tags")
async def get_tag_statistics() -> Dict[str, Any]:
    """
    Get tag usage statistics.
    """
    scheduler = get_scheduler()
    content_agent = scheduler.get_agent("content_agent")

    if not content_agent:
        raise HTTPException(status_code=404, detail="Content agent not found")

    return await content_agent.get_tag_statistics()


@router.get("/content/daily-summary")
async def get_daily_summary() -> Dict[str, Any]:
    """
    Get daily summary of note activity.
    """
    scheduler = get_scheduler()
    content_agent = scheduler.get_agent("content_agent")

    if not content_agent:
        raise HTTPException(status_code=404, detail="Content agent not found")

    return await content_agent.generate_daily_summary()
