from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from src.ingestion.vector_db import (
    create_portal_link,
    get_all_portal_links,
    update_portal_link,
    delete_portal_link
)
from src.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/links", tags=["Link Management"])

# ── Pydantic Models ──

class PortalLinkBase(BaseModel):
    page_url: HttpUrl
    domain: str
    page_type: str
    summary: str

class PortalLinkCreate(PortalLinkBase):
    pass

class PortalLinkUpdate(PortalLinkBase):
    pass

class PortalLinkResponse(PortalLinkBase):
    id: int
    page_url: str

# ── Endpoints ──

@router.get("/", response_model=List[PortalLinkResponse])
async def get_links():
    """Retrieve all stored portal links."""
    try:
        links = await get_all_portal_links()
        return links
    except Exception as e:
        logger.error(f"Error fetching links: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=PortalLinkResponse, status_code=201)
async def create_link(link: PortalLinkCreate):
    """Add a new portal link."""
    try:
        # Convert HttpUrl to string for DB insertion
        result = await create_portal_link(
            str(link.page_url), 
            link.domain, 
            link.page_type, 
            link.summary
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create link")
        return result
    except Exception as e:
        logger.error(f"Error creating link: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{link_id}", response_model=PortalLinkResponse)
async def update_link(link_id: int, link: PortalLinkUpdate):
    """Update an existing portal link."""
    try:
        result = await update_portal_link(
            link_id, 
            str(link.page_url), 
            link.domain, 
            link.page_type, 
            link.summary
        )
        if not result:
            raise HTTPException(status_code=404, detail="Link not found")
        return result
    except Exception as e:
        logger.error(f"Error updating link: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{link_id}", status_code=204)
async def delete_link(link_id: int):
    """Delete a portal link."""
    try:
        success = await delete_portal_link(link_id)
        if not success:
            raise HTTPException(status_code=404, detail="Link not found")
        return None
    except Exception as e:
        logger.error(f"Error deleting link: {e}")
        raise HTTPException(status_code=500, detail=str(e))
