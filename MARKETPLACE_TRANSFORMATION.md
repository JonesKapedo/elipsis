# Elipsis Marketplace Transformation - Implementation Guide

## Overview
This document outlines the complete transformation of Elipsis from a Kenyan-focused assessment tool to a **global AI automation marketplace platform** connecting companies seeking automation with service providers.

---

## 🎯 Core Changes Summary

### 1. **User Type System**
- **Client Companies**: Request assessments & physical automation services
- **Bidder Companies**: Deliver automation solutions (subscription-based)
- **Admin**: Verify & publish requests to marketplace

### 2. **New Features**
- Marketplace for automation service requests
- Bidder company profiles ("Shop" pages)
- Physical assessment request system
- Subscription management for bidders
- Feedback & rating system
- Global market focus (USD, international)

### 3. **Assessment Flow Enhancement**
- Pre-load existing company data
- Scope selection (whole organization vs department)
- Remove redundant company input on repeat assessments

### 4. **Authentication & Security**
- Proper credential validation
- NEON database integration
- Session management fixes
- Error handling improvements

---

## 📊 Database Schema Changes

### New Tables Required

```sql
-- Enhanced User table
ALTER TABLE users ADD COLUMN user_type VARCHAR(20) DEFAULT 'client';  -- 'client' or 'bidder'
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;

-- Enhanced Organization table
ALTER TABLE organizations ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE organizations ADD COLUMN annual_revenue_min FLOAT;  -- USD
ALTER TABLE organizations ADD COLUMN annual_revenue_max FLOAT;  -- USD
ALTER TABLE organizations ADD COLUMN company_size VARCHAR(20);  -- 'small', 'medium', 'big'
ALTER TABLE organizations ADD COLUMN contact_email VARCHAR(255);
ALTER TABLE organizations ADD COLUMN contact_phone VARCHAR(50);
ALTER TABLE organizations ADD COLUMN website VARCHAR(255);
ALTER TABLE organizations ADD COLUMN description TEXT;

-- Bidder Companies
CREATE TABLE bidder_companies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    services_offered TEXT,
    rate_card TEXT,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    website VARCHAR(255),
    description TEXT,
    experience_years INTEGER,
    subscription_status VARCHAR(20) DEFAULT 'inactive',
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bidder Portfolio
CREATE TABLE bidder_portfolio (
    id SERIAL PRIMARY KEY,
    bidder_company_id INTEGER REFERENCES bidder_companies(id) NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Physical Assessment Requests
CREATE TABLE physical_assessment_requests (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id) NOT NULL,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    requirements TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'verified', 'published', 'completed', 'cancelled'
    payment_status VARCHAR(20) DEFAULT 'unpaid',
    payment_amount FLOAT,
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    verified_at TIMESTAMP,
    published_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Request Documents
CREATE TABLE request_documents (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES physical_assessment_requests(id) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    file_size INTEGER,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Bid Submissions
CREATE TABLE bid_submissions (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES physical_assessment_requests(id) NOT NULL,
    bidder_company_id INTEGER REFERENCES bidder_companies(id) NOT NULL,
    message TEXT NOT NULL,
    proposed_timeline VARCHAR(255),
    proposed_cost FLOAT,
    status VARCHAR(20) DEFAULT 'submitted',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bidder Feedback
CREATE TABLE bidder_feedback (
    id SERIAL PRIMARY KEY,
    bidder_company_id INTEGER REFERENCES bidder_companies(id) NOT NULL,
    request_id INTEGER REFERENCES physical_assessment_requests(id) NOT NULL,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    bidder_company_id INTEGER REFERENCES bidder_companies(id) NOT NULL,
    plan_type VARCHAR(20) DEFAULT 'monthly',
    amount FLOAT,
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'active',
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    cancelled_at TIMESTAMP
);

-- Assessment scope enhancement
ALTER TABLE assessments ADD COLUMN scope VARCHAR(50) DEFAULT 'whole_organization';
```

---

## 🔒 Authentication Enhancement

### File: `elipsis_api/services_auth.py`

**Key Changes:**
1. Add email validation (proper @ check)
2. Add password strength requirements (min 8 chars)
3. Check for existing users before registration
4. Verify credentials against database (not just accept any input)
5. Return proper error messages for invalid credentials

