"""Curated source catalog for the Public Library.

Each entry describes a real AI policy, regulation, guidance, standard, or framework
with verified metadata. Content is substantive — key provisions, structure, and
requirements drawn from the actual documents.

To add a new source: append a dict to LIBRARY_SOURCES with the required keys.
"""
from datetime import date

LIBRARY_SOURCES: list[dict] = [
    # =========================================================================
    # 1. EU AI Act
    # =========================================================================
    {
        "source_id": "eu-ai-act-2024",
        "title": "EU AI Act (Regulation 2024/1689)",
        "document_type": "regulation",
        "jurisdiction": "eu",
        "publisher": "European Parliament and Council of the European Union",
        "publication_date": date(2024, 7, 12),
        "source_url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
        "tags": ["risk-classification", "conformity-assessment", "prohibited-ai", "high-risk-ai", "general-purpose-ai"],
        "summary": (
            "The world's first comprehensive horizontal legal framework for regulating artificial intelligence systems. "
            "It establishes a risk-based classification system with corresponding obligations for developers and deployers. "
            "Enforcement is phased: bans on unacceptable-risk AI apply after 6 months, general-purpose AI rules after 12 months, "
            "and most high-risk provisions by August 2026."
        ),
        "content_markdown": """## EU Artificial Intelligence Act — Key Provisions

### Risk-Based Classification

The EU AI Act categorises AI systems into four tiers of risk, each carrying different regulatory obligations:

**Unacceptable Risk (Prohibited)**
Certain AI practices are banned outright due to their potential for harm:
- Social scoring systems used by public authorities that evaluate trustworthiness based on social behaviour or personal characteristics.
- Real-time remote biometric identification in publicly accessible spaces for law enforcement, except in narrowly defined emergency situations.
- AI systems that deploy subliminal, manipulative, or deceptive techniques to distort behaviour and cause significant harm.
- Systems that exploit vulnerabilities of specific groups due to age, disability, or social or economic situation.
- Untargeted scraping of facial images from the internet or CCTV to build facial recognition databases.
- Emotion recognition in the workplace and educational institutions, except for medical or safety reasons.
- Biometric categorisation systems that infer sensitive attributes such as race, political opinions, or sexual orientation.

**High Risk**
AI systems in critical sectors must meet strict requirements before being placed on the market:
- Biometric identification and categorisation of natural persons.
- Management and operation of critical infrastructure (energy, transport, water, digital).
- Education and vocational training (access to education, assessment of students).
- Employment, workers management and access to self-employment (recruitment, task allocation, performance monitoring).
- Access to essential private and public services (credit scoring, emergency dispatch, health insurance).
- Law enforcement (risk assessment of individuals, polygraphs, evidence evaluation).
- Migration, asylum and border control (risk assessment, document authentication).
- Administration of justice and democratic processes.

Requirements for high-risk AI systems include:
- Risk management system operating throughout the entire lifecycle.
- Data governance and management practices for training, validation, and testing data sets.
- Technical documentation before the system is placed on the market.
- Record-keeping enabling automatic logging of events.
- Transparency and provision of information to deployers.
- Human oversight measures allowing humans to monitor, intervene, and override.
- Accuracy, robustness, and cybersecurity appropriate to intended purpose.

**Limited Risk (Transparency)**
Some AI systems carry specific transparency obligations:
- AI systems interacting with natural persons must inform users they are interacting with AI.
- Emotion recognition and biometric categorisation systems must inform persons exposed.
- AI-generated or manipulated content (deepfakes) must be labelled as artificially generated or manipulated.

**Minimal Risk**
All other AI systems can be developed and used without additional legal requirements, though voluntary codes of conduct are encouraged.

### General-Purpose AI Models (GPAI)

The Act introduces dedicated rules for general-purpose AI models (such as foundation models and large language models):
- All GPAI providers must maintain technical documentation, provide information to downstream deployers, comply with copyright law, and publish a sufficiently detailed summary of training data.
- GPAI models with systemic risk (assessed by cumulative compute exceeding 10^25 FLOPs or designated by the AI Office) must additionally: perform model evaluations including adversarial testing, assess and mitigate systemic risks, report serious incidents, and ensure adequate cybersecurity.

### Governance and Enforcement

- A new European AI Office within the Commission oversees GPAI rules and coordinates enforcement.
- Each Member State designates a national competent authority and a market surveillance authority.
- A European Artificial Intelligence Board coordinates national authorities.
- Penalties: up to EUR 35 million or 7% of global annual turnover for prohibited AI practices; up to EUR 15 million or 3% for other violations; up to EUR 7.5 million or 1.5% for supplying incorrect information.

### Timeline

- 1 August 2024: Entry into force.
- 2 February 2025: Prohibition of unacceptable-risk AI practices.
- 2 August 2025: Rules on GPAI models apply; appointment of national authorities.
- 2 August 2026: Most provisions including high-risk AI obligations become applicable.
- 2 August 2027: High-risk AI obligations for certain existing EU product safety legislation.
""",
        "sections": [
            {"heading": "Risk-Based Classification", "content": "Four tiers: Unacceptable (prohibited), High Risk (strict requirements), Limited Risk (transparency obligations), and Minimal Risk (no additional requirements)."},
            {"heading": "High-Risk Requirements", "content": "Risk management, data governance, technical documentation, record-keeping, transparency, human oversight, accuracy, robustness, and cybersecurity."},
            {"heading": "General-Purpose AI", "content": "Dedicated rules for GPAI models: documentation, downstream info, copyright compliance, training data summary. Systemic-risk models face additional obligations."},
            {"heading": "Enforcement", "content": "European AI Office, national authorities, AI Board. Penalties up to EUR 35M or 7% turnover."},
        ],
    },
    # =========================================================================
    # 2. OECD AI Principles
    # =========================================================================
    {
        "source_id": "oecd-ai-principles-2024",
        "title": "OECD Recommendation on Artificial Intelligence",
        "document_type": "framework",
        "jurisdiction": "global",
        "publisher": "Organisation for Economic Co-operation and Development (OECD)",
        "publication_date": date(2024, 5, 3),
        "source_url": "https://legalinstruments.oecd.org/en/instruments/OECD-LEGAL-0449",
        "tags": ["responsible-ai", "intergovernmental", "trustworthy-ai", "policy-recommendations", "generative-ai"],
        "summary": (
            "The first intergovernmental standard on AI, adopted by 47 countries plus the EU. "
            "It establishes five values-based principles and five policy recommendations for governments. "
            "The 2024 revision expanded coverage to address generative and general-purpose AI, environmental sustainability, and misinformation."
        ),
        "content_markdown": """## OECD AI Principles — Full Framework

### Background

Originally adopted on 22 May 2019, the OECD Recommendation on Artificial Intelligence was the first intergovernmental standard on AI. It was revised on 3 May 2024 to address developments in generative AI, foundation models, and large language models. The Principles have been adhered to by 47 countries and the European Union, and formed the basis for the G20 AI Principles.

### Part One: Principles for Responsible Stewardship of Trustworthy AI

**1. Inclusive Growth, Sustainable Development and Well-Being**
AI should benefit people and the planet by driving inclusive growth, sustainable development, and well-being. Stakeholders should proactively engage in responsible stewardship of trustworthy AI in pursuit of beneficial outcomes for people and the planet, including augmenting human capabilities and enhancing creativity, advancing inclusion of underrepresented populations, reducing economic, social, gender, and other inequalities, and protecting natural environments.

**2. Human-Centred Values and Fairness**
AI actors should respect the rule of law, human rights, democratic values, and diversity, and should include appropriate safeguards — for example, enabling human intervention where necessary — to ensure a fair and just society. These include freedom, dignity and autonomy, privacy and data protection, non-discrimination and equality, diversity, fairness, social justice, and internationally recognised labour rights.

**3. Transparency and Explainability**
AI actors should commit to transparency and responsible disclosure regarding AI systems. This includes meaningful information appropriate to the context and consistent with the state of art, to foster a general understanding of AI systems, make stakeholders aware of their interactions with AI systems, enable those affected by an AI system to understand the outcome, and enable those adversely affected by an AI system to challenge its outcome based on plain and easy-to-understand information.

**4. Robustness, Security and Safety**
AI systems should function appropriately and not pose unreasonable safety or security risks. AI actors should ensure traceability, including in relation to datasets, processes and decisions made during the AI system lifecycle, to enable analysis of the AI system's outcomes and responses to inquiry. AI actors should, based on their roles, the context, and their ability to act, apply a systematic risk management approach to each phase of the AI system lifecycle to address risks related to AI systems.

**5. Accountability**
AI actors should be accountable for the proper functioning of AI systems and for the respect of the above principles, based on their roles, the context, and consistent with the state of the art. Mechanisms should be in place to ensure accountability, and these mechanisms should be appropriate to the potential impact of an AI system and should be proportionate to the extent of influence AI actors have over relevant decisions.

### Part Two: National Policies and International Co-operation

**1. Investing in AI Research and Development**
Governments should consider long-term public investment in, and encourage private investment in, research and development — including interdisciplinary efforts — to spur innovation in trustworthy AI that focuses on challenging technical issues and on AI-related social, legal, and ethical implications and policy issues.

**2. Fostering a Digital Ecosystem for AI**
Governments should foster the development of, and access to, a digital ecosystem for trustworthy AI. Such an ecosystem includes digital technologies and infrastructure, mechanisms for sharing AI knowledge, and open and accessible data resources.

**3. Shaping an Enabling Policy Environment for AI**
Governments should promote a policy environment that supports an agile transition from the research and development stage to the deployment and operation stage for trustworthy AI systems. They should review and adapt their policy and regulatory frameworks to encourage innovation and competition.

**4. Building Human Capacity and Preparing for Labour Market Transformation**
Governments should work closely with stakeholders to prepare for the transformation of the world of work and of society. They should empower people to effectively use and interact with AI systems across the breadth of applications, including by equipping them with the necessary skills.

**5. International Co-operation for Trustworthy AI**
Governments should actively co-operate to advance these principles, including through the development of international standards and interoperable governance frameworks, sharing of best practices, and engagement in multi-stakeholder processes.

### 2024 Revision — Key Updates

The May 2024 revision addressed several emerging issues:
- Expanded scope to explicitly cover generative AI and general-purpose AI systems.
- Added emphasis on environmental sustainability and the environmental impact of AI systems.
- Strengthened provisions on misinformation, disinformation, and manipulation.
- Updated language on bias, discrimination, and representativeness in AI training data.
- Added consideration of concentration of market power in AI development.
- Reinforced the importance of content provenance and authenticity.
""",
        "sections": [
            {"heading": "Five Values-Based Principles", "content": "Inclusive growth, human-centred values, transparency, robustness, and accountability."},
            {"heading": "Five Policy Recommendations", "content": "Investment in R&D, digital ecosystem, enabling policy, human capacity, and international cooperation."},
            {"heading": "2024 Revision", "content": "Expanded to cover generative AI, environmental sustainability, misinformation, and market concentration."},
        ],
    },
    # =========================================================================
    # 3. NIST AI Risk Management Framework
    # =========================================================================
    {
        "source_id": "nist-ai-rmf-1-0",
        "title": "NIST AI Risk Management Framework (AI RMF 1.0)",
        "document_type": "framework",
        "jurisdiction": "us_federal",
        "publisher": "National Institute of Standards and Technology (NIST), U.S. Department of Commerce",
        "publication_date": date(2023, 1, 26),
        "source_url": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10",
        "tags": ["risk-management", "trustworthy-ai", "voluntary-framework", "ai-lifecycle", "governance"],
        "summary": (
            "A voluntary, rights-preserving framework for managing risks throughout the AI lifecycle, "
            "organised around four core functions: Govern, Map, Measure, and Manage. "
            "Designed for organisations of any size across sectors, technology-neutral."
        ),
        "content_markdown": """## NIST AI Risk Management Framework (AI RMF 1.0)

### Purpose and Scope

The AI RMF is intended for voluntary use to help organisations that design, develop, deploy, or use AI systems manage the many risks of AI. It is intended to be technology-neutral, applicable across all sectors, and usable by organisations of any size. The framework is not a compliance mechanism; rather, it provides a structured approach to improving the ability to incorporate trustworthiness considerations into the design, development, use, and evaluation of AI products, services, and systems.

### Characteristics of Trustworthy AI

The framework identifies seven key characteristics that contribute to trustworthy AI:

1. **Valid and Reliable** — The AI system performs as intended under the conditions it was designed for, producing correct and consistent outputs. Validation and reliability testing covers both expected and unexpected inputs.

2. **Safe** — The AI system does not endanger human life, health, property, or the environment. Safety considerations include the ability to constrain the system to function within approved boundaries.

3. **Secure and Resilient** — The system maintains confidentiality, integrity, and availability of data and models, and can withstand or quickly recover from adverse events. This covers adversarial attacks, data poisoning, and model theft.

4. **Accountable and Transparent** — Appropriate levels of transparency throughout the AI lifecycle help promote accountability. Transparency relates to the data used, the system design, how the system functions, and how outputs are used.

5. **Explainable and Interpretable** — Explainability refers to the ability to provide representations of why an AI system made a particular decision. Interpretability refers to the meaning of the AI system's output in the context of its intended purpose.

6. **Privacy-Enhanced** — The system protects individuals' privacy and manages data in accordance with applicable laws and values. Techniques include privacy-preserving machine learning, de-identification, and data minimisation.

7. **Fair — with Harmful Bias Managed** — The system actively identifies and manages bias, and promotes fairness in its outcomes. This includes both statistical bias in data and models, and systemic and human biases in design and deployment.

### Core Functions

The AI RMF Core is organised into four functions:

**GOVERN** — Cultivate and implement a culture of risk management within the organisation.
- Establish policies, processes, procedures, and practices for AI risk management.
- Define roles, responsibilities, and lines of authority.
- Ensure the workforce has the knowledge and skills to manage AI risks.
- Create mechanisms for ongoing monitoring and periodic review.
- Foster an organisational culture that considers and communicates AI risk.
- Establish and implement processes for risk tolerance determination.

**MAP** — Establish the context to frame risks related to an AI system.
- Identify and categorise the intended purposes, contexts of use, and potential impacts of the AI system.
- Determine the likelihood and magnitude of each identified risk.
- Examine the AI system's technical characteristics and known limitations.
- Document assumptions, constraints, and requirements.
- Identify relevant stakeholders and affected communities.
- Assess the broader societal impact, including on equity and civil liberties.

**MEASURE** — Employ quantitative, qualitative, or mixed-method tools and techniques to analyse, assess, benchmark, and monitor AI risk and related impacts.
- Establish appropriate metrics to assess the trustworthiness characteristics.
- Measure or estimate the AI risks identified in the MAP function.
- Track emerging risks and changes in the operating environment.
- Gather feedback from relevant stakeholders about AI system performance and impacts.
- Use red-teaming, impact assessments, and stress testing.

**MANAGE** — Allocate risk resources to mapped and measured risks.
- Plan and implement risk treatment actions to maximise the benefits and minimise the negative impacts.
- Continue monitoring risks and risk treatment actions.
- Document and communicate risk management decisions and rationale.
- Establish processes for decommissioning AI systems or managing them post-deployment.
- Create escalation pathways for risks that exceed tolerance levels.

### AI RMF Profiles and Playbook

The framework is accompanied by:
- **Profiles**: Mappings of the AI RMF to specific use cases, sectors, or risk types, enabling tailored implementation.
- **Playbook**: Practical guidance, suggested actions, and transparency notes for each subcategory within the Core functions.
- **Crosswalks**: Mappings to existing frameworks such as ISO/IEC 23894, the OECD AI Principles, and the EU AI Act requirements.
""",
        "sections": [
            {"heading": "Seven Trustworthy AI Characteristics", "content": "Valid and reliable, safe, secure and resilient, accountable and transparent, explainable and interpretable, privacy-enhanced, and fair with harmful bias managed."},
            {"heading": "Four Core Functions", "content": "GOVERN (cultivate risk culture), MAP (establish context), MEASURE (analyse and benchmark), MANAGE (allocate risk resources)."},
            {"heading": "Profiles and Playbook", "content": "Practical guidance, crosswalks to other frameworks, and tailored profiles for specific use cases."},
        ],
    },
    # =========================================================================
    # 4. UK ICO Guidance on AI and Data Protection
    # =========================================================================
    {
        "source_id": "uk-ico-ai-guidance-2023",
        "title": "ICO Guidance on AI and Data Protection",
        "document_type": "guidance",
        "jurisdiction": "uk",
        "publisher": "Information Commissioner's Office (ICO), United Kingdom",
        "publication_date": date(2023, 3, 15),
        "source_url": "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/guidance-on-ai-and-data-protection/",
        "tags": ["data-protection", "uk-gdpr", "fairness", "transparency", "impact-assessment"],
        "summary": (
            "Non-statutory guidance explaining how UK data protection law applies to AI systems that process personal data. "
            "Covers lawfulness, fairness, transparency, and accountability when using AI, including data protection impact assessments. "
            "Updated in 2023 with new chapters on fairness in AI and handling of special category data."
        ),
        "content_markdown": """## ICO Guidance on AI and Data Protection

### Overview

This guidance from the UK Information Commissioner's Office explains how data protection law — specifically the UK GDPR and the Data Protection Act 2018 — applies to organisations developing or using AI systems that process personal data. It is structured around the key data protection principles and aims to help organisations comply with the law while still innovating with AI.

### How Data Protection Applies to AI

**Lawfulness of Processing**
Organisations must have a valid lawful basis for processing personal data in AI systems. Common lawful bases include:
- Legitimate interests (requires a three-part test: identifying the legitimate interest, showing the processing is necessary, and balancing against the individual's interests and rights).
- Consent (must be freely given, specific, informed, and unambiguous).
- Contract (processing necessary for a contract with the individual).
- Legal obligation or public task (for public authorities).

Special category data (race, health, political opinions, biometric data, etc.) requires an additional condition under Article 9 UK GDPR. Processing criminal offence data requires a separate condition under Article 10.

**Fairness**
AI systems must not process personal data in ways that are unduly detrimental, unexpected, or misleading to the individuals concerned. The ICO identifies three aspects of fairness:
- Non-discrimination: AI should not produce biased or discriminatory outcomes for individuals or groups with protected characteristics.
- Statistical accuracy: Models should be accurate and not produce misleading results.
- Distributional fairness: Benefits and risks of AI processing should be fairly distributed.

Organisations should use bias testing and monitoring throughout the AI lifecycle, not just at deployment.

**Transparency**
Organisations must be transparent about how they use AI:
- Privacy notices must explain the use of AI in processing personal data.
- Where solely automated decision-making with legal or similarly significant effects applies (Article 22 UK GDPR), organisations must provide meaningful information about the logic involved and the significance and envisaged consequences.
- Even where Article 22 does not apply, individuals have a general right to know how their data is processed.

**Data Minimisation and Purpose Limitation**
- Only collect and use personal data that is necessary for the specific AI purpose.
- Do not repurpose personal data collected for one purpose to train AI for an unrelated purpose without a new lawful basis.
- Anonymisation and pseudonymisation should be considered to reduce privacy risks.

### Data Protection Impact Assessments (DPIAs)

The ICO strongly recommends conducting a DPIA before deploying an AI system that processes personal data, and a DPIA is legally required when:
- Processing is likely to result in a high risk to individuals' rights and freedoms.
- The processing involves systematic and extensive evaluation of personal aspects (profiling).
- The processing involves large-scale use of special category data.

A DPIA for AI should assess:
- The necessity and proportionality of the AI processing.
- The risks to individuals (discrimination, loss of autonomy, financial harm, etc.).
- The measures in place to mitigate those risks.
- Whether additional safeguards are needed.

### Individual Rights

AI systems must be designed to accommodate individual rights under UK GDPR:
- **Right of access** — Individuals can request information about how AI has been used in decisions about them.
- **Right to rectification** — If AI relies on inaccurate data, individuals have the right to have it corrected.
- **Right to erasure** — In some circumstances, individuals can request deletion of data used by AI systems.
- **Right to object** — Individuals can object to processing based on legitimate interests or direct marketing, including profiling.
- **Rights related to automated decision-making** — Where decisions are made solely by AI with legal or similarly significant effects, individuals have the right not to be subject to such decisions, to obtain human intervention, to express their point of view, and to contest the decision.

### Accountability

Organisations must demonstrate compliance through:
- Documentation of AI development and deployment decisions.
- Records of processing activities.
- Regular auditing and monitoring of AI systems.
- Staff training on data protection requirements for AI.
- Clear governance structures with assigned responsibilities.
""",
        "sections": [
            {"heading": "Lawfulness", "content": "Valid lawful basis required: legitimate interests, consent, contract, or legal obligation. Special category data needs additional conditions."},
            {"heading": "Fairness and Bias", "content": "Non-discrimination, statistical accuracy, distributional fairness. Bias testing throughout the AI lifecycle."},
            {"heading": "Transparency", "content": "Privacy notices, meaningful information about AI logic, individuals' right to know."},
            {"heading": "DPIAs", "content": "Required for high-risk processing. Assess necessity, proportionality, risks, and mitigation measures."},
            {"heading": "Individual Rights", "content": "Access, rectification, erasure, objection, and rights related to automated decision-making."},
        ],
    },
    # =========================================================================
    # 5. UNESCO Recommendation on the Ethics of AI
    # =========================================================================
    {
        "source_id": "unesco-ethics-ai-2021",
        "title": "UNESCO Recommendation on the Ethics of Artificial Intelligence",
        "document_type": "framework",
        "jurisdiction": "global",
        "publisher": "United Nations Educational, Scientific and Cultural Organization (UNESCO)",
        "publication_date": date(2021, 11, 23),
        "source_url": "https://unesdoc.unesco.org/ark:/48223/pf0000380455",
        "tags": ["ethics", "human-rights", "global-norms", "values-based", "member-states"],
        "summary": (
            "The first global normative instrument on AI ethics, adopted by all 194 UNESCO member states. "
            "Establishes a framework of values and principles to guide the ethical development and deployment of AI, "
            "covering data governance, education, health, environment, and gender."
        ),
        "content_markdown": """## UNESCO Recommendation on the Ethics of Artificial Intelligence

### Significance

Adopted unanimously by the General Conference of UNESCO on 23 November 2021, this is the first global normative instrument on the ethics of artificial intelligence. All 194 UNESCO Member States agreed to implement its principles, making it the most widely adopted international framework for AI ethics.

### Values

The Recommendation identifies four foundational values:

**1. Human Rights and Human Dignity**
AI systems must respect, protect, and promote human rights and fundamental freedoms as enshrined in international law. No one shall be subjected to AI-driven discrimination, and AI development should serve to protect and promote human dignity.

**2. Living in Peaceful, Just, and Interconnected Societies**
AI should contribute to peaceful societies, help overcome divides, promote inclusiveness, and strengthen democratic institutions. AI must not be used to undermine democratic processes or suppress fundamental freedoms.

**3. Ensuring Diversity and Inclusiveness**
AI should promote social, cultural, and biological diversity. Development and deployment of AI should involve diverse stakeholders, and AI should not contribute to the homogenisation of cultures, perspectives, or knowledge systems.

**4. Environment and Ecosystem Flourishing**
AI actors should favour data, energy, and resource-efficient methods. The environmental impact of AI systems throughout their lifecycle should be assessed and minimised, including the extraction of raw materials, energy consumption, and electronic waste.

### Principles

Ten principles guide ethical AI development and use:

1. **Proportionality and Do No Harm** — AI methods should be appropriate and proportionate to achieve legitimate aims. The use of AI should not go beyond what is necessary.
2. **Safety and Security** — Unwanted harms and vulnerabilities should be avoided and addressed.
3. **Right to Privacy and Data Protection** — Privacy must be respected and protected throughout the AI lifecycle.
4. **Multi-stakeholder and Adaptive Governance** — Inclusive, participatory approaches to AI governance.
5. **Responsibility and Accountability** — AI actors should be held responsible for the functioning of AI systems.
6. **Transparency and Explainability** — AI actors should provide appropriate and comprehensible information about AI systems.
7. **Human Oversight and Determination** — AI systems should not replace ultimate human responsibility for decisions.
8. **Sustainability** — AI should advance the UN Sustainable Development Goals.
9. **Awareness and Literacy** — Public understanding of AI should be promoted.
10. **Fairness and Non-Discrimination** — AI should promote social justice and not create or reinforce unfair bias.

### Policy Action Areas

The Recommendation includes specific policy guidance across 11 areas:
- Ethical impact assessment
- Ethical governance and stewardship
- Data policy
- Development and international cooperation
- Environment and ecosystem
- Gender
- Culture
- Education and research
- Communication and information
- Economy and labour
- Health and social well-being

### Implementation and Monitoring

UNESCO has established a Readiness Assessment Methodology (RAM) to help Member States assess their preparedness to implement the Recommendation. As of 2024, over 50 countries have completed or initiated readiness assessments. UNESCO also reports regularly on global implementation progress.
""",
        "sections": [
            {"heading": "Four Values", "content": "Human rights, peaceful societies, diversity and inclusiveness, environment and ecosystem."},
            {"heading": "Ten Principles", "content": "Proportionality, safety, privacy, governance, accountability, transparency, human oversight, sustainability, awareness, and fairness."},
            {"heading": "Eleven Policy Areas", "content": "Ethical impact assessment, governance, data policy, development cooperation, environment, gender, culture, education, communication, economy, and health."},
        ],
    },
    # =========================================================================
    # 6. US Executive Order on AI (historical — revoked Jan 2025)
    # =========================================================================
    {
        "source_id": "us-eo-14110-ai-2023",
        "title": "Executive Order 14110 on Safe, Secure, and Trustworthy AI",
        "document_type": "regulation",
        "jurisdiction": "us_federal",
        "publisher": "The White House",
        "publication_date": date(2023, 10, 30),
        "source_url": "https://www.federalregister.gov/documents/2023/11/01/2023-24283/safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence",
        "tags": ["executive-order", "safety-testing", "federal-agencies", "revoked-jan-2025", "ai-governance"],
        "summary": (
            "The most comprehensive U.S. federal executive action on AI, directing over 50 agencies to undertake more than "
            "100 actions across safety, security, privacy, equity, and workforce impacts. Mandated safety testing for powerful AI models. "
            "Note: This order was revoked on 20 January 2025 but remains a significant reference document."
        ),
        "content_markdown": """## Executive Order 14110 — Safe, Secure, and Trustworthy AI

**Status: Revoked on 20 January 2025.** This document remains historically significant and is included as a reference for the policy approaches it pioneered.

### Background

Issued on 30 October 2023, Executive Order 14110 was the most comprehensive U.S. federal executive action on artificial intelligence. It directed more than 50 federal agencies and departments to undertake over 100 specific actions to manage AI risks while promoting innovation.

### Eight Policy Areas

**1. New Standards for AI Safety and Security**
- Developers of the most powerful AI systems (dual-use foundation models trained above a compute threshold of approximately 10^26 FLOPs) were required to notify the federal government and share results of safety tests (red-team testing) before public release.
- NIST was directed to develop standards, tools, and tests for red-teaming AI systems.
- The Department of Energy was tasked with evaluating risks of AI in biological and chemical threats.

**2. Protecting Americans' Privacy**
- Called for federal support for privacy-preserving technologies (such as cryptographic tools for anonymised data analysis).
- Directed agencies to evaluate how they collect and use commercially available data containing personal information.
- Strengthened guidance for federal agencies on privacy impact assessments.

**3. Advancing Equity and Civil Rights**
- Directed agencies to address algorithmic discrimination by providing guidance on preventing AI bias.
- DOJ and federal civil rights offices were tasked with monitoring AI use in the criminal justice system.
- Required assessment of AI's potential to perpetuate or reduce inequities in housing, healthcare, and employment.

**4. Standing Up for Consumers, Patients, and Students**
- HHS was directed to develop an AI safety program for healthcare to evaluate AI-enabled tools used in drug development and clinical settings.
- Department of Education was tasked with creating resources on AI-enabled educational tools.

**5. Supporting Workers**
- Directed development of principles and best practices for employers to mitigate AI-driven displacement.
- Commissioned reports on AI's impact on the labour market and workforce development needs.

**6. Promoting Innovation and Competition**
- Streamlined visa processes for AI talent seeking to study or work in the United States.
- Expanded grants for AI research at National AI Research Institutes.
- Catalysed AI research in critical areas including healthcare and climate change.

**7. Advancing American Leadership Abroad**
- Committed to leading international frameworks for AI governance.
- Expanded bilateral and multilateral engagement on AI risk management.
- Supported safe and responsible deployment of AI in developing countries.

**8. Ensuring Responsible and Effective Government Use of AI**
- Directed agencies to adopt AI governance practices, appoint Chief AI Officers, and inventory AI use cases.
- Required agencies to assess the impact of AI on their workforce.
- Created guidelines for procurement of AI products and services.

### Significance and Legacy

Despite its revocation, the Executive Order influenced:
- Development of safety testing norms for frontier AI models.
- Establishment of Chief AI Officer roles across federal agencies.
- International alignment on AI governance approaches.
- Industry adoption of voluntary safety commitments.
""",
        "sections": [
            {"heading": "Safety and Security", "content": "Red-team testing for powerful models, NIST standards, biological and chemical risk evaluation."},
            {"heading": "Privacy and Civil Rights", "content": "Privacy-preserving technologies, algorithmic discrimination guidance, equity assessments."},
            {"heading": "Innovation and Workers", "content": "Visa streamlining, research grants, workforce displacement mitigation."},
            {"heading": "Revocation", "content": "Revoked 20 January 2025. Remains historically significant for the policy approaches it pioneered."},
        ],
    },
    # =========================================================================
    # 7. Ireland National AI Strategy
    # =========================================================================
    {
        "source_id": "ireland-ai-strategy-2021",
        "title": "AI - Here for Good: National AI Strategy for Ireland",
        "document_type": "policy",
        "jurisdiction": "ireland",
        "publisher": "Department of Enterprise, Trade and Employment, Government of Ireland",
        "publication_date": date(2021, 7, 8),
        "source_url": "https://enterprise.gov.ie/en/publications/national-ai-strategy.html",
        "tags": ["national-strategy", "innovation", "ethical-ai", "ecosystem", "human-centric"],
        "summary": (
            "Ireland's national roadmap for leveraging AI through a people-centred, ethical approach. "
            "Built around three pillars: human-centric AI, growing the AI ecosystem, and building a governance framework. "
            "Refreshed in November 2024 to address generative AI and EU AI Act alignment."
        ),
        "content_markdown": """## AI — Here for Good: Ireland's National AI Strategy

### Vision

Ireland's AI strategy aims to be an international leader in using AI to benefit its economy and society, through a people-centred approach to AI development, adoption, and governance. The title "Here for Good" carries a dual meaning: AI is here to stay, and it should be here for the good of all.

### Three Strategic Pillars

**Pillar 1: A Human-Centric Approach to AI**
- Ensure AI is developed and deployed in ways that respect human rights, democratic values, and the rule of law.
- Promote public awareness and understanding of AI, its potential benefits, and its limitations.
- Build public trust through transparent governance and ethical guidelines.
- Protect individuals from potential harms of AI, including bias, discrimination, and erosion of privacy.
- Ensure that AI augments rather than replaces human decision-making in critical areas.

**Pillar 2: Growing the AI Ecosystem**
- Develop Ireland's capacity to be a leader in AI research and innovation.
- Attract and retain AI talent through education, training, and immigration policies.
- Support Irish businesses — particularly SMEs — in adopting and leveraging AI.
- Position Ireland as a hub for responsible AI development within the EU.
- Develop the national data infrastructure needed to support AI adoption, including open data initiatives and data sharing frameworks.
- Foster collaboration between industry, academia, and government on AI development.

**Pillar 3: Governance Framework for Trustworthy AI**
- Develop a regulatory framework consistent with EU approaches — particularly the EU AI Act.
- Engage with the European Commission, OECD, and Council of Europe on AI governance.
- Support the Data Protection Commission in applying GDPR to AI contexts.
- Develop sector-specific guidance for AI use in areas such as healthcare, education, and public services.
- Establish sandboxes and regulatory experimentation spaces for AI innovation.
- Create mechanisms for ongoing monitoring and assessment of AI impacts.

### Key Actions

The strategy identified over 90 actions across government, enterprise, and society:
- Establish an AI Advisory Council to guide policy development.
- Create a national AI research programme with dedicated funding.
- Develop AI skills programmes at all education levels.
- Launch awareness campaigns to build public understanding of AI.
- Support public sector adoption of AI to improve service delivery.
- Develop ethical guidelines for AI in the public sector.

### 2024 Refresh

The November 2024 refresh updated the strategy to address:
- Developments in generative AI and large language models.
- Alignment with the EU AI Act implementation timeline.
- Enhanced focus on AI skills and workforce development.
- Updated enterprise support measures for AI adoption.
- Strengthened governance and regulatory preparedness.
""",
        "sections": [
            {"heading": "Pillar 1: Human-Centric AI", "content": "Human rights, public trust, transparency, protection from harm, augmenting rather than replacing human decisions."},
            {"heading": "Pillar 2: AI Ecosystem", "content": "Research leadership, talent retention, SME adoption, data infrastructure, industry-academia collaboration."},
            {"heading": "Pillar 3: Governance", "content": "EU AI Act alignment, regulatory sandboxes, sector-specific guidance, monitoring mechanisms."},
        ],
    },
    # =========================================================================
    # 8. Colorado AI Act
    # =========================================================================
    {
        "source_id": "colorado-ai-act-sb24-205",
        "title": "Colorado AI Act (SB24-205)",
        "document_type": "regulation",
        "jurisdiction": "us_state",
        "publisher": "Colorado General Assembly",
        "publication_date": date(2024, 5, 17),
        "source_url": "https://leg.colorado.gov/bills/sb24-205",
        "tags": ["algorithmic-discrimination", "consumer-protection", "high-risk-ai", "impact-assessment", "state-law"],
        "summary": (
            "One of the first comprehensive U.S. state laws regulating AI, focused on preventing algorithmic discrimination "
            "in high-risk AI systems making consequential decisions in employment, housing, credit, education, and healthcare. "
            "Imposes duties on both developers and deployers. Effective date postponed to June 2026."
        ),
        "content_markdown": """## Colorado AI Act (SB24-205)

### Scope

The Colorado AI Act addresses the use of artificial intelligence in making or substantially assisting "consequential decisions" — decisions that have a material legal or similarly significant effect on consumers in areas including:
- Education enrolment and opportunities
- Employment and employment-related decisions
- Financial or lending services
- Essential government services
- Healthcare services and health insurance
- Housing opportunities
- Insurance (other than health)
- Legal services

### Developer Obligations

Developers (entities that design, code, or substantially modify an AI system) must exercise reasonable care to protect consumers from known or foreseeable risks of algorithmic discrimination. Specific duties include:

- **Disclosure to Deployers**: Provide deployers with documentation describing the intended uses and known limitations of the AI system, a summary of the training data and known biases, instructions for use to avoid algorithmic discrimination, and a description of evaluation conducted by the developer.
- **Risk Documentation**: Make available a general description of the types of data used to train the AI system, known or foreseeable limitations, the purpose and intended benefits of the system, and a description of the type of data the system processes.
- **Known Risk Disclosure**: Disclose any known risks of algorithmic discrimination to the Colorado Attorney General and deployers within 90 days of discovery.
- **Annual Review**: Conduct annual reviews and updates of systems to identify and address risks of algorithmic discrimination.

### Deployer Obligations

Deployers (entities that use an AI system to make or substantially assist consequential decisions) must:

- **Risk Management Programme**: Implement a risk management policy and programme proportionate to the size, complexity, and risk profile of the deployer's operations and the AI systems used.
- **Impact Assessment**: Complete an impact assessment for each high-risk AI system before deployment, including: a statement of the system's purpose, an analysis of the benefits and risks, the categories of data processed, an evaluation of the system's outputs for algorithmic discrimination, a description of transparency measures, and the post-deployment monitoring plan.
- **Annual Review**: Conduct annual reviews of deployed high-risk AI systems, updating impact assessments as needed.
- **Consumer Notification**: Provide consumers with notice that an AI system is being used to make or substantially assist a consequential decision about them, including a plain-language description of the system and its purpose, contact information, and information about how to contest the decision.
- **Adverse Decision Process**: If a consequential decision is adverse to a consumer, the deployer must provide a statement of the principal reasons for the decision, an opportunity to correct any incorrect personal data, and an opportunity to appeal to a human reviewer.

### Algorithmic Discrimination

The Act defines algorithmic discrimination as any condition in which an AI system's use results in unlawful differential treatment or impact on individuals on the basis of actual or perceived age, colour, disability, ethnicity, genetic information, limited proficiency in English, national origin, race, religion, reproductive health, sex, veteran status, or other protected classification.

### Enforcement

- Enforcement authority rests exclusively with the Colorado Attorney General.
- No private right of action is created.
- Compliance with recognised frameworks or standards (such as the NIST AI RMF) creates a rebuttable presumption of reasonable care.
- The Attorney General must consider whether the developer or deployer has discovered and cured any violations, and whether the entity cooperated in good faith.

### Timeline

- Signed: 17 May 2024.
- Original effective date: 1 February 2026.
- Postponed effective date: June 2026 (via subsequent legislation SB 25B-004).
""",
        "sections": [
            {"heading": "Scope", "content": "Covers AI used for consequential decisions in education, employment, finance, government services, healthcare, housing, insurance, and legal services."},
            {"heading": "Developer Duties", "content": "Disclosure to deployers, risk documentation, known risk notification, and annual review."},
            {"heading": "Deployer Duties", "content": "Risk management programme, impact assessment, annual review, consumer notification, and adverse decision process."},
            {"heading": "Enforcement", "content": "Exclusively by the Colorado Attorney General. NIST AI RMF compliance creates rebuttable presumption of reasonable care."},
        ],
    },
    # =========================================================================
    # 9. GDPR Article 22 — Automated Decision-Making
    # =========================================================================
    {
        "source_id": "eu-gdpr-article-22",
        "title": "GDPR Automated Decision-Making Provisions (Article 22)",
        "document_type": "regulation",
        "jurisdiction": "eu",
        "publisher": "European Parliament and Council of the European Union",
        "publication_date": date(2016, 5, 4),
        "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng",
        "tags": ["automated-decision-making", "profiling", "data-subject-rights", "human-intervention", "personal-data"],
        "summary": (
            "Article 22 of the GDPR grants data subjects the right not to be subject to decisions based solely on automated "
            "processing that produce legal or similarly significant effects. Requires safeguards including human intervention, "
            "the right to contest decisions, and restrictions on special category data."
        ),
        "content_markdown": """## GDPR Article 22 — Automated Individual Decision-Making, Including Profiling

### The Right

Article 22(1) of the General Data Protection Regulation establishes that data subjects have the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning them or similarly significantly affects them.

This right applies when three conditions are met simultaneously:
1. There is a decision (an act that produces effects on the individual).
2. The decision is based solely on automated processing (no meaningful human involvement).
3. The decision produces legal effects or similarly significantly affects the individual.

### Exceptions

Article 22(2) provides three exceptions where solely automated decision-making with significant effects is permitted:
1. **Contractual necessity**: The decision is necessary for entering into or performing a contract between the data subject and the data controller.
2. **EU or Member State law**: The decision is authorised by Union or Member State law to which the controller is subject, and which lays down suitable measures to safeguard the data subject's rights, freedoms, and legitimate interests.
3. **Explicit consent**: The decision is based on the data subject's explicit consent.

### Required Safeguards

In cases where the exceptions apply (contract or consent), the data controller must implement suitable measures to safeguard the data subject's rights, freedoms, and legitimate interests, at least including the right to:
- Obtain human intervention on the part of the controller.
- Express their point of view.
- Contest the decision.

### Special Category Data

Article 22(4) restricts automated decision-making involving special categories of personal data (Article 9(1)). Such decisions may only be made where:
- The data subject has given explicit consent for specified purposes, OR
- Processing is necessary for reasons of substantial public interest under EU or Member State law.

In both cases, suitable measures must be in place to safeguard the data subject's rights, freedoms, and legitimate interests.

### Profiling

Profiling is defined by Article 4(4) as any form of automated processing of personal data consisting of using personal data to evaluate certain personal aspects relating to a natural person, in particular to analyse or predict aspects concerning that person's performance at work, economic situation, health, personal preferences, interests, reliability, behaviour, location, or movements.

Profiling is not automatically caught by Article 22 — it is only covered when used as the basis for a solely automated decision with legal or significant effects.

### Practical Implications for AI Systems

**What constitutes "solely automated"?**
The Article 29 Working Party (now the European Data Protection Board) has clarified that involvement of a human in the decision process does not automatically take the decision outside of Article 22. The human involvement must be meaningful: the person must have the authority and competence to change the decision, must actually consider all relevant data, and must not just routinely endorse the automated decision.

**What are "legal effects" or "similarly significant effects"?**
Legal effects include decisions that affect someone's legal rights or legal status (for example, cancellation of a contract or denial of a statutory benefit). Similarly significant effects include decisions with equivalent impacts on circumstances, behaviour, or choices, such as denial of credit, denial of employment, or differential pricing that has a substantial effect.

**Transparency requirements**
Under Articles 13(2)(f), 14(2)(g), and 15(1)(h) GDPR, data controllers must provide the data subject with meaningful information about the logic involved and the significance and envisaged consequences of solely automated decision-making. The European Data Protection Board recommends providing information about:
- The categories of data used.
- Why those categories are relevant.
- How the profile is built, including any statistics used.
- Why the profile is relevant to the decision.
- How the profile is used for a decision concerning the individual.
""",
        "sections": [
            {"heading": "The Right", "content": "Right not to be subject to solely automated decisions with legal or similarly significant effects."},
            {"heading": "Exceptions", "content": "Contractual necessity, authorisation by law, or explicit consent."},
            {"heading": "Safeguards", "content": "Human intervention, right to express a view, right to contest the decision."},
            {"heading": "Special Category Data", "content": "Additional restrictions on automated decisions involving sensitive data."},
            {"heading": "Practical Implications", "content": "Meaningful human involvement required. Transparency about logic, significance, and consequences."},
        ],
    },
    # =========================================================================
    # 10. ISO/IEC 42001:2023 — AI Management Systems
    # =========================================================================
    {
        "source_id": "iso-iec-42001-2023",
        "title": "ISO/IEC 42001:2023 — AI Management Systems",
        "document_type": "standard",
        "jurisdiction": "global",
        "publisher": "International Organization for Standardization (ISO) and International Electrotechnical Commission (IEC)",
        "publication_date": date(2023, 12, 18),
        "source_url": "https://www.iso.org/standard/42001",
        "tags": ["management-system", "certification", "governance", "risk-management", "organizational"],
        "summary": (
            "The first international certifiable management system standard for AI. "
            "Specifies requirements for establishing, implementing, and improving an AI Management System (AIMS) "
            "using the Plan-Do-Check-Act methodology. Applicable to organisations of any size."
        ),
        "content_markdown": """## ISO/IEC 42001:2023 — AI Management Systems

### Overview

ISO/IEC 42001 is the first international standard that specifies requirements for an Artificial Intelligence Management System (AIMS). Published in December 2023, it enables organisations to demonstrate responsible development, provision, or use of AI through a certifiable management system.

The standard follows the Harmonized Structure (HS) common to all ISO management system standards, making it compatible with ISO 9001 (quality), ISO 27001 (information security), ISO 14001 (environment), and other management system standards.

### Scope and Applicability

The standard is applicable to any organisation that:
- Develops AI systems or products.
- Provides AI-based services.
- Uses or deploys AI systems within its operations.
- Is of any size, type, or sector.

### Plan-Do-Check-Act Structure

**Plan — Establish the AIMS**
- Understand the organisation and its context, including interested parties.
- Determine the scope of the AIMS.
- Establish an AI policy and objectives.
- Identify and assess AI-related risks and opportunities.
- Plan actions to address risks and achieve objectives.
- Determine necessary resources, competence, awareness, and communication.

**Do — Implement and Operate**
- Implement the planned actions and processes.
- Perform AI risk assessments for specific AI systems.
- Apply AI risk treatments (accept, mitigate, transfer, or avoid risks).
- Address AI system lifecycle processes: design, development, testing, deployment, operation, monitoring, and retirement.
- Manage third-party relationships and outsourced AI processes.
- Document and maintain records of AI development and deployment decisions.

**Check — Monitor and Review**
- Monitor, measure, analyse, and evaluate AIMS performance and effectiveness.
- Conduct internal audits of the AIMS at planned intervals.
- Perform management reviews to assess AIMS suitability, adequacy, and effectiveness.
- Review the results of AI system monitoring and evaluation.

**Act — Improve**
- Address nonconformities and take corrective action.
- Continually improve the suitability, adequacy, and effectiveness of the AIMS.
- Update AI risk assessments and treatments as the AI landscape evolves.

### Key Requirements

**AI Risk Assessment (Clause 6.1.4)**
Organisations must establish a process for AI risk assessment that:
- Identifies AI-related risks associated with specific AI systems.
- Analyses and evaluates the identified risks against risk criteria.
- Considers impacts on individuals, groups, and societies.
- Considers technical risks (data quality, model performance, cybersecurity).
- Prioritises risks for treatment.

**AI Risk Treatment (Clause 6.1.4)**
For each identified risk, organisations must:
- Select appropriate risk treatment options.
- Determine all controls necessary to implement the chosen options.
- Compare determined controls with those in Annex A.
- Produce a Statement of Applicability listing necessary controls and their justification.

**Annex A — Reference Controls**
The standard includes an extensive set of AI-specific controls in Annex A, covering:
- AI policies and governance.
- Internal organisation for AI responsibilities.
- Resources for AI systems (data, tools, computing).
- AI system impact assessment.
- AI system lifecycle management.
- Data management for AI systems.
- Technology and AI system monitoring.
- Third-party and customer relationships.

**Annex B — AI Objectives and Risk Sources**
Provides guidance on:
- Potential AI objectives organisations may establish.
- Sources of AI-related risk across the development and deployment lifecycle.
- Guidance on assessing impact severity and likelihood.

### Relationship to Other Standards

ISO/IEC 42001 forms the cornerstone of the ISO/IEC 42000 family of AI standards:
- **ISO/IEC 23894** — AI Risk Management (guidance).
- **ISO/IEC 42005** — AI System Impact Assessment.
- **ISO/IEC 42006** — Requirements for bodies providing audit and certification of AIMS.
- **ISO/IEC TR 24028** — Trustworthiness in AI.
- **ISO/IEC 5338** — AI System Lifecycle Processes.

### Certification

Organisations can seek third-party certification of their AIMS against ISO/IEC 42001, providing independent assurance that their AI governance meets international standards. Certification bodies must themselves comply with ISO/IEC 42006.
""",
        "sections": [
            {"heading": "PDCA Structure", "content": "Plan (establish AIMS), Do (implement), Check (monitor and audit), Act (improve)."},
            {"heading": "AI Risk Assessment", "content": "Identify, analyse, evaluate, and treat AI-related risks for specific systems."},
            {"heading": "Annex A Controls", "content": "AI policies, governance, resources, impact assessment, lifecycle management, data management, monitoring."},
            {"heading": "Certification", "content": "Organisations can seek third-party certification. Part of the ISO/IEC 42000 family of AI standards."},
        ],
    },
]
