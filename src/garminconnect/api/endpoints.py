from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class EndpointCategory(Enum):
    DAILY = "daily"
    MONITORING = "monitoring"
    SLEEP = "sleep"
    ACTIVITY = "activity"
    TRAINING = "training"
    BODY = "body"
    DEVICE = "device"


@dataclass(frozen=True)
class Endpoint:
    name: str
    url_template: str
    category: EndpointCategory
    requires_user_id: bool = False
    params: dict[str, str] | None = None


ENDPOINTS: list[Endpoint] = [
    Endpoint("daily_summary", "/usersummary-service/usersummary/daily/{user_id}?calendarDate={date}", EndpointCategory.DAILY, requires_user_id=True),
    Endpoint("daily_steps", "/usersummary-service/stats/steps/daily/{start}/{end}", EndpointCategory.DAILY),
    Endpoint("daily_stats", "/userstats-service/wellness/daily/{user_id}?fromDate={start}&untilDate={end}", EndpointCategory.DAILY, requires_user_id=True),
    Endpoint("hydration", "/usersummary-service/usersummary/hydration/allData/{date}", EndpointCategory.DAILY),
    Endpoint("heart_rate", "/wellness-service/wellness/dailyHeartRate/{user_id}?date={date}", EndpointCategory.MONITORING, requires_user_id=True),
    Endpoint("stress", "/wellness-service/wellness/dailyStress/{date}", EndpointCategory.MONITORING),
    # body_battery: extracted from stress endpoint response (bodyBatteryValuesArray)
    Endpoint("respiration", "/wellness-service/wellness/daily/respiration/{date}", EndpointCategory.MONITORING),
    Endpoint("spo2", "/wellness-service/wellness/daily/spo2/{date}", EndpointCategory.MONITORING),
    Endpoint("steps_intraday", "/wellness-service/wellness/dailySummaryChart/{user_id}?date={date}", EndpointCategory.MONITORING, requires_user_id=True),
    Endpoint("sleep", "/wellness-service/wellness/dailySleepData/{user_id}?date={date}&nonSleepBufferMinutes=60", EndpointCategory.SLEEP, requires_user_id=True),
    Endpoint("activity_list", "/activitylist-service/activities/search/activities", EndpointCategory.ACTIVITY),
    Endpoint("activity_detail", "/activity-service/activity/{activity_id}", EndpointCategory.ACTIVITY),
    Endpoint("activity_splits", "/activity-service/activity/{activity_id}/splits", EndpointCategory.ACTIVITY),
    Endpoint("activity_hr_zones", "/activity-service/activity/{activity_id}/hrTimeInZones", EndpointCategory.ACTIVITY),
    Endpoint("activity_weather", "/activity-service/activity/{activity_id}/weather", EndpointCategory.ACTIVITY),
    Endpoint("activity_gps", "/activity-service/activity/{activity_id}/details", EndpointCategory.ACTIVITY),
    Endpoint("training_readiness", "/metrics-service/metrics/trainingreadiness/{date}", EndpointCategory.TRAINING),
    Endpoint("training_status", "/metrics-service/metrics/trainingstatus/aggregated/{date}", EndpointCategory.TRAINING),
    Endpoint("hrv", "/hrv-service/hrv/{date}", EndpointCategory.TRAINING),
    Endpoint("vo2max", "/metrics-service/metrics/maxmet/daily/{start}/{end}", EndpointCategory.TRAINING),
    Endpoint("fitness_age", "/fitnessage-service/fitnessage", EndpointCategory.TRAINING),
    Endpoint("race_predictions", "/metrics-service/metrics/racepredictions", EndpointCategory.TRAINING),
    Endpoint("endurance_score", "/metrics-service/metrics/endurancescore", EndpointCategory.TRAINING),
    Endpoint("hill_score", "/metrics-service/metrics/hillscore", EndpointCategory.TRAINING),
    Endpoint("training_load", "/metrics-service/metrics/trainingload/weekly", EndpointCategory.TRAINING),
    Endpoint("weight", "/weight-service/weight/dateRange?startDate={start}&endDate={end}", EndpointCategory.BODY),
    Endpoint("body_composition", "/weight-service/weight/daterangesnapshot?startDate={start}&endDate={end}", EndpointCategory.BODY),
    Endpoint("devices", "/device-service/deviceregistration/devices", EndpointCategory.DEVICE),
    Endpoint("device_solar", "/web-gateway/solar/{date}/{device_id}", EndpointCategory.DEVICE),
]

ENDPOINTS_BY_NAME: dict[str, Endpoint] = {ep.name: ep for ep in ENDPOINTS}
