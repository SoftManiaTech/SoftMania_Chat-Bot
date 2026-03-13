# SoftMania Exact RAG Dataset Index

Per your instructions, the **exact, raw, text content** of each page and image has been extracted and saved into individual files within the `data/softmania_pages/` directory, rather than being summarized into a single file. 

This ensures your RAG ingestion script has full access to the precise wording, JS rendered tables, prices, and links from the website.

---

## 🌐 Website Content (Extracted via Headless Browser)
*   **[index.md](softmania_pages/index.md)** - `https://www.softmania.in/`
*   **[about.md](softmania_pages/about.md)** - `https://www.softmania.in/about`
*   **[splunk_community.md](softmania_pages/splunk_community.md)** - `https://www.softmania.in/splunk-community`
*   **[projects.md](softmania_pages/projects.md)** - `https://www.softmania.in/projects`
*   **[terms.md](softmania_pages/terms.md)** - `https://www.softmania.in/terms`
*   **[refund_policy.md](softmania_pages/refund_policy.md)** - `https://www.softmania.in/refund-policy`
*   **[cancellation_policy.md](softmania_pages/cancellation_policy.md)** - `https://www.softmania.in/cancellation-policy`
*   **[contact_us.md](softmania_pages/contact_us.md)** - `https://www.softmania.in/contact-us`
*   **[privacy_policy.md](softmania_pages/privacy_policy.md)** - `https://www.softmania.in/privacy-policy`

## 🧪 Splunk Lab Content (Extracted via Headless Browser)
*   **[splunklab_index.md](softmania_pages/splunklab_index.md)** - `https://splunklab.softmania.in/`
*   **[bookings.md](softmania_pages/bookings.md)** - `https://bookings.softmania.in/#/services`
*   **[project_labs.md](softmania_pages/project_labs.md)** - `https://splunklab.softmania.in/project-course-based-labs`
*   **[custom_labs.md](softmania_pages/custom_labs.md)** - `https://splunklab.softmania.in/custom-labs`

## 🎓 Splunk Academy & Bundles (Extracted via Headless Browser)
*   **[premium_bundle.md](softmania_pages/premium_bundle.md)** - `https://splunk.softmania.in/course/softmania-premium#/home?home=true`
*   **[all_courses.md](softmania_pages/all_courses.md)** - `https://splunk.softmania.in/clientapp/app/products/explore-products/all-courses`

---

## 🖼️ User Provided Image Transcriptions
The text content and data from the screenshots you provided have been exactly transcribed:
*   **[image_1_important_disclaimer.md](softmania_pages/image_1_important_disclaimer.md)** (Important License Disclaimer)
*   **[image_2_lab_dashboard.md](softmania_pages/image_2_lab_dashboard.md)** (Lab Portal Dashboard View)
*   **[image_3_join_community.md](softmania_pages/image_3_join_community.md)** (Community Features & Pricing)
*   **[image_4_independent_disclaimer.md](softmania_pages/image_4_independent_disclaimer.md)** (Independent Service Disclaimer)
*   **[image_5_feedbacks.md](softmania_pages/image_5_feedbacks.md)** (Learner WhatsApp Feedback)

*To ingest these into the RAG Pipeline, you can run:*
```bash
python scripts/test_e2e.py data/softmania_pages/
```