```python
def authenticate(db: Session, email: str, password: str):
    """Authenticate user with proper validation."""
    if not email or "@" not in email:
        return None
    
    user = db.scalar(select(models.User).where(
        models.User.email == email.strip().lower()
    ))
    
    if user and security.verify_password(password, user.password_hash):
        # Update last login
        user.last_login = _now()
        db.commit()
        return user
    
    return None

def register_user(db: Session, email: str, password: str, name: str | None = None, user_type: str = "client"):
    """Register new user with validation."""
    email = (email or "").strip().lower()
    
    # Validation
    if not email or "@" not in email or "." not in email.split("@")[1]:
        raise ValueError("Please enter a valid email address.")
    
    if len(password or "") < 8:
        raise ValueError("Password must be at least 8 characters long.")
    
    # Check existing user
    existing = db.scalar(select(models.User).where(models.User.email == email))
    if existing:
        raise ValueError("An account with this email already exists. Please sign in instead.")
    
    # Create user
    user = models.User(
        email=email,
        name=(name or "").strip()[:120] or None,
        role="client" if user_type == "client" else "bidder",
        user_type=user_type,
        password_hash=security.hash_password(password),
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

---

## 🏢 Company Size Calculation Logic

### File: `elipsis_api/services_core.py`

```python
def calculate_company_size(employee_count: int | None, annual_revenue_avg: float | None) -> str:
    """
    Calculate company size based on employees and revenue.
    Returns: 'small', 'medium', or 'big'
    
    Criteria:
    - Small: <50 employees OR <$5M revenue
    - Medium: 50-500 employees OR $5M-$50M revenue  
    - Big: >500 employees OR >$50M revenue
    """
    if employee_count is None and annual_revenue_avg is None:
        return 'small'  # Default
    
    # Check employee count
    if employee_count is not None:
        if employee_count > 500:
            return 'big'
        elif employee_count >= 50:
            return 'medium'
        else:
            return 'small'
    
    # Check revenue
    if annual_revenue_avg is not None:
        if annual_revenue_avg > 50_000_000:  # >$50M
            return 'big'
        elif annual_revenue_avg >= 5_000_000:  # $5M-$50M
            return 'medium'
        else:
            return 'small'
    
    return 'small'

def get_company_badge_color(size: str) -> str:
    """Return badge color for company size."""
    return {
        'small': 'green',
        'medium': 'maroon',
        'big': 'red'
    }.get(size, 'green')
```

---

## 🎨 Logo Implementation

### Create: `frontend/src/components/logo.tsx`

```tsx
import React from 'react';

interface LogoProps {
  variant?: 'icon' | 'full';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Logo({ variant = 'full', size = 'md', className = '' }: LogoProps) {
  const sizeClasses = {
    sm: 'h-8',
    md: 'h-12',
    lg: 'h-16'
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* SVG Icon */}
      <svg 
        className={sizeClasses[size]} 
        viewBox="0 0 100 100" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Three dots morphing into circuit nodes */}
        <defs>
          <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1e3a8a" />
            <stop offset="50%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#7c3aed" />
          </linearGradient>
        </defs>
        
        {/* Circuit paths */}
        <path d="M20 50 L40 50" stroke="url(#logoGradient)" strokeWidth="2" opacity="0.6"/>
        <path d="M60 50 L80 50" stroke="url(#logoGradient)" strokeWidth="2" opacity="0.6"/>
        
        {/* Three nodes/dots */}
        <circle cx="20" cy="50" r="8" fill="url(#logoGradient)"/>
        <circle cx="50" cy="50" r="8" fill="url(#logoGradient)"/>
        <circle cx="80" cy="50" r="8" fill="url(#logoGradient)"/>
        
        {/* Neural connections */}
        <path d="M28 50 L42 50" stroke="url(#logoGradient)" strokeWidth="3" strokeLinecap="round"/>
        <path d="M58 50 L72 50" stroke="url(#logoGradient)" strokeWidth="3" strokeLinecap="round"/>
      </svg>
      
