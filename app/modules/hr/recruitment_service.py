from datetime import datetime, date
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.hr.models import (
    RecruitmentCandidate, RecruitmentRequisition, RecruitmentInterview, RecruitmentOffer,
    RecruitmentDocument, RecruitmentApplication,
    RecruitmentInterviewFeedback, RecruitmentOfferApproval,
    RecruitmentCandidateStatus, RequisitionStatus, InterviewStatus, OfferStatus,
)
from app.modules.hr.schemas import (
    RequisitionCreate, RequisitionUpdate,
    CandidateCreate, CandidateUpdate, CandidateStatusUpdate,
    InterviewCreate, InterviewUpdate, InterviewFeedback,
    OfferCreate, OfferUpdate, OfferStatusUpdate,
    DocumentCreate, DocumentResponse,
    ApplicationCreate, ApplicationResponse,
    InterviewFeedbackCreate,
    OfferApprovalCreate, OfferApprovalResponse,
)
from app.core.exceptions import NotFoundException, BadRequestException
from app.core.sanitize import sanitize_dict


def get_recruitment_dashboard(db: Session) -> dict:
    total_open_positions = db.query(func.count(RecruitmentRequisition.id)).filter(
        RecruitmentRequisition.status == RequisitionStatus.OPEN
    ).scalar() or 0

    active_candidates = db.query(func.count(RecruitmentCandidate.id)).filter(
        RecruitmentCandidate.status.notin_([RecruitmentCandidateStatus.HIRED, RecruitmentCandidateStatus.REJECTED])
    ).scalar() or 0

    scheduled_interviews = db.query(func.count(RecruitmentInterview.id)).filter(
        RecruitmentInterview.status == InterviewStatus.SCHEDULED
    ).scalar() or 0

    offers_extended = db.query(func.count(RecruitmentOffer.id)).filter(
        RecruitmentOffer.status.in_([OfferStatus.PENDING, OfferStatus.APPROVED])
    ).scalar() or 0

    offers_accepted = db.query(func.count(RecruitmentOffer.id)).filter(
        RecruitmentOffer.status == OfferStatus.ACCEPTED
    ).scalar() or 0

    time_to_hire = 0.0
    hired = db.query(RecruitmentCandidate).filter(
        RecruitmentCandidate.status == RecruitmentCandidateStatus.HIRED
    ).all()
    if hired:
        total_days = 0
        for c in hired:
            if c.applied_at and c.updated_at:
                delta = (c.updated_at - c.applied_at).days
                total_days += delta
        time_to_hire = round(total_days / len(hired), 1)

    hiring_funnel = (
        db.query(RecruitmentCandidate.status, func.count(RecruitmentCandidate.id))
        .group_by(RecruitmentCandidate.status)
        .all()
    )

    recent = (
        db.query(RecruitmentCandidate)
        .order_by(RecruitmentCandidate.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_open_positions": total_open_positions,
        "active_candidates": active_candidates,
        "scheduled_interviews": scheduled_interviews,
        "offers_extended": offers_extended,
        "offers_accepted": offers_accepted,
        "time_to_hire": time_to_hire,
        "hiring_funnel": [{"status": s.value, "count": cnt} for s, cnt in hiring_funnel],
        "recent_activity": [
            {
                "id": c.id,
                "name": c.name,
                "position": c.position,
                "status": c.status.value if c.status else None,
                "applied_at": c.applied_at,
            }
            for c in recent
        ],
    }


def create_requisition(db: Session, data: RequisitionCreate) -> RecruitmentRequisition:
    safe = sanitize_dict(data.model_dump(exclude_unset=True))
    req = RecruitmentRequisition(**safe)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def get_requisitions(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    status: Optional[RequisitionStatus] = None,
    department: Optional[str] = None,
) -> dict:
    per_page = min(per_page, 100)
    query = db.query(RecruitmentRequisition)

    if search:
        term = f"%{search}%"
        query = query.filter(
            (RecruitmentRequisition.title.ilike(term)) |
            (RecruitmentRequisition.department.ilike(term))
        )

    if status:
        query = query.filter(RecruitmentRequisition.status == status)

    if department:
        query = query.filter(RecruitmentRequisition.department == department)

    total = query.count()
    items = query.order_by(RecruitmentRequisition.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": items,
    }


def get_requisition_by_id(db: Session, req_id: int) -> RecruitmentRequisition:
    req = db.query(RecruitmentRequisition).filter(RecruitmentRequisition.id == req_id).first()
    if not req:
        raise NotFoundException("RecruitmentRequisition", req_id)
    return req


def update_requisition(db: Session, req_id: int, data: RequisitionUpdate) -> RecruitmentRequisition:
    req = get_requisition_by_id(db, req_id)
    update_data = sanitize_dict(data.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(req, field, value)
    db.commit()
    db.refresh(req)
    return req


def delete_requisition(db: Session, req_id: int) -> None:
    req = get_requisition_by_id(db, req_id)
    db.delete(req)
    db.commit()


def approve_requisition(db: Session, req_id: int) -> RecruitmentRequisition:
    req = get_requisition_by_id(db, req_id)
    if req.status != RequisitionStatus.DRAFT and req.status != RequisitionStatus.PENDING:
        raise BadRequestException("Requisition must be in DRAFT or PENDING status to approve")
    req.status = RequisitionStatus.OPEN
    db.commit()
    db.refresh(req)
    return req


def reject_requisition(db: Session, req_id: int) -> RecruitmentRequisition:
    req = get_requisition_by_id(db, req_id)
    if req.status not in (RequisitionStatus.DRAFT, RequisitionStatus.PENDING, RequisitionStatus.OPEN):
        raise BadRequestException("Requisition cannot be rejected in its current status")
    req.status = RequisitionStatus.CLOSED
    db.commit()
    db.refresh(req)
    return req


def create_candidate(db: Session, data: CandidateCreate) -> RecruitmentCandidate:
    safe = sanitize_dict(data.model_dump(exclude_unset=True))
    candidate = RecruitmentCandidate(**safe)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_candidates(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    status: Optional[RecruitmentCandidateStatus] = None,
    position: Optional[str] = None,
) -> dict:
    per_page = min(per_page, 100)
    query = db.query(RecruitmentCandidate)

    if search:
        term = f"%{search}%"
        query = query.filter(
            (RecruitmentCandidate.name.ilike(term)) |
            (RecruitmentCandidate.email.ilike(term)) |
            (RecruitmentCandidate.position.ilike(term))
        )

    if status:
        query = query.filter(RecruitmentCandidate.status == status)

    if position:
        query = query.filter(RecruitmentCandidate.position == position)

    total = query.count()
    items = query.order_by(RecruitmentCandidate.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": items,
    }


def get_candidate_by_id(db: Session, candidate_id: int) -> RecruitmentCandidate:
    candidate = db.query(RecruitmentCandidate).filter(RecruitmentCandidate.id == candidate_id).first()
    if not candidate:
        raise NotFoundException("RecruitmentCandidate", candidate_id)
    return candidate


def update_candidate(db: Session, candidate_id: int, data: CandidateUpdate) -> RecruitmentCandidate:
    candidate = get_candidate_by_id(db, candidate_id)
    update_data = sanitize_dict(data.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


def delete_candidate(db: Session, candidate_id: int) -> None:
    candidate = get_candidate_by_id(db, candidate_id)
    db.delete(candidate)
    db.commit()


def update_candidate_status(db: Session, candidate_id: int, data: CandidateStatusUpdate) -> RecruitmentCandidate:
    candidate = get_candidate_by_id(db, candidate_id)
    candidate.status = data.status
    db.commit()
    db.refresh(candidate)
    return candidate


def create_interview(db: Session, data: InterviewCreate) -> RecruitmentInterview:
    safe = sanitize_dict(data.model_dump(exclude_unset=True))
    interview = RecruitmentInterview(**safe)
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def get_interviews(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    candidate_id: Optional[int] = None,
    status: Optional[InterviewStatus] = None,
) -> dict:
    per_page = min(per_page, 100)
    query = db.query(RecruitmentInterview)

    if candidate_id:
        query = query.filter(RecruitmentInterview.candidate_id == candidate_id)

    if status:
        query = query.filter(RecruitmentInterview.status == status)

    total = query.count()
    items = query.order_by(RecruitmentInterview.interview_date.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": items,
    }


def get_interview_by_id(db: Session, interview_id: int) -> RecruitmentInterview:
    interview = db.query(RecruitmentInterview).filter(RecruitmentInterview.id == interview_id).first()
    if not interview:
        raise NotFoundException("RecruitmentInterview", interview_id)
    return interview


def update_interview(db: Session, interview_id: int, data: InterviewUpdate) -> RecruitmentInterview:
    interview = get_interview_by_id(db, interview_id)
    update_data = sanitize_dict(data.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(interview, field, value)
    db.commit()
    db.refresh(interview)
    return interview


def delete_interview(db: Session, interview_id: int) -> None:
    interview = get_interview_by_id(db, interview_id)
    db.delete(interview)
    db.commit()


def update_interview_feedback(db: Session, interview_id: int, data: InterviewFeedback) -> RecruitmentInterview:
    interview = get_interview_by_id(db, interview_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(interview, field, value)
    db.commit()
    db.refresh(interview)
    return interview


def create_offer(db: Session, data: OfferCreate) -> RecruitmentOffer:
    safe = sanitize_dict(data.model_dump(exclude_unset=True))
    offer = RecruitmentOffer(**safe)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def get_offers(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    candidate_id: Optional[int] = None,
    status: Optional[OfferStatus] = None,
) -> dict:
    per_page = min(per_page, 100)
    query = db.query(RecruitmentOffer)

    if candidate_id:
        query = query.filter(RecruitmentOffer.candidate_id == candidate_id)

    if status:
        query = query.filter(RecruitmentOffer.status == status)

    total = query.count()
    items = query.order_by(RecruitmentOffer.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": items,
    }


def get_offer_by_id(db: Session, offer_id: int) -> RecruitmentOffer:
    offer = db.query(RecruitmentOffer).filter(RecruitmentOffer.id == offer_id).first()
    if not offer:
        raise NotFoundException("RecruitmentOffer", offer_id)
    return offer


def update_offer(db: Session, offer_id: int, data: OfferUpdate) -> RecruitmentOffer:
    offer = get_offer_by_id(db, offer_id)
    update_data = sanitize_dict(data.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(offer, field, value)
    db.commit()
    db.refresh(offer)
    return offer


def delete_offer(db: Session, offer_id: int) -> None:
    offer = get_offer_by_id(db, offer_id)
    db.delete(offer)
    db.commit()


def accept_offer(db: Session, offer_id: int) -> RecruitmentOffer:
    offer = get_offer_by_id(db, offer_id)
    if offer.status != OfferStatus.PENDING and offer.status != OfferStatus.APPROVED:
        raise BadRequestException("Offer must be in PENDING or APPROVED status to accept")
    offer.status = OfferStatus.ACCEPTED
    db.commit()
    db.refresh(offer)
    return offer


def reject_offer(db: Session, offer_id: int) -> RecruitmentOffer:
    offer = get_offer_by_id(db, offer_id)
    if offer.status not in (OfferStatus.DRAFT, OfferStatus.PENDING, OfferStatus.APPROVED):
        raise BadRequestException("Offer cannot be rejected in its current status")
    offer.status = OfferStatus.REJECTED
    db.commit()
    db.refresh(offer)
    return offer


def withdraw_offer(db: Session, offer_id: int) -> RecruitmentOffer:
    offer = get_offer_by_id(db, offer_id)
    if offer.status not in (OfferStatus.DRAFT, OfferStatus.PENDING, OfferStatus.APPROVED):
        raise BadRequestException("Offer cannot be withdrawn in its current status")
    offer.status = OfferStatus.WITHDRAWN
    db.commit()
    db.refresh(offer)
    return offer


# ════════════════════════════════════════════════════════════════════════════
# DOCUMENTS
# ════════════════════════════════════════════════════════════════════════════

def create_document(db: Session, data: DocumentCreate, file_path: str) -> RecruitmentDocument:
    doc = RecruitmentDocument(
        candidate_id=data.candidate_id,
        document_type=data.document_type,
        file_path=file_path,
        file_name=data.file_name,
        file_size=data.file_size,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_candidate_documents(db: Session, candidate_id: int) -> list[RecruitmentDocument]:
    return db.query(RecruitmentDocument).filter(
        RecruitmentDocument.candidate_id == candidate_id
    ).all()


def delete_document(db: Session, document_id: int) -> None:
    doc = db.query(RecruitmentDocument).filter(RecruitmentDocument.id == document_id).first()
    if not doc:
        raise NotFoundException("RecruitmentDocument", document_id)
    db.delete(doc)
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# APPLICATIONS
# ════════════════════════════════════════════════════════════════════════════

def create_application(db: Session, data: ApplicationCreate) -> RecruitmentApplication:
    app = RecruitmentApplication(**data.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def get_applications(db: Session, candidate_id: Optional[int] = None,
                     requisition_id: Optional[int] = None) -> list[RecruitmentApplication]:
    query = db.query(RecruitmentApplication)
    if candidate_id:
        query = query.filter(RecruitmentApplication.candidate_id == candidate_id)
    if requisition_id:
        query = query.filter(RecruitmentApplication.requisition_id == requisition_id)
    return query.all()


def update_application_status(db: Session, application_id: int, status: str) -> RecruitmentApplication:
    app = db.query(RecruitmentApplication).filter(RecruitmentApplication.id == application_id).first()
    if not app:
        raise NotFoundException("RecruitmentApplication", application_id)
    app.status = status
    db.commit()
    db.refresh(app)
    return app


# ════════════════════════════════════════════════════════════════════════════
# INTERVIEW FEEDBACK
# ════════════════════════════════════════════════════════════════════════════

def create_interview_feedback(db: Session, data: InterviewFeedbackCreate) -> RecruitmentInterviewFeedback:
    fb = RecruitmentInterviewFeedback(**data.model_dump())
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def get_interview_feedback_list(db: Session, interview_id: int) -> list[RecruitmentInterviewFeedback]:
    return db.query(RecruitmentInterviewFeedback).filter(
        RecruitmentInterviewFeedback.interview_id == interview_id
    ).all()


# ════════════════════════════════════════════════════════════════════════════
# OFFER APPROVALS
# ════════════════════════════════════════════════════════════════════════════

def create_offer_approval(db: Session, data: OfferApprovalCreate) -> RecruitmentOfferApproval:
    approval = RecruitmentOfferApproval(**data.model_dump())
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def get_offer_approvals(db: Session, offer_id: int) -> list[RecruitmentOfferApproval]:
    return db.query(RecruitmentOfferApproval).filter(
        RecruitmentOfferApproval.offer_id == offer_id
    ).all()


# ════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ════════════════════════════════════════════════════════════════════════════

def get_recruitment_analytics_summary(db: Session) -> dict:
    total_candidates = db.query(RecruitmentCandidate).count()
    total_requisitions = db.query(RecruitmentRequisition).count()
    total_interviews = db.query(RecruitmentInterview).count()
    total_offers = db.query(RecruitmentOffer).count()
    total_hired = db.query(RecruitmentOffer).filter(
        RecruitmentOffer.status == OfferStatus.ACCEPTED
    ).count()
    return {
        "total_candidates": total_candidates,
        "total_requisitions": total_requisitions,
        "total_interviews": total_interviews,
        "total_offers": total_offers,
        "total_hired": total_hired,
        "conversion_rates": {
            "application_to_interview": (total_interviews / total_applications * 100) if (total_applications := db.query(RecruitmentApplication).count()) > 0 else 0,
            "interview_to_offer": (total_offers / total_interviews * 100) if total_interviews > 0 else 0,
            "offer_to_hire": (total_hired / total_offers * 100) if total_offers > 0 else 0,
        }
    }
