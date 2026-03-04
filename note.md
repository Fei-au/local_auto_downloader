
- Google Cloud
    Resources include computing, storage, ML, networking...
- Google Skills
    Access labs and courses
  - Qwiklabs

Three wave of cloud computing
1. Colocation
Rent physical place, providers provide electricity, network, air condition and more. But  os and software are provided by companies themselives.
2. Virtual Data Center
Split a physical machine to many virtual machine, each machine contains their os.
3. Container-based Architecture
Docker and Kubernetes
Do not need to virtualize a whole computer, but only virtualize the running enviroment for the application.

## IaaS and PaaS
Virtual data center:
Infrastructure as a service
- Raw compute
- Storage
- Network
Similar to physical data centers
Computer Engine is an IaaS
Customer pay the resources ahead of time

Platform as a service
- Bind code to libraries that provide access to the infrasture application needs
App Engine is an PaaS
    - App Engine, you provide code like python, js, java, and give it to google, they config the compute, storage, network resources and run your code, return you an url.
Customer pay the resources they acutally use

Cloud Run is another PaaS, a serverless technology, run containerized microservices
Cloud Run functions, manages event-driven codes

SaaS
Provide entire application stack, deliverying entire cloud-based application that customer can use
Like Gmail, Drive

## The Google Cloud network
- Google cloud Run on Google's own global network
- High throughput and low latencies
- Locations cached for quicker access
- Redundant cloud regions to high-bandwidth connectivity
- Seven major geographic locations, each location divided into different regions and zones. For availability, durability, and latency
  - Locations: Asian, North America, Europe...
  - Regions: asia-east1
  - Zones: asia-east1-a, zones are connected by high fiber network


## Security
- Hardware infrastructure layer
  - Hardware design and provenance: customer design data center, chips
  - Secure boot stack: BIOS, bootloader, kernel, OS
  - Permises security
- Service deployment layer
  - encryption of inter-service communication: cryptographic privacy and integrity for remote procedure call (RPC). 
    - Google services communicate with each other using RPC calls
    - Deploy hardware cryptographic accelerators, exntend the default encryption to all RPC traffic inside data centers
- User identity layer
  - Similar location, same device
  - Universal Second factor U2F
- Storage layer
  - Encryption using centrally managed key
  - Enables hardware encryption
- Internet communication layer
  - Google Front End, TSL connections: public-private key pair and CA certificates
  - Denial of Service DoS protections
- Google's Operational security layer
  - Intrusion detection: Rules gives security teams warnings of possible incidents
  - Reducing insider risk: Limits and monitors the activities of employees who access to infrastructure
  - Employee U2F use
  - Stringent software development practices：central source control and two-party review of code
## Billings and pricing
- Rate Quotas: For example, by default, the GKE service implements a quota of 3,000 calls to its API from each Google Cloud project every 100 seconds.
- Allocation quotas: For example, by default, each Google Cloud project has a quota allowing it no more than 15 Virtual Private Cloud networks.

## Multi-zone
- Improve fault tolerance 即便是一个region中的multi-zone，防止单个机房出问题，如火灾等
- Multi-region 成本更高，防止的是地震，战争等

## Googel Cloud's resource hierarchy
Four levels, buttom up. Each resource has exactly one parent
1. Resources
Like VM, Storage buckets, tables in BigQuery, organized into projects
2. Projects: A trust boundary within your company
Can be organized into folders
- Basis for enabling and using GC services, APIs, billing...
- Each project is a seperate entity under the organization node
- Each resource belongs to exactly one project
Identity attributes
- Project ID, name, number
Google Cloud’s Resource Manager tool: the API manages projects
-  Even recover projects that were previously deleted,and can be accessed through the RPC API and the REST API
3. folders: Your department
Have subfolders
- The resources in a folder inherit policies and permissions from the folder
- To use folders, must have an organization node
Folders:
  - subfolder - department X
    - subfolder - teamA
      - subfolder - product1
      - subfolder - product2
    - subfoler - teamB
  subfolder - department Y
