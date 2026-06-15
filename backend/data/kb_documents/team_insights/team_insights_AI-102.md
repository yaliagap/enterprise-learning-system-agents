# AI-102 — Team Insights & Instructor Notes
> Source: internal cohort analytics + instructor feedback (anonymized)
> Last updated: 2026-Q1 | Cohort size: 15

## Team overview
The AI-102 cohort brings stronger hands-on Azure experience than the AI-900 cohort, with most engineers already holding AZ-104 or AZ-900. However, the certification's breadth across six distinct skill areas creates uneven readiness — engineers tend to be strong in the areas closest to their day-to-day work (computer vision or NLP) but have significant gaps in knowledge mining and agentic solution design. The generative AI domain shows the highest average accuracy but scenario questions about safety and content filtering remain a consistent weakness.

## Common stumbling blocks by domain

### Plan and manage an Azure AI solution
- Stumbling block: Azure AI services authentication models — especially when to use managed identity vs. key-based auth vs. Microsoft Entra ID token auth. Questions about cost management and responsible AI deployment reviews also cause errors.
- Why it happens: Engineers default to key-based auth in practice but exam scenarios often test managed identity as the preferred option for production workloads. The responsible AI content review steps are rarely encountered in day-to-day development.
- Instructor note: Review the Azure AI services security best practices documentation. Focus specifically on when managed identity is mandated vs. optional. The Microsoft Learn "Plan and manage an Azure AI solution" module covers this well; supplement with the Azure Well-Architected Framework's security pillar for AI services.

### Implement generative AI solutions
- Stumbling block: Distinguishing appropriate deployment configurations — when to use system prompts vs. few-shot examples vs. fine-tuning vs. retrieval-augmented generation for a given scenario. Content filtering configuration is also a common error point.
- Why it happens: The four approaches have overlapping use cases and the exam uses nuanced scenarios to differentiate them. Engineers familiar with the Azure OpenAI playground tend to default to prompt engineering for all scenarios, missing fine-tuning and RAG as the more appropriate answer.
- Instructor note: Practice with the RAG vs. fine-tuning vs. prompt engineering decision tree. The Microsoft Learn "Develop generative AI solutions with Azure OpenAI Service" learning path is the most comprehensive resource. Hands-on lab time with Azure AI Foundry's prompt flow is strongly recommended.

### Implement an agentic solution
- Stumbling block: Azure AI Agent Service architecture — specifically how agents, threads, tools, and runs relate to each other. Questions about when to use built-in tools (code interpreter, file search) vs. custom function tools cause significant errors.
- Why it happens: Agentic solutions are the newest skill area in AI-102 and most engineers have not built production agents before the exam. The abstraction model differs enough from standard Azure OpenAI that existing knowledge does not transfer cleanly.
- Instructor note: This domain has the highest variability in team scores — some engineers score 90%+ while others score below 50%. The Microsoft Learn "Implement an agentic solution" module is the primary resource; supplement with the Azure AI Agent Service quickstart documentation. Hands-on lab building a simple agent with a function tool is strongly recommended before the exam.

### Implement computer vision solutions
- Stumbling block: Choosing between Azure AI Vision (pre-built), Custom Vision (custom classification/detection), and Azure AI Vision custom model training. Questions about when custom training is justified vs. when pre-built models suffice are the most error-prone.
- Why it happens: The distinction between Azure AI Vision's built-in capabilities and what requires custom model training is blurry without hands-on experience. Engineers overestimate what the pre-built Image Analysis API can do.
- Instructor note: Build a hands-on lab that compares Azure AI Vision Image Analysis results vs. Custom Vision results on the same image set. The performance gap makes the service selection decision clear in practice. Microsoft Learn "Create computer vision solutions with Azure AI Vision" module covers the service boundaries well.

### Implement natural language processing solutions
- Stumbling block: Service selection across Azure AI Language capabilities — CLU (Conversational Language Understanding) vs. custom text classification vs. question answering vs. named entity recognition. Multi-service scenarios where the correct answer requires combining two services are especially error-prone.
- Why it happens: The Azure AI Language service consolidates what were previously separate services (LUIS, QnA Maker, Text Analytics) under a unified API, but the mental model for which capability to use for which scenario is not always clear without hands-on experience in Language Studio.
- Instructor note: Language Studio is the most effective learning tool for this domain. Spend at least two hours in Language Studio building a CLU model, a question answering project, and a custom NER model before the exam. The service boundaries become intuitive after hands-on use. Microsoft Learn "Build a question answering solution" and "Create a conversational language understanding model" modules are the most targeted resources.

### Implement knowledge mining and information extraction solutions
- Stumbling block: Azure AI Search index design — particularly skillsets, enrichment pipelines, and the relationship between indexers, data sources, and indexes. RAG architecture questions that combine Azure AI Search with Azure OpenAI are consistently the most difficult question type for this team.
- Why it happens: Azure AI Search has a complex configuration model that is difficult to learn from documentation alone. Engineers who haven't built a full enrichment pipeline often have incorrect mental models of how indexers, skillsets, and indexes interact. RAG architecture questions compound this by adding Azure OpenAI integration complexity.
- Instructor note: This domain has the lowest team average (72.1 for knowledge mining generally; RAG-specific questions score lower). Building a complete Azure AI Search solution with an enrichment pipeline in a lab environment is the single highest-impact preparation activity for this domain. Microsoft Learn "Implement knowledge mining with Azure AI Search" is the primary resource; supplement with the Azure AI Foundry RAG quickstart to understand the Azure AI Search + Azure OpenAI integration pattern.

## Recommended resources for weak areas
- Plan and manage an Azure AI solution: Microsoft Learn — "Plan and manage an Azure AI solution"; Azure AI services security best practices documentation
- Implement generative AI solutions: Microsoft Learn — "Develop generative AI solutions with Azure OpenAI Service"; Azure AI Foundry prompt flow documentation
- Implement an agentic solution: Microsoft Learn — "Implement an agentic solution"; Azure AI Agent Service quickstart documentation
- Implement computer vision solutions: Microsoft Learn — "Create computer vision solutions with Azure AI Vision"; Custom Vision portal quickstart
- Implement natural language processing solutions: Microsoft Learn — "Build a question answering solution" and "Create a conversational language understanding model"; Azure AI Language Studio hands-on labs
- Implement knowledge mining and information extraction solutions: Microsoft Learn — "Implement knowledge mining with Azure AI Search"; Azure AI Foundry RAG quickstart

## Closing guidance
AI-102 rewards engineers who have built real Azure AI solutions more than those who have only studied documentation. The team's most reliable improvement path is: (1) complete at least one hands-on lab per skill area in Azure AI Foundry or the relevant service portal, (2) focus specifically on service-selection scenarios where multiple Azure AI services could theoretically apply, and (3) prioritize knowledge mining and agentic solution architecture given their consistently below-average team scores. Engineers who combine Microsoft Learn module completion with hands-on lab time consistently score 10-15 percentage points higher than those who rely on documentation study alone.
