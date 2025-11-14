"""Backend package (ex-legacy app_final) re-exporting scheduling & LLM utilities.

Credentials come from session_state or environment variables (never hard-coded).
"""

from .llm import (
    load_fjsp_schema,
    get_openai_functions,
    generate_schedule_json,
    update_schedule_json,
    update_solution_csv_llm,
    get_llm_update_decision,
)

from .transform import (
    openai_json_to_npy,
    split_re,
    combine_re,
    json_to_tables,
    tables_to_json,
)

from .solver import (
    load_validation_model,
    prepare_data_for_validation,
    solve_with_ppo,
    solve_with_iaoa_gns,
    display_results,
    save_solution_pool,
)

from .validation import (
    validate_schedule_for_ppo,
    check_deadlines,
    check_precedence_constraints,
    extract_precedence_matrix,
)

from .diff_view import (
    show_json_diff,
    show_table_comparison,
)

__all__ = [
    # llm
    'load_fjsp_schema','get_openai_functions','generate_schedule_json','update_schedule_json',
    'update_solution_csv_llm','get_llm_update_decision',
    # transform
    'openai_json_to_npy','split_re','combine_re','json_to_tables','tables_to_json',
    # solver
    'load_validation_model','prepare_data_for_validation','solve_with_ppo','solve_with_iaoa_gns','display_results','save_solution_pool',
    # validation
    'validate_schedule_for_ppo','check_deadlines','check_precedence_constraints','extract_precedence_matrix',
    # diff
    'show_json_diff','show_table_comparison'
]
