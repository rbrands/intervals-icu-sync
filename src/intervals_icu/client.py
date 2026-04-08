import requests

BASE_URL = "https://intervals.icu/api/v1"


def get_activities(api_key: str, athlete_id: str, start_date: str, end_date: str) -> list:
    """Fetch activities from intervals.icu for the given date range.

    Args:
        api_key: The intervals.icu API key.
        athlete_id: The intervals.icu athlete ID.
        start_date: The start date in ISO 8601 format (e.g. "2024-01-01").
        end_date: The end date in ISO 8601 format (e.g. "2024-01-07").

    Returns:
        A list of activity dicts as returned by the API.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/activities"

    
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        params={"oldest": start_date, "newest": end_date},
    )
  
    response.raise_for_status()

    return response.json()
