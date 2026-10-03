from constants import DEFAULT_HOURLY_RATE


def score_tasks(data):
    """Preliminary automation-opportunity band from overall team workload."""
    workload_minutes = data['tasks_per_week'] * data['minutes_per_task'] * data['staff']
    if workload_minutes > 2000:
        return "High"
    if workload_minutes > 600:
        return "Medium"
    return "Low"


def estimate_roi(data, hourly_rate=DEFAULT_HOURLY_RATE):
    """Estimated monthly savings, in the Elipsis reporting currency (KES)."""
    workload_hours_per_month = (
        data['tasks_per_week'] * data['minutes_per_task'] * data['staff']
    ) / 60 * 4.33
    monthly_cost = workload_hours_per_month * hourly_rate
    savings = monthly_cost * 0.4
    return savings
