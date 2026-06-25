"""add_organization_id_to_hr_models

Revision ID: 5c16b7f0bebc
Revises: ee2ad78d66d6
Create Date: 2026-06-25 10:04:02.702013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5c16b7f0bebc'
down_revision: Union[str, None] = 'ee2ad78d66d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Asset Categories ──
    op.add_column('asset_categories', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_asset_categories_organization_id'), 'asset_categories', ['organization_id'], unique=False)
    op.create_foreign_key('fk_asset_categories_organization_id', 'asset_categories', 'organizations', ['organization_id'], ['id'])

    # ── Asset Maintenance Requests ──
    op.add_column('asset_maintenance_requests', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_asset_maintenance_requests_organization_id'), 'asset_maintenance_requests', ['organization_id'], unique=False)
    op.create_foreign_key('fk_asset_maintenance_requests_organization_id', 'asset_maintenance_requests', 'organizations', ['organization_id'], ['id'])

    # ── Asset Requests ──
    op.add_column('asset_requests', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_asset_requests_organization_id'), 'asset_requests', ['organization_id'], unique=False)
    op.create_foreign_key('fk_asset_requests_organization_id', 'asset_requests', 'organizations', ['organization_id'], ['id'])

    # ── Assets ──
    op.add_column('assets', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_assets_organization_id'), 'assets', ['organization_id'], unique=False)
    op.create_foreign_key('fk_assets_organization_id', 'assets', 'organizations', ['organization_id'], ['id'])

    # ── Attendance Records ──
    op.add_column('attendance_records', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_attendance_records_organization_id'), 'attendance_records', ['organization_id'], unique=False)
    op.create_foreign_key('fk_attendance_records_organization_id', 'attendance_records', 'organizations', ['organization_id'], ['id'])

    # ── Compliance Records ──
    op.add_column('compliance_records', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_compliance_records_organization_id'), 'compliance_records', ['organization_id'], unique=False)
    op.create_foreign_key('fk_compliance_records_organization_id', 'compliance_records', 'organizations', ['organization_id'], ['id'])

    # ── Departments ──
    op.add_column('departments', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_departments_organization_id'), 'departments', ['organization_id'], unique=False)
    op.create_foreign_key('fk_departments_organization_id', 'departments', 'organizations', ['organization_id'], ['id'])

    # ── Designations ──
    op.add_column('designations', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_designations_organization_id'), 'designations', ['organization_id'], unique=False)
    op.create_foreign_key('fk_designations_organization_id', 'designations', 'organizations', ['organization_id'], ['id'])

    # ── Engagement Surveys ──
    op.add_column('engagement_surveys', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_engagement_surveys_organization_id'), 'engagement_surveys', ['organization_id'], unique=False)
    op.create_foreign_key('fk_engagement_surveys_organization_id', 'engagement_surveys', 'organizations', ['organization_id'], ['id'])

    # ── ESS Requests ──
    op.add_column('ess_requests', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_ess_requests_organization_id'), 'ess_requests', ['organization_id'], unique=False)
    op.create_foreign_key('fk_ess_requests_organization_id', 'ess_requests', 'organizations', ['organization_id'], ['id'])

    # ── Holidays ──
    op.add_column('holidays', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_holidays_organization_id'), 'holidays', ['organization_id'], unique=False)
    op.create_foreign_key('fk_holidays_organization_id', 'holidays', 'organizations', ['organization_id'], ['id'])

    # ── HR Documents ──
    op.add_column('hr_documents', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_hr_documents_organization_id'), 'hr_documents', ['organization_id'], unique=False)
    op.create_foreign_key('fk_hr_documents_organization_id', 'hr_documents', 'organizations', ['organization_id'], ['id'])

    # ── Learning Calendar Events ──
    op.add_column('learning_calendar_events', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_calendar_events_organization_id'), 'learning_calendar_events', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_calendar_events_organization_id', 'learning_calendar_events', 'organizations', ['organization_id'], ['id'])

    # ── Learning Certifications ──
    op.add_column('learning_certifications', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_certifications_organization_id'), 'learning_certifications', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_certifications_organization_id', 'learning_certifications', 'organizations', ['organization_id'], ['id'])

    # ── Learning Courses ──
    op.add_column('learning_courses', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_courses_organization_id'), 'learning_courses', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_courses_organization_id', 'learning_courses', 'organizations', ['organization_id'], ['id'])

    # ── Learning Enrollments ──
    op.add_column('learning_enrollments', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_enrollments_organization_id'), 'learning_enrollments', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_enrollments_organization_id', 'learning_enrollments', 'organizations', ['organization_id'], ['id'])

    # ── Learning Path Items ──
    op.add_column('learning_path_items', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_path_items_organization_id'), 'learning_path_items', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_path_items_organization_id', 'learning_path_items', 'organizations', ['organization_id'], ['id'])

    # ── Learning Paths ──
    op.add_column('learning_paths', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_paths_organization_id'), 'learning_paths', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_paths_organization_id', 'learning_paths', 'organizations', ['organization_id'], ['id'])

    # ── Learning Training Program Assignments ──
    op.add_column('learning_training_program_assignments', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_training_program_assignments_organization_id'), 'learning_training_program_assignments', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_training_program_assignments_organization_id', 'learning_training_program_assignments', 'organizations', ['organization_id'], ['id'])

    # ── Learning Training Programs ──
    op.add_column('learning_training_programs', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_learning_training_programs_organization_id'), 'learning_training_programs', ['organization_id'], unique=False)
    op.create_foreign_key('fk_learning_training_programs_organization_id', 'learning_training_programs', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding Activities ──
    op.add_column('onboarding_activities', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_activities_organization_id'), 'onboarding_activities', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_activities_organization_id', 'onboarding_activities', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding Checklist Items ──
    op.add_column('onboarding_checklist_items', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_checklist_items_organization_id'), 'onboarding_checklist_items', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_checklist_items_organization_id', 'onboarding_checklist_items', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding Checklists ──
    op.add_column('onboarding_checklists', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_checklists_organization_id'), 'onboarding_checklists', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_checklists_organization_id', 'onboarding_checklists', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding Documents ──
    op.add_column('onboarding_documents', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_documents_organization_id'), 'onboarding_documents', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_documents_organization_id', 'onboarding_documents', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding New Hires ──
    op.add_column('onboarding_new_hires', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_new_hires_organization_id'), 'onboarding_new_hires', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_new_hires_organization_id', 'onboarding_new_hires', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding Orientation Attendees ──
    op.add_column('onboarding_orientation_attendees', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_orientation_attendees_organization_id'), 'onboarding_orientation_attendees', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_orientation_attendees_organization_id', 'onboarding_orientation_attendees', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding Orientations ──
    op.add_column('onboarding_orientations', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_orientations_organization_id'), 'onboarding_orientations', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_orientations_organization_id', 'onboarding_orientations', 'organizations', ['organization_id'], ['id'])

    # ── Onboarding Preboarding Tasks ──
    op.add_column('onboarding_preboarding_tasks', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_onboarding_preboarding_tasks_organization_id'), 'onboarding_preboarding_tasks', ['organization_id'], unique=False)
    op.create_foreign_key('fk_onboarding_preboarding_tasks_organization_id', 'onboarding_preboarding_tasks', 'organizations', ['organization_id'], ['id'])

    # ── Performance Goals ──
    op.add_column('performance_goals', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_performance_goals_organization_id'), 'performance_goals', ['organization_id'], unique=False)
    op.create_foreign_key('fk_performance_goals_organization_id', 'performance_goals', 'organizations', ['organization_id'], ['id'])

    # ── Performance KPIs ──
    op.add_column('performance_kpis', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_performance_kpis_organization_id'), 'performance_kpis', ['organization_id'], unique=False)
    op.create_foreign_key('fk_performance_kpis_organization_id', 'performance_kpis', 'organizations', ['organization_id'], ['id'])

    # ── Performance Reviews ──
    op.add_column('performance_reviews', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_performance_reviews_organization_id'), 'performance_reviews', ['organization_id'], unique=False)
    op.create_foreign_key('fk_performance_reviews_organization_id', 'performance_reviews', 'organizations', ['organization_id'], ['id'])

    # ── Performance Feedback ──
    op.add_column('performance_feedback', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_performance_feedback_organization_id'), 'performance_feedback', ['organization_id'], unique=False)
    op.create_foreign_key('fk_performance_feedback_organization_id', 'performance_feedback', 'organizations', ['organization_id'], ['id'])

    # ── Performance Appraisals ──
    op.add_column('performance_appraisals', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_performance_appraisals_organization_id'), 'performance_appraisals', ['organization_id'], unique=False)
    op.create_foreign_key('fk_performance_appraisals_organization_id', 'performance_appraisals', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Applications ──
    op.add_column('recruitment_applications', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_applications_organization_id'), 'recruitment_applications', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_applications_organization_id', 'recruitment_applications', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Candidates ──
    op.add_column('recruitment_candidates', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_candidates_organization_id'), 'recruitment_candidates', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_candidates_organization_id', 'recruitment_candidates', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Documents ──
    op.add_column('recruitment_documents', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_documents_organization_id'), 'recruitment_documents', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_documents_organization_id', 'recruitment_documents', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Interview Feedback ──
    op.add_column('recruitment_interview_feedback', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_interview_feedback_organization_id'), 'recruitment_interview_feedback', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_interview_feedback_organization_id', 'recruitment_interview_feedback', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Interviews ──
    op.add_column('recruitment_interviews', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_interviews_organization_id'), 'recruitment_interviews', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_interviews_organization_id', 'recruitment_interviews', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Offer Approvals ──
    op.add_column('recruitment_offer_approvals', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_offer_approvals_organization_id'), 'recruitment_offer_approvals', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_offer_approvals_organization_id', 'recruitment_offer_approvals', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Offers ──
    op.add_column('recruitment_offers', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_offers_organization_id'), 'recruitment_offers', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_offers_organization_id', 'recruitment_offers', 'organizations', ['organization_id'], ['id'])

    # ── Recruitment Requisitions ──
    op.add_column('recruitment_requisitions', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruitment_requisitions_organization_id'), 'recruitment_requisitions', ['organization_id'], unique=False)
    op.create_foreign_key('fk_recruitment_requisitions_organization_id', 'recruitment_requisitions', 'organizations', ['organization_id'], ['id'])

    # ── Shifts ──
    op.add_column('shifts', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_shifts_organization_id'), 'shifts', ['organization_id'], unique=False)
    op.create_foreign_key('fk_shifts_organization_id', 'shifts', 'organizations', ['organization_id'], ['id'])

    # ── Travel Policies ──
    op.add_column('travel_policies', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_travel_policies_organization_id'), 'travel_policies', ['organization_id'], unique=False)
    op.create_foreign_key('fk_travel_policies_organization_id', 'travel_policies', 'organizations', ['organization_id'], ['id'])

    # ── Workforce Plans ──
    op.add_column('workforce_plans', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_workforce_plans_organization_id'), 'workforce_plans', ['organization_id'], unique=False)
    op.create_foreign_key('fk_workforce_plans_organization_id', 'workforce_plans', 'organizations', ['organization_id'], ['id'])


def downgrade() -> None:
    # ── Workforce Plans ──
    op.drop_constraint('fk_workforce_plans_organization_id', 'workforce_plans', type_='foreignkey')
    op.drop_index(op.f('ix_workforce_plans_organization_id'), table_name='workforce_plans')
    op.drop_column('workforce_plans', 'organization_id')

    # ── Travel Policies ──
    op.drop_constraint('fk_travel_policies_organization_id', 'travel_policies', type_='foreignkey')
    op.drop_index(op.f('ix_travel_policies_organization_id'), table_name='travel_policies')
    op.drop_column('travel_policies', 'organization_id')

    # ── Attendance Records ──
    op.drop_constraint('fk_attendance_records_organization_id', 'attendance_records', type_='foreignkey')
    op.drop_index(op.f('ix_attendance_records_organization_id'), table_name='attendance_records')
    op.drop_column('attendance_records', 'organization_id')

    # ── Shifts ──
    op.drop_constraint('fk_shifts_organization_id', 'shifts', type_='foreignkey')
    op.drop_index(op.f('ix_shifts_organization_id'), table_name='shifts')
    op.drop_column('shifts', 'organization_id')

    # ── Recruitment Requisitions ──
    op.drop_constraint('fk_recruitment_requisitions_organization_id', 'recruitment_requisitions', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_requisitions_organization_id'), table_name='recruitment_requisitions')
    op.drop_column('recruitment_requisitions', 'organization_id')

    # ── Recruitment Offers ──
    op.drop_constraint('fk_recruitment_offers_organization_id', 'recruitment_offers', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_offers_organization_id'), table_name='recruitment_offers')
    op.drop_column('recruitment_offers', 'organization_id')

    # ── Recruitment Offer Approvals ──
    op.drop_constraint('fk_recruitment_offer_approvals_organization_id', 'recruitment_offer_approvals', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_offer_approvals_organization_id'), table_name='recruitment_offer_approvals')
    op.drop_column('recruitment_offer_approvals', 'organization_id')

    # ── Recruitment Interviews ──
    op.drop_constraint('fk_recruitment_interviews_organization_id', 'recruitment_interviews', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_interviews_organization_id'), table_name='recruitment_interviews')
    op.drop_column('recruitment_interviews', 'organization_id')

    # ── Recruitment Interview Feedback ──
    op.drop_constraint('fk_recruitment_interview_feedback_organization_id', 'recruitment_interview_feedback', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_interview_feedback_organization_id'), table_name='recruitment_interview_feedback')
    op.drop_column('recruitment_interview_feedback', 'organization_id')

    # ── Recruitment Documents ──
    op.drop_constraint('fk_recruitment_documents_organization_id', 'recruitment_documents', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_documents_organization_id'), table_name='recruitment_documents')
    op.drop_column('recruitment_documents', 'organization_id')

    # ── Recruitment Candidates ──
    op.drop_constraint('fk_recruitment_candidates_organization_id', 'recruitment_candidates', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_candidates_organization_id'), table_name='recruitment_candidates')
    op.drop_column('recruitment_candidates', 'organization_id')

    # ── Recruitment Applications ──
    op.drop_constraint('fk_recruitment_applications_organization_id', 'recruitment_applications', type_='foreignkey')
    op.drop_index(op.f('ix_recruitment_applications_organization_id'), table_name='recruitment_applications')
    op.drop_column('recruitment_applications', 'organization_id')

    # ── Performance Reviews ──
    op.drop_constraint('fk_performance_reviews_organization_id', 'performance_reviews', type_='foreignkey')
    op.drop_index(op.f('ix_performance_reviews_organization_id'), table_name='performance_reviews')
    op.drop_column('performance_reviews', 'organization_id')

    # ── Performance Appraisals ──
    op.drop_constraint('fk_performance_appraisals_organization_id', 'performance_appraisals', type_='foreignkey')
    op.drop_index(op.f('ix_performance_appraisals_organization_id'), table_name='performance_appraisals')
    op.drop_column('performance_appraisals', 'organization_id')

    # ── Performance Feedback ──
    op.drop_constraint('fk_performance_feedback_organization_id', 'performance_feedback', type_='foreignkey')
    op.drop_index(op.f('ix_performance_feedback_organization_id'), table_name='performance_feedback')
    op.drop_column('performance_feedback', 'organization_id')

    # ── Performance KPIs ──
    op.drop_constraint('fk_performance_kpis_organization_id', 'performance_kpis', type_='foreignkey')
    op.drop_index(op.f('ix_performance_kpis_organization_id'), table_name='performance_kpis')
    op.drop_column('performance_kpis', 'organization_id')

    # ── Performance Goals ──
    op.drop_constraint('fk_performance_goals_organization_id', 'performance_goals', type_='foreignkey')
    op.drop_index(op.f('ix_performance_goals_organization_id'), table_name='performance_goals')
    op.drop_column('performance_goals', 'organization_id')

    # ── Onboarding Preboarding Tasks ──
    op.drop_constraint('fk_onboarding_preboarding_tasks_organization_id', 'onboarding_preboarding_tasks', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_preboarding_tasks_organization_id'), table_name='onboarding_preboarding_tasks')
    op.drop_column('onboarding_preboarding_tasks', 'organization_id')

    # ── Onboarding Orientations ──
    op.drop_constraint('fk_onboarding_orientations_organization_id', 'onboarding_orientations', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_orientations_organization_id'), table_name='onboarding_orientations')
    op.drop_column('onboarding_orientations', 'organization_id')

    # ── Onboarding Orientation Attendees ──
    op.drop_constraint('fk_onboarding_orientation_attendees_organization_id', 'onboarding_orientation_attendees', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_orientation_attendees_organization_id'), table_name='onboarding_orientation_attendees')
    op.drop_column('onboarding_orientation_attendees', 'organization_id')

    # ── Onboarding New Hires ──
    op.drop_constraint('fk_onboarding_new_hires_organization_id', 'onboarding_new_hires', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_new_hires_organization_id'), table_name='onboarding_new_hires')
    op.drop_column('onboarding_new_hires', 'organization_id')

    # ── Onboarding Documents ──
    op.drop_constraint('fk_onboarding_documents_organization_id', 'onboarding_documents', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_documents_organization_id'), table_name='onboarding_documents')
    op.drop_column('onboarding_documents', 'organization_id')

    # ── Onboarding Checklists ──
    op.drop_constraint('fk_onboarding_checklists_organization_id', 'onboarding_checklists', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_checklists_organization_id'), table_name='onboarding_checklists')
    op.drop_column('onboarding_checklists', 'organization_id')

    # ── Onboarding Checklist Items ──
    op.drop_constraint('fk_onboarding_checklist_items_organization_id', 'onboarding_checklist_items', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_checklist_items_organization_id'), table_name='onboarding_checklist_items')
    op.drop_column('onboarding_checklist_items', 'organization_id')

    # ── Onboarding Activities ──
    op.drop_constraint('fk_onboarding_activities_organization_id', 'onboarding_activities', type_='foreignkey')
    op.drop_index(op.f('ix_onboarding_activities_organization_id'), table_name='onboarding_activities')
    op.drop_column('onboarding_activities', 'organization_id')

    # ── Learning Training Programs ──
    op.drop_constraint('fk_learning_training_programs_organization_id', 'learning_training_programs', type_='foreignkey')
    op.drop_index(op.f('ix_learning_training_programs_organization_id'), table_name='learning_training_programs')
    op.drop_column('learning_training_programs', 'organization_id')

    # ── Learning Training Program Assignments ──
    op.drop_constraint('fk_learning_training_program_assignments_organization_id', 'learning_training_program_assignments', type_='foreignkey')
    op.drop_index(op.f('ix_learning_training_program_assignments_organization_id'), table_name='learning_training_program_assignments')
    op.drop_column('learning_training_program_assignments', 'organization_id')

    # ── Learning Paths ──
    op.drop_constraint('fk_learning_paths_organization_id', 'learning_paths', type_='foreignkey')
    op.drop_index(op.f('ix_learning_paths_organization_id'), table_name='learning_paths')
    op.drop_column('learning_paths', 'organization_id')

    # ── Learning Path Items ──
    op.drop_constraint('fk_learning_path_items_organization_id', 'learning_path_items', type_='foreignkey')
    op.drop_index(op.f('ix_learning_path_items_organization_id'), table_name='learning_path_items')
    op.drop_column('learning_path_items', 'organization_id')

    # ── Learning Enrollments ──
    op.drop_constraint('fk_learning_enrollments_organization_id', 'learning_enrollments', type_='foreignkey')
    op.drop_index(op.f('ix_learning_enrollments_organization_id'), table_name='learning_enrollments')
    op.drop_column('learning_enrollments', 'organization_id')

    # ── Learning Courses ──
    op.drop_constraint('fk_learning_courses_organization_id', 'learning_courses', type_='foreignkey')
    op.drop_index(op.f('ix_learning_courses_organization_id'), table_name='learning_courses')
    op.drop_column('learning_courses', 'organization_id')

    # ── Learning Certifications ──
    op.drop_constraint('fk_learning_certifications_organization_id', 'learning_certifications', type_='foreignkey')
    op.drop_index(op.f('ix_learning_certifications_organization_id'), table_name='learning_certifications')
    op.drop_column('learning_certifications', 'organization_id')

    # ── Learning Calendar Events ──
    op.drop_constraint('fk_learning_calendar_events_organization_id', 'learning_calendar_events', type_='foreignkey')
    op.drop_index(op.f('ix_learning_calendar_events_organization_id'), table_name='learning_calendar_events')
    op.drop_column('learning_calendar_events', 'organization_id')

    # ── HR Documents ──
    op.drop_constraint('fk_hr_documents_organization_id', 'hr_documents', type_='foreignkey')
    op.drop_index(op.f('ix_hr_documents_organization_id'), table_name='hr_documents')
    op.drop_column('hr_documents', 'organization_id')

    # ── Holidays ──
    op.drop_constraint('fk_holidays_organization_id', 'holidays', type_='foreignkey')
    op.drop_index(op.f('ix_holidays_organization_id'), table_name='holidays')
    op.drop_column('holidays', 'organization_id')

    # ── ESS Requests ──
    op.drop_constraint('fk_ess_requests_organization_id', 'ess_requests', type_='foreignkey')
    op.drop_index(op.f('ix_ess_requests_organization_id'), table_name='ess_requests')
    op.drop_column('ess_requests', 'organization_id')

    # ── Engagement Surveys ──
    op.drop_constraint('fk_engagement_surveys_organization_id', 'engagement_surveys', type_='foreignkey')
    op.drop_index(op.f('ix_engagement_surveys_organization_id'), table_name='engagement_surveys')
    op.drop_column('engagement_surveys', 'organization_id')

    # ── Designations ──
    op.drop_constraint('fk_designations_organization_id', 'designations', type_='foreignkey')
    op.drop_index(op.f('ix_designations_organization_id'), table_name='designations')
    op.drop_column('designations', 'organization_id')

    # ── Departments ──
    op.drop_constraint('fk_departments_organization_id', 'departments', type_='foreignkey')
    op.drop_index(op.f('ix_departments_organization_id'), table_name='departments')
    op.drop_column('departments', 'organization_id')

    # ── Compliance Records ──
    op.drop_constraint('fk_compliance_records_organization_id', 'compliance_records', type_='foreignkey')
    op.drop_index(op.f('ix_compliance_records_organization_id'), table_name='compliance_records')
    op.drop_column('compliance_records', 'organization_id')

    # ── Assets ──
    op.drop_constraint('fk_assets_organization_id', 'assets', type_='foreignkey')
    op.drop_index(op.f('ix_assets_organization_id'), table_name='assets')
    op.drop_column('assets', 'organization_id')

    # ── Asset Requests ──
    op.drop_constraint('fk_asset_requests_organization_id', 'asset_requests', type_='foreignkey')
    op.drop_index(op.f('ix_asset_requests_organization_id'), table_name='asset_requests')
    op.drop_column('asset_requests', 'organization_id')

    # ── Asset Maintenance Requests ──
    op.drop_constraint('fk_asset_maintenance_requests_organization_id', 'asset_maintenance_requests', type_='foreignkey')
    op.drop_index(op.f('ix_asset_maintenance_requests_organization_id'), table_name='asset_maintenance_requests')
    op.drop_column('asset_maintenance_requests', 'organization_id')

    # ── Asset Categories ──
    op.drop_constraint('fk_asset_categories_organization_id', 'asset_categories', type_='foreignkey')
    op.drop_index(op.f('ix_asset_categories_organization_id'), table_name='asset_categories')
    op.drop_column('asset_categories', 'organization_id')
