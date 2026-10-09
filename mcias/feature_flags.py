"""Default-deny feature entitlements enforced server-side."""
import re
from mcias.policy import has_permission

_FEATURE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")

def feature_enabled(db, user, feature: str) -> bool:
    if not isinstance(feature, str) or _FEATURE.fullmatch(feature) is None:
        return False
    return has_permission(db, user, "features." + feature + ".use")
