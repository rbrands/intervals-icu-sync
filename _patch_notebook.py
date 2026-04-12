"""Patch: add Long Ride Sessions row to week_display dict in week_summary.ipynb."""
from pathlib import Path

path = Path(__file__).parent / "notebooks" / "week_summary.ipynb"
content = path.read_text(encoding="utf-8")

old = '    \\"Threshold Sessions\\": ws.get(\\"threshold_sessions\\"),\\n",\n    "    \\"Endurance Sessions\\": ws.get(\\"endurance_sessions\\"),'
new = '    \\"Threshold Sessions\\": ws.get(\\"threshold_sessions\\"),\\n",\n    "    \\"Long Ride Sessions\\": ws.get(\\"long_ride_sessions\\"),\\n",\n    "    \\"Endurance Sessions\\": ws.get(\\"endurance_sessions\\"),'

if old in content:
    path.write_text(content.replace(old, new), encoding="utf-8")
    print("Done")
else:
    idx = content.find("threshold_sessions")
    print("NOT FOUND; ctx:", repr(content[max(0, idx - 5):idx + 150]))
