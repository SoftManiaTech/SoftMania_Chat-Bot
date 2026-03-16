import asyncio
import httpx
from src.ingestion.vector_db import setup_pgvector_tables
from src.config import Config

SEED_LINKS = [
    {"page_url": "https://www.softmania.in/", "domain": "softmania.in", "page_type": "homepage", "summary": "main portal presenting Splunk training services, labs, projects, and learning resources"},
    {"page_url": "https://www.softmania.in/about", "domain": "softmania.in", "page_type": "about", "summary": "company overview, mission, training services and Splunk learning ecosystem"},
    {"page_url": "https://www.softmania.in/splunk-community", "domain": "softmania.in", "page_type": "community", "summary": "Splunk community resources, collaboration, and knowledge sharing"},
    {"page_url": "https://www.softmania.in/projects", "domain": "softmania.in", "page_type": "projects", "summary": "list of Splunk projects and project-based learning opportunities"},
    {"page_url": "https://www.softmania.in/terms", "domain": "softmania.in", "page_type": "legal", "summary": "terms and conditions governing service usage"},
    {"page_url": "https://www.softmania.in/refund-policy", "domain": "softmania.in", "page_type": "legal", "summary": "refund conditions and eligibility rules"},
    {"page_url": "https://www.softmania.in/cancellation-policy", "domain": "softmania.in", "page_type": "legal", "summary": "cancellation rules for courses or bookings"},
    {"page_url": "https://www.softmania.in/contact-us", "domain": "softmania.in", "page_type": "contact", "summary": "contact information and communication channels"},
    {"page_url": "https://www.softmania.in/privacy-policy", "domain": "softmania.in", "page_type": "legal", "summary": "data privacy rules and information usage"},
    {"page_url": "https://splunklab.softmania.in/", "domain": "splunklab.softmania.in", "page_type": "labs", "summary": "platform providing Splunk hands-on lab environments"},
    {"page_url": "https://bookings.softmania.in/#/services", "domain": "bookings.softmania.in", "page_type": "booking", "summary": "service booking portal for training and labs"},
    {"page_url": "https://splunklab.softmania.in/project-course-based-labs", "domain": "splunklab.softmania.in", "page_type": "labs", "summary": "Splunk project-based laboratory environments for practice"},
    {"page_url": "https://splunklab.softmania.in/custom-labs", "domain": "splunklab.softmania.in", "page_type": "labs", "summary": "customizable Splunk lab environments"},
    {"page_url": "https://splunk.softmania.in/course/softmania-premium#/home?home=true", "domain": "splunk.softmania.in", "page_type": "course", "summary": "premium course platform for Splunk learning"},
    {"page_url": "https://splunk.softmania.in/clientapp/app/products/explore-products/all-courses", "domain": "splunk.softmania.in", "page_type": "course", "summary": "catalog listing all available Splunk courses"}
]

async def seed_database():
    from src.ingestion.vector_db import setup_pgvector_tables, create_portal_link
    try:
        # 1. Ensure table exists
        print("Setting up pgvector tables and portal_links table...")
        await setup_pgvector_tables()
        print("Tables setup completed.\n")
        
        # 2. Insert links directly via DB function
        print("Inserting seed links to the Database...")
        for link in SEED_LINKS:
            try:
                await create_portal_link(
                    page_url=link["page_url"], 
                    domain=link["domain"], 
                    page_type=link["page_type"], 
                    summary=link["summary"]
                )
                print(f"✅ Created: {link['page_url']}")
            except Exception as e:
                print(f"❌ Error inserting {link['page_url']}: {e}")
    finally:
        # Close the DB pool so the script can exit
        from src.config import Config
        if Config._pg_pool:
            await Config._pg_pool.close()
            print("DB Connection closed.")

if __name__ == "__main__":
    asyncio.run(seed_database())