      {/* Text */}
      {variant === 'full' && (
        <span className="font-bold text-2xl bg-gradient-to-r from-blue-900 via-cyan-600 to-purple-600 bg-clip-text text-transparent">
          ELIPSIS
        </span>
      )}
    </div>
  );
}
```

### Usage in Components

**Landing Page (`frontend/src/routes/index.tsx`):**
```tsx
<Logo variant="full" size="lg" className="mb-8" />
```

**Navigation Bar:**
```tsx
<Logo variant="full" size="md" />
```

**Favicon:** Generate from logo SVG at 32x32, 64x64 sizes

---

## 🔄 Assessment Flow Changes

### File: `frontend/src/routes/app/assessments/new.tsx`

**Changes:**
1. Remove organization name input
2. Add dropdown to select existing organizations
3. Add scope selector (whole organization / department)
4. Pre-fill company data when selecting existing org

```tsx
export function AssessmentsNew() {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrgId, setSelectedOrgId] = useState(null);
  const [scope, setScope] = useState('whole_organization');
  const [departments, setDepartments] = useState([]);
  
  useEffect(() => {
    // Load user's organizations
    fetch('/api/v1/organizations/my')
      .then(res => res.json())
      .then(data => setOrganizations(data));
  }, []);
  
  // When org selected, load its departments
  useEffect(() => {
    if (selectedOrgId) {
      fetch(`/api/v1/organizations/${selectedOrgId}/departments`)
        .then(res => res.json())
        .then(data => setDepartments(data));
    }
  }, [selectedOrgId]);
  
  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">New Assessment</h1>
      
      {/* Organization Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">
          Select Organization
        </label>
        <select 
          value={selectedOrgId || ''} 
          onChange={(e) => setSelectedOrgId(e.target.value)}
          className="w-full border rounded px-3 py-2"
        >
          <option value="">-- Select Organization --</option>
          {organizations.map(org => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
        <a href="/app/my-company" className="text-sm text-blue-600 mt-1 inline-block">
          + Add New Organization
        </a>
      </div>
      
      {/* Scope Selection */}
      {selectedOrgId && (
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Assessment Scope
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input 
                type="radio" 
                value="whole_organization" 
                checked={scope === 'whole_organization'}
                onChange={(e) => setScope(e.target.value)}
                className="mr-2"
              />
              Whole Organization
            </label>
            <label className="flex items-center">
              <input 
                type="radio" 
                value="department" 
                checked={scope === 'department'}
                onChange={(e) => setScope(e.target.value)}
                className="mr-2"
              />
              Specific Department
            </label>
          </div>
        </div>
      )}
      
      {/* Department Selection (if scope = department) */}
      {scope === 'department' && (
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Select Department
          </label>
          <select className="w-full border rounded px-3 py-2">
            <option value="">-- Select Department --</option>
            {departments.map(dept => (
              <option key={dept.id} value={dept.id}>
                {dept.name}
              </option>
            ))}
          </select>
        </div>
      )}
      
      <button className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
        Start Assessment
      </button>
    </div>
  );
}
```

---

## 🛒 Marketplace Implementation

### New File: `frontend/src/routes/app/marketplace.tsx`

```tsx
import { useState, useEffect } from 'react';
import { CompanyBadge } from '@/components/company-badge';

