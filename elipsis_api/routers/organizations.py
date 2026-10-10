"""Organizations API routes for managing companies and departments."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.services_marketplace import (
    get_user_organizations,
    get_organization_departments,
    update_organization_size,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/my")
def list_my_organizations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all organizations owned by or accessible to the current user.
    
    Returns list of organizations with basic details.
    """
    organizations = get_user_organizations(db, current_user.id)
    
    return {
        "organizations": organizations,
        "count": len(organizations)
    }


@router.get("/{org_id}")
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get detailed information about a specific organization.
    
    - **org_id**: Organization ID
    """
    org = db.get(models.Organization, org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user has access to this organization
    if org.user_id != current_user.id and not current_user.is_admin:
        # Check if user is linked through OrgOwner
        org_owner = db.scalar(
            select(models.OrgOwner).where(
                models.OrgOwner.organization_id == org_id,
                models.OrgOwner.user_id == current_user.id
            )
        )
        
        if not org_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
    
    return {
        "id": org.id,
        "name": org.name,
        "industry": org.industry,
        "employee_count": org.employee_count,
        "company_size": org.company_size or "small",
        "annual_revenue_min": org.annual_revenue_min,
        "annual_revenue_max": org.annual_revenue_max,
        "city": org.city,
        "country": org.country,
        "contact_email": org.contact_email,
        "contact_phone": org.contact_phone,
        "website": org.website,
        "created_at": org.created_at.isoformat(),
    }


@router.get("/{org_id}/departments")
def list_organization_departments(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all departments for an organization.
    
    - **org_id**: Organization ID
    """
    org = db.get(models.Organization, org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check access
    if org.user_id != current_user.id and not current_user.is_admin:
        org_owner = db.scalar(
            select(models.OrgOwner).where(
                models.OrgOwner.organization_id == org_id,
                models.OrgOwner.user_id == current_user.id
            )
        )
        
        if not org_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
    
    departments = get_organization_departments(db, org_id)
    
    return {
        "departments": departments,
        "count": len(departments)
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_organization(
    name: str,
    industry: str,
    employee_count: int | None = None,
    annual_revenue_min: float | None = None,
    annual_revenue_max: float | None = None,
    city: str | None = None,
    country: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    website: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new organization.
    
    - **name**: Company name (required)
    - **industry**: Industry/sector (required)
    - **employee_count**: Number of employees
    - **annual_revenue_min**: Minimum annual revenue (USD)
    - **annual_revenue_max**: Maximum annual revenue (USD)
    - **city**: City location
    - **country**: Country
    - **contact_email**: Contact email
    - **contact_phone**: Contact phone
    - **website**: Company website
    """
    # Create organization
    org = models.Organization(
        user_id=current_user.id,
        name=name,
        industry=industry,
        employee_count=employee_count,
        annual_revenue_min=annual_revenue_min,
        annual_revenue_max=annual_revenue_max,
        city=city,
        country=country,
        contact_email=contact_email,
        contact_phone=contact_phone,
        website=website,
    )
    
    db.add(org)
    db.flush()  # Get ID without committing
    
    # Calculate company size
    update_organization_size(db, org.id)
    
    db.commit()
    db.refresh(org)
    
    return {
        "id": org.id,
        "name": org.name,
        "company_size": org.company_size,
        "message": "Organization created successfully"
    }


@router.put("/{org_id}")
def update_organization(
    org_id: int,
    name: str | None = None,
    industry: str | None = None,
    employee_count: int | None = None,
    annual_revenue_min: float | None = None,
    annual_revenue_max: float | None = None,
    city: str | None = None,
    country: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    website: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update an existing organization.
    
    - **org_id**: Organization ID
    - All other fields optional (only provided fields will be updated)
    """
    org = db.get(models.Organization, org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check ownership
    if org.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this organization"
        )
    
    # Update fields
    if name is not None:
        org.name = name
    if industry is not None:
        org.industry = industry
    if employee_count is not None:
        org.employee_count = employee_count
    if annual_revenue_min is not None:
        org.annual_revenue_min = annual_revenue_min
    if annual_revenue_max is not None:
        org.annual_revenue_max = annual_revenue_max
    if city is not None:
        org.city = city
    if country is not None:
        org.country = country
    if contact_email is not None:
        org.contact_email = contact_email
    if contact_phone is not None:
        org.contact_phone = contact_phone
    if website is not None:
        org.website = website
    
    # Recalculate company size if revenue or employee count changed
    if employee_count is not None or annual_revenue_min is not None or annual_revenue_max is not None:
        update_organization_size(db, org.id)
    
    db.commit()
    db.refresh(org)
    
    return {
        "id": org.id,
        "name": org.name,
        "company_size": org.company_size,
        "message": "Organization updated successfully"
    }


@router.post("/{org_id}/departments", status_code=status.HTTP_201_CREATED)
def create_department(
    org_id: int,
    name: str,
    head: str | None = None,
    staff_count: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a department for an organization.
    
    - **org_id**: Organization ID
    - **name**: Department name (required)
    - **head**: Department head/manager name
    - **staff_count**: Number of staff in department
    """
    org = db.get(models.Organization, org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check ownership
    if org.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add departments to this organization"
        )
    
    dept = models.Department(
        organization_id=org_id,
        name=name,
        head=head,
        staff_count=staff_count,
    )
    
    db.add(dept)
    db.commit()
    db.refresh(dept)
    
    return {
        "id": dept.id,
        "name": dept.name,
        "message": "Department created successfully"
    }


@router.delete("/{org_id}/departments/{dept_id}")
def delete_department(
    org_id: int,
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a department."""
    org = db.get(models.Organization, org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check ownership
    if org.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    dept = db.get(models.Department, dept_id)
    
    if not dept or dept.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    db.delete(dept)
    db.commit()
    
    return {"message": "Department deleted"}