1. Organization node: Your company
- When a user with a Google Workspace or Cloud Identity account creates a Google Cloud project, an organization resource is automatically provisioned for them.
Policies can be defined at project, folder, organization node levels, some GC services allow polices to be applied to individual resources
- Google Workspace or Cloud Identity super administrator:
  - Assign the Organization Admin role
  - be a point of contact in case of recovery issues
  - control the lifecycle of the Google Workspace or Cloud Identity account
- Organization Admin role:
  - Define IAM policies
  - determine the structure of the resource hierarchy
  - delegate responsibility over critical components, such as networking, billing, and resource hierarchy, through IAM roles.
  - Cannot create folders initially, but can give itself the permission to create folders, and then it is able to do so.
Policies are inherited downward:
A policy applied to folder, will applied to its projects within the folder

## IAM
Define who can do what on which resources
- Who (also called principles) of an IAM policies can be
  - a Google account
    - with email as an entity, end user
  - a Google group
    - a named collection of Google Accounts and service accounts
    - has a unique email associate with the group
  - a service Account
    - belong to application instead of end user
    - when run code that is hosted on GC, specify the account that code should run as.
  - a Cloud Identity domain
    - customers who are not Google Workspace customers can get these same capabilities through Cloud Identity
    - Users can be managed by Google Admin console, and IAM is not capable
  - a Google Workspace domain
    - like company.com
    - a virtual group of all the Google Accounts that have been created in an organization's Google Workspace account.
  Identified by email usually
- Can do what defined by a role
  - a collection of permissions
  When you grant role to a principle, you grant all the permissions that the role contains
  - Define deny rules, and apply to certain principle, even it inherit the permission from certion role, it is denied to access the resources as GC check deny rule before permissions
  - Deny policies are inherited through resource hierarchy
  Three kind of roles in IAM
  1. Basic
     1. Owner: access, change and manage associated roles and permissions and set up billing
     2. Editor: access and change, deploy and modify or configure its resources
     3. Viewer: access but not change
     4. Billing administrator
  2. Predefined
     1. InstantAdmin, which manages Compute Engine, apply to principle, folder...
  3. Custom
     1. least-privilege
     2. Can only be defined at project or organization level 
Best practice:
- Granting roles to groups instead of individuals
- Resource hierarchy

### Policy
A policy is a list of bindings which bind “谁（Principal）在什么资源上拥有什么权力（Role）”
It has to bind with resources
```json
{
  "bindings": [
    {
      "role": "roles/storage.objectViewer",
      "members": [
        "user:alice@example.com",
        "serviceAccount:my-app@project-id.iam.gserviceaccount.com"
      ]
    },
    {
      "role": "roles/compute.admin",
      "members": [
        "group:dev-admins@example.com"
      ]
    }
  ],
  "etag": "BwWW4zdwfNE=",
  "version": 3
}
```
Policy insights to help you do the least priviledge
ML-based findings about permission usage in your project, folder, or organization

### Google Cloud Directory Sync
This tool synchronizes users and groups from your existing Active Directory or LDAP system with the users and groups in your Cloud Identity domain.

### Service accounts
It is an account that belongs to your application instead of to an individual end user.

Eg, compute engine holds a service account, and the service account holds some roles, so the compute engine have access to some resources. So applications running in the compute engine have certion permissions
- service account itself is a resource that can be managed by roles
  Eg, Alice has service accounts create permission, so she can create and set any permissions on the service accounts even the permission Alice does not have like bucket access
  Anothe Eg, Service_Account_1 has InstanceAdmin role, and some users or a group are assigned to Service Account User Role, which means they can manipulate or pretend they are a certain Service Account. So they act as Service_Account_1, and then they can do create, modify action on instance which from InstanceAdmin role.

### IAP Identity-Aware Proxy
Is to project custom applications like (Admin website, internal tools)
Which IAM is to project Cloud Resources which hold those custom applications.

It acts like the authorization step in public website

