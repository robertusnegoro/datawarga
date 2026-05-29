from __future__ import annotations
import logging
import time
import uuid
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


def check_database() -> tuple[bool, str]:
    """Check database connectivity by executing a simple SELECT 1 query."""
    try:
        db_conn = connections["default"]
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True, "Database is healthy"
    except OperationalError as e:
        return False, f"Database query failed: {str(e)}"
    except Exception as e:
        return False, f"Database error: {str(e)}"


def health_check(request) -> JsonResponse:
    """Liveness probe: returns 200 OK if the process is alive.

    Does not check downstream dependencies.
    """
    start_time = time.time()
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    operation = "health_check"

    logger.info(
        "Operation started",
        extra={
            "operation": operation,
            "correlationId": correlation_id,
            "userId": "system",
        },
    )

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": operation,
            "correlationId": correlation_id,
            "userId": "system",
            "duration": duration,
        },
    )

    return JsonResponse(
        {
            "status": "UP",
            "timestamp": timezone.now().isoformat(),
        },
        status=200,
    )


def ready_check(request) -> JsonResponse:
    """Readiness probe: checks critical dependencies (database) and returns 200 OK.

    Returns 503 Service Unavailable if any critical dependency is down.
    """
    start_time = time.time()
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    operation = "ready_check"

    logger.info(
        "Operation started",
        extra={
            "operation": operation,
            "correlationId": correlation_id,
            "userId": "system",
        },
    )

    db_healthy, db_message = check_database()
    duration = int((time.time() - start_time) * 1000)

    if db_healthy:
        logger.info(
            "Operation success",
            extra={
                "operation": operation,
                "correlationId": correlation_id,
                "userId": "system",
                "duration": duration,
            },
        )
        return JsonResponse(
            {
                "status": "UP",
                "timestamp": timezone.now().isoformat(),
                "components": {
                    "database": {
                        "status": "UP",
                        "message": db_message,
                    }
                },
            },
            status=200,
        )
    else:
        logger.error(
            "Operation failure",
            extra={
                "operation": operation,
                "correlationId": correlation_id,
                "userId": "system",
                "duration": duration,
                "error": db_message,
            },
        )
        return JsonResponse(
            {
                "status": "DOWN",
                "timestamp": timezone.now().isoformat(),
                "components": {
                    "database": {
                        "status": "DOWN",
                        "message": db_message,
                    }
                },
            },
            status=503,
        )
