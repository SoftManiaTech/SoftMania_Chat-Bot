# Source URL: https://www.softmania.in/projects

[![SoftMania Logo](/softmania-grad2IT.svg)](/)
[![SoftMania Logo](/softmania-grad2IT.svg)](/)Join Community[Home](/)[About](/about)[Community](/splunk-community)[Projects](/projects)
Others
[Terms & Conditions](/terms)[Refund Policy](/refund-policy)[Cancellation Policy](/cancellation-policy)[Contact Us](/contact-us)[Privacy Policy](/privacy-policy)
Join
## Navigation
012345678910
Search projects and topics
## Common Doubts & Misconceptions
### Prerequisites before learning Splunk
Modules
### How does a computer work?
### What happens when you move file from one folder to another folder?
### Difference between network / internet?
### What happens when you upload file from your laptop to Google Drive?
### How to share files between your primary laptop & secondary laptop?
### How to access your secondary laptop using RDP protocol?
### Why is everyone having a website? What is the purpose of a website?
### Create a Job application portal, which accepts form based input & resume upload
### How does a website work? Why are there multiple components?
### How to host a website on your laptop? & make it accessible to public users?
## Project-1: End-to-end monitoring solution for NovaTech Industries using Splunk
SoftMania Labs
Rent Lab
### SoftMania Labs
₹1,197 Setup
Splunk Distributed Non-clustered
• Search Head-1
• Indexer-1
• Heavy Forwarder-1
• Universal Forwarder-1
# Validity -
Max Hours: 10h  Max Days: 5d
Whichever comes first, environment will automatically terminate.
Data Sources
• Windows (AD & DNS)
• Linux server
• syslog-ng
# Validity -
Max Hours: 6h  Max Days: 3d
Whichever comes first, environment will automatically terminate.
Validity is applicable to individual data sources, not all.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Live Implementation Recordings
2 sessions
Project OverviewArchitecture & Implementation Details
You are part of the IT Observability & Security team at NovaTech Industries, a large smart-manufacturing company.Your mission is to build Splunk as their unified monitoring platform. NovaTech runs Windows and Linux servers both on-prem and in AWS. Their firewalls and security devices send data to a central syslog server. They use ServiceNow for their IT operations.
Your job is to deploy a distributed Splunk environment and onboard all these data sources so NovaTech gains full visibility across servers, cloud, applications, and security.
Architecture Diagram
![Project Architecture](/project-overview/project-1.png)
100%
Procedure
### Prerequisite
### How to create an EC2 instance in AWS?
### How to install Splunk in EC2 instances?3 topic(s) 3 topic(s)
### Splunk Universal Forwarder Installation
### Splunk Architecture Basics4 topic(s) 4 topic(s)
### Connecting Splunk Components3 topic(s) 3 topic(s)
### How to onboard data from Windows
### How to onboard data from Linux
### How to onboard data from ServiceNow
### How to onboard data from Syslog
### How to onboard data from AWS
### How to troubleshoot common issues3 topic(s) 3 topic(s)
## Project-2: A one time Splunk Deployment assignment given to you
SoftMania Labs
Rent Lab
### SoftMania Labs
₹1,330 Setup
Splunk Distributed Cluster
• Search Head-3
• Indexer-3
• Cluster Master
• Heavy Forwarder-1
• Management server
# Validity -
Max Hours: 10h  Max Days: 5d
Whichever comes first, environment will automatically terminate.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Live Implementation Recordings
1 sessions
Project OverviewArchitecture & Implementation Details
One of our client approached us and asking us to configure Clustered Splunk environment for them, they have provided all the required Linux servers (Total - 13)..
Also they want us to configure a deployment Pipeline using Jenkins, Github to streamline their App / Add-on deployment procedure.
Along with SAML/SSO integration using OKTA
Architecture Diagram
![Project Architecture](/project-overview/project-2.png)
100%
Procedure
### Prerequisite
### Configure License manager
### Configure Monitoring Console
### Configure Indexer cluster
### Configure Search head cluster
### Configure Forwarders
### Connect All tiers
### Connect UF's to IF
### Splunk App deployment using Jenkins
### Configure SAML and SSO authentication using OKTA
## Project-3: One Year Splunk Support Project given to you
SoftMania Labs
Rent Lab
### SoftMania Labs
₹1,330 Setup
Splunk Distributed Cluster
• Search Head-3
• Indexer-3
• Cluster Master
• Heavy Forwarder-1
• Management server
# Validity -
Max Hours: 10h  Max Days: 5d
Whichever comes first, environment will automatically terminate.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Project OverviewArchitecture & Implementation Details
One of our client given a 1 Year contract to maintain their Splunk clustered environment, the maintenance activities includes
### Deploying Apps / Addons to environment
* Search Head Cluster
* Indexer Cluster
* Forwarders
### Index Maintenance
* Create required indexes for new customer data onboarding
* Support the Operations team in closing the tenants
---- Removing old customer data from environment (clean & delete the indexes)
* Create required indexes for new customer data onboarding
* Support audit team in restoring the archived data in Splunk
---- How to perform thawing of archived data from frozen bucket?
### Storage maintenance & Reporting
* Analyze index growth pattern and manage disk space
---- Use Monitoring console & queries to check the data volume, events, disk usage
Architecture Diagram
![Project Architecture](/project-overview/project-3.png)
100%
Procedure
### How to Deploy Apps to Search Head cluster?
### How to Uninstall Apps from Search Head cluster?
### How to Deploy Apps to Indexer cluster?
### How to Uninstall Apps from Indexer cluster?
### How to Deploy Apps to Forwarders using Deployment Server?
### How to Uninstall Apps from Forwarders?
### How to create Indexes in an Indexer cluster?
### How to clean an index in an Indexer cluster?
### How to delete an index from an Indexer cluster?
### How to configure frozen bucket for an Index?
### How to resolve index replication or bucket fixup issues?
### How to perform thawing of archived data from frozen bucket?
### How to analyze index growth pattern and manage disk space?
## Project-4: Short term Resilience & Disaster Simulation Assessment in Splunk
SoftMania Labs
Rent Lab
### SoftMania Labs
₹1,330 Setup
Splunk Distributed Cluster
• Search Head-3
• Indexer-3
• Cluster Master
• Heavy Forwarder-1
• Management server
# Validity -
Max Hours: 10h  Max Days: 5d
Whichever comes first, environment will automatically terminate.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Project OverviewArchitecture & Implementation Details
ApexBank reached out to your consulting team because their executives had one major concern:
“We rely heavily on Splunk for Security Operations and Compliance. But we don’t know what happens when Splunk components fail. Show us the risks, the failure scenarios, and how Splunk heals itself.”
They wanted a Resilience & Disaster Simulation Assessment, a hands-on consulting engagement where your team demonstrates what happens when Splunk components fail and how the platform behaves. They wanted not just documentation, but live simulations in a controlled environment.
### List of scenarios you are simulating in this project:
* What happens, If Cluster Master is down?
* What happens, If one of the Indexers is down in a 3-member cluster?
* What happens, If two of the Indexers are down in a 3-member cluster?
* What happens, If all of the Indexers are down in a 3-member cluster?
* What happens, If one of the Search Heads is down in a 3-member cluster?
* What happens, If two of the Search Heads are down in a 3-member cluster?
* What happens, If all of the Search Heads are down in a 3-member cluster?
* What happens, If the Deployer is down?
* What happens, If the Monitoring Console is down?
* What happens, If the Deployment Server is down?
* What happens, If Universal Forwarder is down?
* What happens, If the License Master/Server is down?
Architecture Diagram
![Project Architecture](/project-overview/project-4.png)
100%
Procedure
### What happens, If Cluster Master is down?
### What happens, If one of the Indexers is down in a 3-member cluster?
### What happens, If two of the Indexers are down in a 3-member cluster?
### What happens, If all of the Indexers are down in a 3-member cluster?
### What happens, If one of the Search Heads is down in a 3-member cluster?
### What happens, If two of the Search Heads are down in a 3-member cluster?
### What happens, If all of the Search Heads are down in a 3-member cluster?
### What happens, If the Deployer is down?
### What happens, If the Monitoring Console is down?
### What happens, If the Deployment Server is down?
### What happens, If Universal Forwarder is down?
### What happens, If the License Master or Server is down?
## Project-5: Unified Observability Initiative using Splunk
SoftMania Labs
Rent Lab
### SoftMania Labs
₹2,527 Setup
Splunk Distributed Cluster
• Search Head-3
• Indexer-3
• Cluster Master
• Heavy Forwarder-1
• Management server
# Validity -
Max Hours: 10h  Max Days: 5d
Whichever comes first, environment will automatically terminate.
Data Sources
• Windows (AD & DNS)
• Linux server
• syslog-ng
• OpenVPN
• MySQL
• MSSQL
• Jenkins
# Validity -
Max Hours: 6h  Max Days: 3d
Whichever comes first, environment will automatically terminate.
Validity is applicable to individual data sources, not all.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Project OverviewArchitecture & Implementation Details
Helios Global Technologies runs multiple engineering teams, IT operations, and cloud-native application groups across regions. Each unit built its own monitoring pipeline, resulting in:
* Siloed logs
* No unified compliance visibility
* Cognitive load on engineers
* Repeated troubleshooting failures
* Security blind spots across 3 clouds
* Duplication of monitoring tools
The CIO launches the Unified Observability Initiative, with Splunk as the central analytics engine.
You (the trainees) are the consulting team hired to design, build, and demo a complete onboarding of diverse data sources into a Distributed Splunk deployment.
### List of tasks you are doing in this project:
* How to Onboard data from Windows
* How to Onboard data from Linux
* How to Onboard data from ServiceNow
* How to Onboard data from GitHub
* How to Onboard data from Jenkins
* How to Onboard data from Syslog
* How to Onboard data from AWS
* How to Onboard data from Azure
* How to Onboard data from GCP
* How to Onboard data from MySQL
* How to Onboard data from MSSQL
* How to Onboard data from MongoDB
Architecture Diagram
![Project Architecture](/project-overview/project-5.png)
100%
Procedure
### How to Onboard data from Windows
### How to Onboard data from Linux
### How to Onboard data from ServiceNow
### How to Onboard data from GitHub
### How to Onboard data from Jenkins
### How to Onboard data from Syslog
### How to Onboard data from AWS
### How to Onboard data from Azure
### How to Onboard data from GCP
### How to Onboard data from BIG-IP F5
### How to Onboard data from MySQL
### How to Onboard data from MSSQL
### How to Onboard data from MongoDB
## Project-6: Precision Data Governance & Ingestion Optimization in Splunk
SoftMania Labs
Rent Lab
### SoftMania Labs
₹665 Setup
Splunk Distributed Non-clustered
• Search Head-1
• Indexer-1
• Heavy Forwarder-1
• Universal Forwarder-1
# Validity -
Max Hours: 10h  Max Days: 5d
Whichever comes first, environment will automatically terminate.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Project OverviewArchitecture & Implementation Details
Titan AeroSystems expanded rapidly over the last 2 years. Each engineering division built its own logging standards:
* R&D logs contain massive debug traces
* Manufacturing logs contain repetitive sensor signals
* Security logs contain large noisy fields
* Cloud logs have inconsistent timestamps
* Developers rotate log files unpredictably
As a result:
* Splunk license was being exhausted
* Storage was growing unnecessarily
* Searches were slow
* Correlation rules failed due to timestamps
* Dashboards displayed incorrect timelines
Titan hires your Splunk team to fix the ingestion pipeline and enforce a data governance model.
### List of tasks you are doing in this project:
* Managing Incoming Data (Include or Exclude Specific Data)
* Handling Log Rotation (How Splunk Manages Log File Rotation)
* Discarding Specific Events (Managing Event Data - Discarding Some, Keeping Others)
* Keeping Specific Events (Discarding Unnecessary Events)
* Event Boundary Detection (How Splunk Determines Event Boundaries)
* Timestamp Assignment (Understanding and Configuring Timestamps)
* Timestamp Recognition (Configuring Timestamp Settings)
* Indexed Fields (How Splunk Builds Indexed Fields)
* Importance of Source Types (Why Source Types Matter)
Architecture Diagram
![Project Architecture](/project-overview/project-6.png)
100%
Procedure
### Managing Incoming Data (Include or Exclude Specific Data)
### Handling Log Rotation (How Splunk Manages Log File Rotation)
### Discarding Specific Events (Managing Event Data - Discarding Some, Keeping Others)
### Keeping Specific Events (Discarding Unnecessary Events)
### Event Boundary Detection (How Splunk Determines Event Boundaries)
### Timestamp Assignment (Understanding and Configuring Timestamps)
### Timestamp Recognition (Configuring Timestamp Settings)
### Indexed Fields (How Splunk Builds Indexed Fields)
### Importance of Source Types (Why Source Types Matter)
## Project-7: Splunk Enterprise Upgrade & Continuity Assurance
SoftMania Labs
Rent Lab
### SoftMania Labs
₹1,330 Setup
Splunk Distributed Cluster
• Search Head-3
• Indexer-3
• Cluster Master
• Heavy Forwarder-1
• Management server
# Validity -
Max Hours: 10h  Max Days: 5d
Whichever comes first, environment will automatically terminate.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Project OverviewArchitecture & Implementation Details
## Splunk Enterprise Upgrade & Continuity Assurance
From CTS TechWorks’ point of view, upgrading Splunk to 10.x has become essential because:
* Our current 8.x version is reaching end-of-life, meaning we will soon lose vendor support, security updates, and patch coverage.
* We must meet strict security and compliance requirements, and Splunk 10.x provides updated OpenSSL libraries, hardened components, and modern security standards we need for audits.
* Python 2 dependencies in 8.x are now a risk—we want to fully adopt Python 3 to ensure long-term compatibility of our apps, add-ons, automation, and integrations.
* Our data volume and search load continue to grow, and we need the performance improvements, faster search execution, and optimized indexing delivered by the 10.x architecture.
* We rely heavily on cloud storage and want to take advantage of the improved SmartStore performance and cloud integration features available only in 10.x.
* We need newer Splunk capabilities such as enhanced workload management, better cluster behavior, improved search performance, and the modern UI that improves team productivity.
* Stability and resilience are becoming critical as more business units depend on Splunk dashboards, alerts, and compliance reporting.
* Upgrading now ensures long-term reliability, reduces operational risk, and keeps our monitoring and security ecosystem aligned with future business growth.
Architecture Diagram
![Project Architecture](/project-overview/project-7.png)
100%
Procedure
### How to upgrade a Splunk Standalone environment?2 topic(s) 2 topic(s)
### How to upgrade a Splunk Clustered environment?7 topic(s) 7 topic(s)
## Project-8: Multisite Splunk Architecture Modernization Project
SoftMania Labs
Rent Lab
### SoftMania Labs
₹1,350 Setup
Splunk-DC\_IDX\_SS\_S1
• Site1-IDX1,IDX2,IDX3
• Site1-CM
• Site1-SH1,SH2,SH3
• Site1-Deployer
• IF
• Monitoring Console
• License Server
• Deployment Server
# Validity -
Max Hours: 6h  Max Days: 3d
Whichever comes first, environment will automatically terminate.
Splunk-DC\_IDX\_SS\_S2
• Site1-IDX1
• Site1-IDX2
• Site1-IDX3
# Validity -
Max Hours: 6h  Max Days: 3d
Whichever comes first, environment will automatically terminate.
Splunk-DC\_SH\_SS\_S2
• Site1-SH1
• Site1-SH2
• Site1-SH3
# Validity -
Max Hours: 6h  Max Days: 3d
Whichever comes first, environment will automatically terminate.
#### Important Notes
• This lab environment will be visible to all topics and can be reused after purchase.
Project OverviewArchitecture & Implementation Details
CTS TechWorks is expanding its operations across multiple regions, and we now require a more resilient and scalable Splunk deployment. To support this growth, we have initiated a project focused on designing and implementing a Multisite Splunk Indexer Cluster along with the right Search Head architecture for cross-site visibility and regional performance optimization. Below is what we expect to be delivered as part of this engagement:
### Why We Need This Project (Client Perspective)
* Our business now operates multiple data centers across regions, and we need high availability even if an entire site goes down.
* We want local search performance for each region while still having the option to run global searches across all data.
* We want to optimize storage, replication, and search traffic using Splunk's multisite capabilities. We need flexibility to choose between:
* one central Search Head Cluster for all sites
* or individual Search Head Clusters for each site with independent autonomy
* We also want to evaluate and configure Search Affinity, so searches run on the most relevant set of indexers, reducing WAN load.
Architecture Diagram
![Project Architecture](/project-overview/project-8.png)
100%
Procedure
### How to configure Multisite Indexer Cluster?
### How to configure Common Seach Head Cluster for all Sites?
### How to configure Dedicated Seach Head Cluster for each site?
### How to turn ON and OFF Search Affinity?
## Project-9: Year-Long Splunk Stability & Troubleshooting Engagement
Notify meComing Soon
Project OverviewArchitecture & Implementation Details
CTS TechWorks is entering a critical operational phase where Splunk stability, data quality, and continued visibility across the environment are essential. Over the past few months, our Splunk landscape has grown significantly—more data sources, more indexes, more users, more dashboards, and more security demands.
Because of this rapid scale-up, we have accumulated a backlog of 30+ operational issues across different areas of the platform.
To ensure our monitoring, alerting, and compliance functions remain reliable, we are initiating a 1-year long Splunk Troubleshooting & Platform Health Engagement, where your team is responsible for identifying, isolating, fixing, documenting, and preventing all issues that arise.
### Why We Need This Project (Client Perspective)
* Our Splunk environment is becoming mission-critical, and any outage or data issue directly affects our SOC, NOC, dev teams, and compliance reporting.
* We currently have numerous unresolved Splunk problems, some of which have been lingering for months.
* Many issues are impacting data quality, search accuracy, dashboards, and alerting reliability. Some problems require deep Splunk expertise that our internal teams do not currently have.
* We need long-term expertise to not only fix issues, but also establish prevention mechanisms, so the same issues don't reoccur.
* We want continuous improvement, documentation, and knowledge transfer to our internal teams over 12 months.
Architecture Diagram
![Project Architecture](/project-overview/project-9.png)
100%
Procedure
### Data Replication Issues
### Data Forwarding Issues
### Timestamp Issues
### Event Truncation Issues
### App Deployment Issues
### Retention Policy Issues
### Access Issues
### Parsing Issues
### File Monitoring Issues
### Configuration Issues
### Summary Index Issues
### Splunk Starting Issues
### Splunk Crashing Issues
## SoftMania Community-Led Learning Series
Procedure
### Onboard data from AWS-CloudTrail
[About](/about)|
[Contact Us](/contact-us)|
[Privacy Policy](/privacy-policy)|
[Terms & Conditions](/terms)|
[Refund Policy](/refund-policy)|
[Cancellation Policy](/cancellation-policy)
SoftMania Technologies Private Limited © 2023. All rights reserved.
Labs
V2.0.0
Test Mode