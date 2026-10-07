"""Service layer facade — re-exports core + auth + extended helpers."""

from elipsis_api.services_core import (  # noqa: F401
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    DEMO_DEPARTMENTS,
    _now,
    _seed_admin,
    answers_map,
    compute,
    create_assessment,
    get_bank,
    get_questions,
    list_assessments,
    save,
    seed,
    submit,
)
from elipsis_api.services_auth import (  # noqa: F401
    authenticate,
    build_segments,
    create_session,
    delete_session,
    live_scores,
    question_dicts,
    register_user,
    save_answers,
    user_for_token,
)
from elipsis_api.services_ext import (  # noqa: F401
    _band_counts,
    _demo_score,
    create_share_link,
    dashboard_data,
    department_comparison,
    list_organizations,
    reset_demo_data,
    resolve_share_token,
    run_guided_demo,
)
