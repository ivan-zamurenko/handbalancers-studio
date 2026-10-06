# Последовательность миграций

Каждая ниже — целевой слот задачи; SQL пока не написан. Autogenerate вручную проверить. Optional шаг не требует пустой миграции. down_revision указывает на фактический предыдущий применённый head.

| Слот | Задача | Целевой файл |
|---|---|
| 0001 | S01-02 | `server/alembic/versions/0001_schemas.py` |
| 0002 | S01-04 | `server/alembic/versions/0002_profiles.py` |
| 0003 | S01-05 | `server/alembic/versions/0003_profile_security.py` |
| 0004 | S01-06 | `server/alembic/versions/0004_auth_storage.py` |
| 0005 | S03-09 | `server/alembic/versions/0005_auth_limits.py` |
| 0006 | S04-05 | `server/alembic/versions/0006_audit.py` |
| 0007 | S04-06 | `server/alembic/versions/0007_preferences.py` |
| 0008 | S05-01 | `server/alembic/versions/0008_onboarding.py` |
| 0009 | S05-04 | `server/alembic/versions/0009_subscriptions.py` |
| 0010 | S05-06 | `server/alembic/versions/0010_coach_access.py` |
| 0011 | S05-07 | `server/alembic/versions/0011_command_receipts.py` |
| 0012 | S06-01 | `server/alembic/versions/0012_exercise_drafts.py` |
| 0013 | S06-03 | `server/alembic/versions/0013_exercise_versions.py` |
| 0014 | S07-01 | `server/alembic/versions/0014_program_roots.py` |
| 0015 | S07-02 | `server/alembic/versions/0015_program_workouts.py` |
| 0016 | S07-03 | `server/alembic/versions/0016_workout_blocks.py` |
| 0017 | S07-04 | `server/alembic/versions/0017_program_exercises.py` |
| 0018 | S07-05 | `server/alembic/versions/0018_program_targets.py` |
| 0019 | S07-06 | `server/alembic/versions/0019_program_immutability.py` |
| 0020 | S08-01 | `server/alembic/versions/0020_training_plans.py` |
| 0021 | S08-02 | `server/alembic/versions/0021_assignments.py` |
| 0022 | S08-03 | `server/alembic/versions/0022_training_weeks.py` |
| 0023 | S08-04 | `server/alembic/versions/0023_scheduled_workouts.py` |
| 0024 | S09-01 | `server/alembic/versions/0024_sessions.py` |
| 0025 | S09-02 | `server/alembic/versions/0025_set_logs.py` |
| 0026 | S09-03 | `server/alembic/versions/0026_session_time.py` |
| 0027 | S09-04 | `server/alembic/versions/0027_training_reports.py` |
| 0028 | S10-02 | `server/alembic/versions/0028_media_versions.py` |
| 0029 | S10-03 | `server/alembic/versions/0029_review_tasks.py` |
| 0030 | S10-04 | `server/alembic/versions/0030_private_notes.py` |
| 0031 | S10-05 | `server/alembic/versions/0031_review_versions.py` |
| 0032 | S11-01 | `server/alembic/versions/0032_planning_rules.py` |
| 0033 | S11-04 | `server/alembic/versions/0033_planning_previews.py` |
| 0034 | S11-09 | `server/alembic/versions/0034_plan_permissions.py` |
| 0035 | S11-10 | `server/alembic/versions/0035_change_requests.py` |
| 0036 | S12-01 | `server/alembic/versions/0036_assessment_protocols.py` |
| 0037 | S12-02 | `server/alembic/versions/0037_assessment_runs.py` |
| 0038 | S12-03 | `server/alembic/versions/0038_assessment_results.py` |
| 0039 | S13-02 | `server/alembic/versions/0039_checkout_attempts.py` |
| 0040 | S13-03 | `server/alembic/versions/0040_webhook_inbox.py` |
| 0041 | S13-05 | `server/alembic/versions/0041_trial_claims.py` |
| 0042 | S14-01 | `server/alembic/versions/0042_processing_permissions.py` |
| 0043 | S14-03 | `server/alembic/versions/0043_analysis_jobs.py` |
| 0044 | S14-05 | `server/alembic/versions/0044_analysis_observations.py` |
| 0045 | S14-06 | `server/alembic/versions/0045_adaptation_proposals.py` |
| 0046 | S15-02 | `server/alembic/versions/0046_call_allowance.py` |
| 0047 | S15-03 | `server/alembic/versions/0047_optional_chat.py` |
| 0048 | S16-05 | `server/alembic/versions/0048_measured_indexes.py` |