Tow steps
- Who you are (log in to Cloud Account)
- What can you do (check the account's IAM permissions)

### Cloud Identity

## Virtual Private Cloud Networking
1. Definition & Value
Concept: A private, isolated network hosted within Google’s public cloud.

Hybrid Benefit: Combines scalability (public) with data isolation (private).

2. Core Components
Connectivity: Connects resources to each other and the internet.

Control Tools: * Firewall Rules: Restrict access to instances.

Static Routes: Forward traffic to specific destinations.

Segmentation: Organizes the network into subnets.

3. Global Architecture (High Probability Exam Topic) ⭐
VPC Scope: Global. A single VPC can span multiple regions worldwide.

Subnet Scope: Regional. Subnets are defined within a region but can span multiple Zones.

Key Advantage: Resources (VMs) can be in different Zones but belong to the same Subnet.

4. Flexibility & Scaling
IP Expansion: You can increase subnet size by expanding the IP range.

Zero Downtime: Expanding a subnet does not affect existing, configured VMs.


Subnet:
1. Logical Grouping: You don't want your HR database sitting in the same "room" as your public-facing website code. Subnets let you group related resources.
2. Granular Security: You can apply different rules to different subnets.Example: A "Public Subnet" for your website (allows internet traffic). A "Private Subnet" for your Database (blocks ALL internet traffic, only allows the website to talk to it).
3. Geography (Google Specific): In Google Cloud, a VPC is global, but a Subnet is Regional. You create a subnet to define where in the world your resources physically live (e.g., a subnet in Tokyo, another in Iowa).

Compatibilities:
- Forward traffic from one instance to another within same network, across subnetworks, or between google cloud zones without external IP address
- Firewall, distributed firewall
- VPC Peering, two VPCs can exchange traffic; IAM control who and what in one project can interact with a VPC in another


## Compute Engine
As a solution of IaaS

Pricing: billed by second with one-minute minimum

Preemptible or Spot VMs:
You can use it with a cheap price, if someone else use it, the VM will let them to use and you will be stopped to use it. 


- High Avilibility and Disaster Recovery.
  eg: application on even Zone fails
  ans: use Regional managed, Multi-Regional

- Updating Applications
  eg: update application on 100 VMs with zero downtime
  ans: Rolling update, provide a new instance, MIG replace one by one

- Storage Performance and Persistence
  eg: lowest latency for disk I/O
  ans: Local SSD

- Security, Shielded vs Conditional VMs
  eg: While it is being processed in memory
  ans: Confidential Computing (COnfidential VMs) Encrypts data in-use (in RAM)

  Shielded VMs: Protect against boot-level malware

- Cost Optimization
  eg: Compute Engine cost too high, CPU use 10%
  ans: Rightsizing Recommendations. GC analyzes usage and suggests smaller machine types
  If workloadis predictable in 1-3 years, use Comminuted use Discounts

- Health-check and Self-Healing
  eg: VM on but application inside was crashed
  ans: Application-level Health Check

Managed Instance Groups (MIGs): Always the answer for scaling and auto-healing.

Instance Templates: You cannot edit a template; you must create a new version and update the MIG.

Metadata & Startup Scripts: Used to configure VMs automatically when they boot up.

IP Addresses: Use Alias IP ranges if you are running containers (like GKE) on your VMs.

## Cloud Load Balancing
Senario: 40 VMs handle requests
Distribute user traffic across multiple instances of an application

- Fully-distributed, software-defined
- In front of HTTP, HTTPS, TCP, SSH, UDP
- cross-region load balancing

Application Load Balancer
- works on application layer, for HTTP and HTTPS
- reverse proxies
- internet facing and internal application
  
Network Load Balancer
- works on transport layer
- TCP, UDP, other IP protocols
  1. Proxy NLB
     1. reverse proxies, terminating client connections and establishing new ones to backend services
  2. Passthrough NLB
     1. do not modify or terminate connections
     2. forward traffic and preserving original source IP address
     3. wider range of IP protocols  

## Cloud DNS and Cloud CDN
8.8.8.8 Domain Name Service
Translate internet hostname to addresses

Cloud DNS help to find hostnames and addresses built in Coogle Cloud

Content Delivery Network:

Edge caching refers to use caching servers to store content closer to end users

## Connecting networks to Google VPC
Method 1:
Cloud Virtual Private Network(VPN), the tunnel, connects Cloud VPC and other network like (AWS network or your own data center)
1. VPN is encrypt
2. Cloud Router use Border Gateway Protocol to tell each side the existance of each other (route information). (While Normal case is route table)

Security and bandwidth concerns

Method 2:
Peering, putting a router in the same public data center as a Google point of presence, and exchange traffic
1. networks stay seperate
2. Internal IPs
3. No IP Overlap
4. Transitive Peering is NOT allowed
5. Administration: Each side of the peering must independently agree to the connection (one side "requests," the other "accepts").


Each GC project has a default network


### Service Level Agreement
A Service Level Agreement (SLA) is a documented, formal contract between a service provider and a customer that defines specific, measurable performance metrics (e.g., 99.9% uptime, 4-hour response time).

Network SLA
### Dedicated Interconnect
For solutions where Google has direct control over the physical hardware and the connection termination point.

Peering is to send traffic between your business and Google

Network Tier is to send traffic between Google and end user

### Carrier Peering
Your business === A service Provider === Google
The provider do the handshake with Google
Applicable when your data center location does not have a Google edge location(Points of Presence)
Routes traffic over the public Internet; Google cannot gurantee internet hop performance.

### Direct Peering
Your business === Google
A fiber or logic connection to Google directly
You and Google handshake

Relies on a thrid-party provider's network; your SLA is with the carrier not Google

### Standard Network Tier

Routes traffic over the public Internet; Google not gurantee hop performance.

### Dedicated Interconnect:
Provides physical connection between on-premises network and Google's network.

## Networking subnets
Subnets are used to manage IP, splite a large network into small chunks, reduce traffic congestion and improve safety.
It uses subnet mask to split IP

Purpose:
- Minimize broadcasting: If a network includes a thousand computers, and each computers is broadcasting, it will ruin the network.
- Security: Split financial and guest Wi-Fi into different subnet, so they cannot access data in each other
- Easy management: Let floor 1 use 192.168.1.x subnet and floor 2 use 192.168.2.x subnet

eg:
web-subnet-us use 10.0.1.0/24 for us VMs
web-subnet-asia use 10.0.2.0/24 for asian VMs
db-subnet-us use 10.0.3.0/24 for Cloud SQL and Storage

The subnet mask is to mask the first N bit, so that masked N bit are a subnet IP range, the rest bits are subnets IPs and can be used by hosts in the subnet
Like 10.0.1.0/24, they masked 10.0.1, so all the hosts in this subnets are IPs start from 10.0.1, and they can be arranged as 10.0.1.0 - 10.0.1.255 IPs except broadcasting, and other normal reserved IP, so maybe totally 250 IPs can be used by hosts in the subnet

Normally IP is public, but there are three IP reserved for subnets
1. 10.0.0.0/8 or 10.0.0.0 - 10.255.255.255 are class A subnet, usually used by big companies
2. 176.16.0.0/16 or 176.16.0.0 - 176.16.255.255 for class B subnet
3. 192.168.0.0/16 or 192.168.0.0 - 192.168.255.255 for class C subnet, usually used by personal home

## Storage
For data
- structured
- unstructured
- transactional
- relational

## Cloud Storage

## Cloud SQL
No global Scalability

## Spanner

## Firestore
Non-relational

Document database

## AlloyDB
Relational
Need hybrid transactional and analytical processing (HTAP)

## Bigtable
Analytics

NoSQL wide-column database

low latency, large numbers of reads and writes, and maintaining performance at scale.

Bigtable is also suited as a ‘fast lookup’ non-relational database

## BigQuery
Analytics

as a data warehouse, is the default storage for tabular data, and is optimized for large-scale, ad-hoc SQL-based analysis and reporting.

it has a built-in cache, BigQuery works really well in cases where the data does not often change.

## Memorystore
Non-relational

Google Cloud's fully managed Redis service, cache storage































### Spanner
全球级、强一致性的分布式关系型数据库