export function Marketplace() {
  const [requests, setRequests] = useState([]);
  const [selectedRequest, setSelectedRequest] = useState(null);
  
  useEffect(() => {
    fetch('/api/v1/marketplace/requests')
      .then(res => res.json())
      .then(data => setRequests(data));
  }, []);
  
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Marketplace</h1>
      <p className="text-gray-600 mb-8">
        Browse automation service requests from companies worldwide
      </p>
      
      <div className="grid gap-4">
        {requests.map(req => (
          <div 
            key={req.id} 
            className="border rounded-lg p-6 hover:shadow-lg transition cursor-pointer"
            onClick={() => setSelectedRequest(req)}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-semibold flex items-center gap-2">
                  {req.organization_name}
                  <CompanyBadge size={req.company_size} />
                </h3>
                <p className="text-sm text-gray-500">{req.location}</p>
              </div>
              <span className="text-sm text-gray-400">
                {new Date(req.created_at).toLocaleDateString()}
              </span>
            </div>
            
            <h4 className="font-medium mb-2">{req.title}</h4>
            <p className="text-gray-700 line-clamp-2 mb-4">{req.message}</p>
            
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>📎 {req.document_count} documents</span>
              <span>💼 {req.industry}</span>
            </div>
          </div>
        ))}
      </div>
      
      {/* Request Detail Modal */}
      {selectedRequest && (
        <RequestDetailModal 
          request={selectedRequest} 
          onClose={() => setSelectedRequest(null)} 
        />
      )}
    </div>
  );
}
```

### Company Badge Component

### File: `frontend/src/components/company-badge.tsx`

```tsx
export function CompanyBadge({ size }: { size: 'small' | 'medium' | 'big' }) {
  const colors = {
    small: 'bg-green-100 text-green-800 border-green-300',
    medium: 'bg-red-900 text-white border-red-700',
    big: 'bg-red-600 text-white border-red-800'
  };
  
  const labels = {
    small: 'S',
    medium: 'M',
    big: 'B'
  };
  
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full border-2 text-xs font-bold ${colors[size]}`}>
      {labels[size]}
    </span>
  );
}
```

---

## 🏪 Bidder Shop Page

### File: `frontend/src/routes/app/shop.tsx`

```tsx
export function BidderShop() {
  const [shop, setShop] = useState(null);
  const [editing, setEditing] = useState(false);
  
  useEffect(() => {
    fetch('/api/v1/bidder/shop')
      .then(res => res.json())
      .then(data => setShop(data));
  }, []);
  
  if (!shop) return <div>Loading...</div>;
  
  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">My Shop</h1>
        <button 
          onClick={() => setEditing(!editing)}
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          {editing ? 'Save Changes' : 'Edit Shop'}
        </button>
      </div>
      
      {editing ? (
        <ShopEditForm shop={shop} onSave={(data) => {
          // Save shop data
          fetch('/api/v1/bidder/shop', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
          }).then(() => setEditing(false));
        }} />
      ) : (
        <ShopDisplay shop={shop} />
      )}
    </div>
  );
}
```

---

## 🔐 Admin Panel

### File: `frontend/src/routes/admin/requests.tsx`

```tsx
export function AdminRequests() {
  const [requests, setRequests] = useState([]);
  const [filter, setFilter] = useState('pending'); // pending, verified, all
  
  useEffect(() => {
    fetch(`/api/v1/admin/requests?status=${filter}`)
      .then(res => res.json())
      .then(data => setRequests(data));
  }, [filter]);
  
  const verifyRequest = async (requestId: number) => {
    await fetch(`/api/v1/admin/requests/${requestId}/verify`, {
      method: 'POST'
    });
    // Reload requests
    setRequests(requests.filter(r => r.id !== requestId));
  };
  
  const publishRequest = async (requestId: number) => {
    await fetch(`/api/v1/admin/requests/${requestId}/publish`, {
      method: 'POST'
    });
    // Reload requests
  };
  
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Request Management</h1>
      
      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6">
        <button 
          onClick={() => setFilter('pending')}
          className={`px-4 py-2 rounded ${filter === 'pending' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Pending ({requests.filter(r => r.status === 'pending').length})
        </button>
        <button 
          onClick={() => setFilter('verified')}
          className={`px-4 py-2 rounded ${filter === 'verified' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Verified
        </button>
        <button 
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          All
        </button>
      </div>
      
      {/* Requests List */}
      <div className="space-y-4">
        {requests.map(req => (
          <div key={req.id} className="border rounded-lg p-4">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold">{req.title}</h3>
                <p className="text-sm text-gray-600">{req.organization_name}</p>
              </div>
              <span className={`px-2 py-1 rounded text-sm ${
                req.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                req.status === 'verified' ? 'bg-green-100 text-green-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {req.status}
              </span>
            </div>
            
            <p className="text-gray-700 mb-4">{req.message}</p>
            
            <div className="flex gap-2">
              {req.status === 'pending' && (
                <>
                  <button 
                    onClick={() => verifyRequest(req.id)}
                    className="bg-green-600 text-white px-4 py-1 rounded text-sm"
                  >
                    Verify
                  </button>
                  <button className="bg-red-600 text-white px-4 py-1 rounded text-sm">
                    Reject
                  </button>
                </>
              )}
              {req.status === 'verified' && (
                <button 
                  onClick={() => publishRequest(req.id)}
                  className="bg-blue-600 text-white px-4 py-1 rounded text-sm"
                >
                  Publish to Marketplace
                </button>
              )}
              <button className="bg-gray-200 px-4 py-1 rounded text-sm">
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🌐 API Routes

### File: `elipsis_api/routers/marketplace.py` (NEW)

```python
"""Marketplace API routes."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from elipsis_api import models, schemas
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, require_bidder, require_admin

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


@router.get("/requests")
def list_marketplace_requests(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Get all published marketplace requests."""
    query = db.query(models.PhysicalAssessmentRequest).filter(
        models.PhysicalAssessmentRequest.status == "published"
    ).order_by(models.PhysicalAssessmentRequest.published_at.desc())
    
    requests = query.all()
    
    result = []
    for req in requests:
        org = db.get(models.Organization, req.organization_id)
        result.append({
            "id": req.id,
            "title": req.title,
            "message": req.message,
            "organization_name": org.name if org else "Unknown",
            "company_size": org.company_size if org else "small",
            "location": f"{org.city}, {org.country}" if org else "",
            "industry": org.industry if org else "",
            "created_at": req.created_at,
            "published_at": req.published_at,
            "document_count": db.query(models.RequestDocument).filter(
                models.RequestDocument.request_id == req.id
            ).count()
        })
    
    return result


@router.get("/requests/{request_id}")
def get_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Get detailed request information."""
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req or req.status != "published":
        raise HTTPException(status_code=404, detail="Request not found")
    
    org = db.get(models.Organization, req.organization_id)
    documents = db.query(models.RequestDocument).filter(
        models.RequestDocument.request_id == request_id
    ).all()
    
    # Only bidders can see contact details
    show_contact = user.user_type == "bidder" and user.bidder_company and \
                   user.bidder_company.subscription_status == "active"
    
    return {
        "id": req.id,
        "title": req.title,
        "message": req.message,
        "requirements": req.requirements,
        "organization": {
            "name": org.name,
            "size": org.company_size,
            "location": f"{org.city}, {org.country}",
            "industry": org.industry,
            "description": org.description,
            "contact_email": org.contact_email if show_contact else None,
            "contact_phone": org.contact_phone if show_contact else None
        },
        "documents": [
            {
                "id": doc.id,
                "file_name": doc.file_name,
                "file_url": doc.file_url,
                "file_size": doc.file_size
            } for doc in documents
        ],
        "created_at": req.created_at,
        "published_at": req.published_at
    }


@router.post("/requests/{request_id}/bid")
def submit_bid(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_bidder)
):
    """Submit a bid on a request (bidders only)."""
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req or req.status != "published":
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check subscription
    bidder_company = db.query(models.BidderCompany).filter(
        models.BidderCompany.user_id == user.id
    ).first()
    
    if not bidder_company or bidder_company.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    
    # Create bid
    bid = models.BidSubmission(
        request_id=request_id,
        bidder_company_id=bidder_company.id,
        message=payload.get("message"),
        proposed_timeline=payload.get("timeline"),
        proposed_cost=payload.get("cost"),
        status="submitted"
    )
    db.add(bid)
    db.commit()
    
    return {"ok": True, "bid_id": bid.id}
```

---

## 📋 Registration Flow Update

### File: `frontend/src/routes/register.tsx` (NEW)

```tsx
export function Register() {
  const [step, setStep] = useState(1); // 1: Choose type, 2: Enter details
  const [userType, setUserType] = useState<'client' | 'bidder' | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: ''
  });
  
  const handleSubmit = async () => {
    // Validate
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match');
      return;
    }
    
    // Register
    const res = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...formData,
        user_type: userType
      })
    });
    
    if (res.ok) {
      // Redirect to appropriate onboarding
      if (userType === 'client') {
        window.location.href = '/app/my-company/new';
      } else {
        window.location.href = '/app/shop/setup';
      }
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white p-8 rounded-lg shadow">
        <Logo variant="full" size="lg" className="justify-center mb-8" />
        
        {step === 1 && (
          <div>
            <h2 className="text-2xl font-bold mb-4">Choose Account Type</h2>
            <p className="text-gray-600 mb-6">
              Select how you'll use Elipsis
            </p>
            
            <div className="space-y-4">
              <button
                onClick={() => { setUserType('client'); setStep(2); }}
                className="w-full p-6 border-2 rounded-lg hover:border-blue-600 text-left"
              >
                <h3 className="font-semibold text-lg mb-2">🏢 I need automation services</h3>
                <p className="text-sm text-gray-600">
                  Assess your organization and request automation solutions
                </p>
              </button>
              
              <button
                onClick={() => { setUserType('bidder'); setStep(2); }}
                className="w-full p-6 border-2 rounded-lg hover:border-blue-600 text-left"
              >
                <h3 className="font-semibold text-lg mb-2">🛠️ I deliver automation services</h3>
                <p className="text-sm text-gray-600">
                  Find clients and deliver digital transformation solutions
                </p>
              </button>
            </div>
          </div>
        )}
        
        {step === 2 && (
          <div>
            <h2 className="text-2xl font-bold mb-6">Create Account</h2>
            
            {/* Form fields */}
            <div className="space-y-4">
              <input
                type="email"
                placeholder="Work Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="w-full border rounded px-3 py-2"
              />
              <input
                type="text"
                placeholder="Full Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full border rounded px-3 py-2"
              />
              <input
                type="password"
                placeholder="Password (min 8 characters)"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="w-full border rounded px-3 py-2"
              />
              <input
                type="password"
                placeholder="Confirm Password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                className="w-full border rounded px-3 py-2"
              />
              
              <button
                onClick={handleSubmit}
                className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
              >
                Create Account
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## 🔧 Environment Variables

### Update: `.env.example`

```bash
# Database (NEON PostgreSQL)
ELIPSIS_DATABASE_URL=postgresql://user:password@neon-host/database

# Secret key for sessions
ELIPSIS_SECRET_KEY=your-strong-secret-key-here

# Admin credentials
ELIPSIS_ADMIN_EMAIL=admin@elipsis.ai
ELIPSIS_ADMIN_PASSWORD=change-me

# Payment gateway (optional)
PAYSTACK_SECRET_KEY=
STRIPE_SECRET_KEY=

# File storage
AWS_S3_BUCKET=elipsis-documents
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Email (for notifications)
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
```

---

## 🚀 Deployment Steps

1. **Database Migration:**
   ```bash
   # Run all ALTER TABLE and CREATE TABLE statements
   psql $ELIPSIS_DATABASE_URL < migrations/marketplace.sql
   ```

2. **Update Dependencies:**
   ```bash
   cd frontend && npm install
   pip install -r requirements.txt
   ```

3. **Build Frontend:**
   ```bash
   cd frontend && npm run build
   ```

4. **Deploy to Vercel:**
   ```bash
   vercel deploy --prod
   ```

---

## ✅ Testing Checklist

- [ ] User registration with type selection works
- [ ] Login validates credentials properly
- [ ] Client can create organization without re-entering data
- [ ] Assessment flow shows scope selection
- [ ] Marketplace displays published requests
- [ ] Bidders can access marketplace with subscription
- [ ] Admin can verify and publish requests
- [ ] Company size badges display correctly
- [ ] Logo appears on all pages
- [ ] Session persistence works
- [ ] File upload for request documents works
- [ ] Feedback system functional

---

## 📊 Success Metrics

- User registration rate
- Assessment completion rate
- Marketplace request publication rate
- Bidder subscription rate
- Average time from request to bid
- Client satisfaction scores

---

**Implementation Priority:**
1. ✅ Database models & migrations
2. ✅ Authentication fixes
3. ✅ Logo implementation
4. ✅ Assessment flow updates
5. ✅ Marketplace backend
6. ✅ Marketplace frontend
7. ✅ Bidder shop pages
8. ✅ Admin panel
9. ✅ Payment integration
10. ✅ Testing & deployment

---

*Document Version: 1.0*  
*Last Updated: 2026-10-09*
