## Description 

This project is a **Serverless AI Receipt Data Pipeline** engineered to automate the ingestion, extraction, and semantic structuring of unstructured real-world financial documents. 
 
This platform solves that limitation by implementing an **Asynchronously Decoupled Microservices Pattern**:
1. **The Ingress Ingestion Engine** captures raw multi-modal receipt uploads via a public REST API endpoint managed by Amazon API Gateway and instantly saves them to an object storage buffer.
2. **The Background AI Processing Engine** wakes up automatically via event-driven cloud triggers. It orchestrates **Amazon Rekognition** to execute spatial layout Optical Character Recognition (OCR) before passing the raw unstructured text strings to **Amazon Bedrock (Anthropic Claude 4.6 Sonnet)**.
3. **The LLM Parser** analyzes the chaotic text layout, performs real-time financial data mapping, and serializes the parsed values into a highly organized, type-safe JSON contract.
4. **The Persistence Layer** runs defensive data-sanitization scripts to format the response into a validation-compliant layout, storing the clean metrics securely inside a distributed **Amazon DynamoDB NoSQL database** for rapid frontend dashboard rendering.

The entire cloud ecosystem is 100% serverless, executing on-demand with fine-grained IAM security boundaries, and costing exactly **$0.00 in maintenance overhead when completely inactive**.

## Tech Stack 
- Compute / Microservices: AWS Lambda
- Web API Engine: Amazon API Gateway 
- Object Storage: Amazon S3 
- AI & Computer Vision: Amazon Bedrock, Amazon Rekognition
- Database Management: Amazon DynamoDB


## Architecture Diagram
```mermaid
graph TD
    %% Global Styles
    classDef client fill:#f9fafd,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a;
    classDef web fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d;
    classDef worker fill:#fff7ed,stroke:#ea580c,stroke-width:2px,color:#7c2d12;
    classDef storage fill:#faf5ff,stroke:#8b5cf6,stroke-width:2px,color:#4c1d95;

    %% Client Layer
    Frontend["📱 React Frontend / Client Application"]:::client

    %% Ingress Layer (Web)
    subgraph Web_Ingress_Layer ["🌐 SYNCHRONOUS INGRESS TIER"]
        Gateway["Amazon API Gateway"]:::web
        ApiHandler["⚡ Lambda: api-handler"]:::web
    end

    %% Data Pipeline Layer (Async AI)
    subgraph Async_Processing_Tier ["🤖 ASYNCHRONOUS AI DATA PIPELINE"]
        S3Bucket[("🪣 Amazon S3 Ingest Buffer")]:::storage
        PipelineWorker["⚡ Lambda: process-receipt-pipeline"]:::worker
        Rekognition["👁️ Amazon Rekognition <br> (Computer Vision OCR)"]:::worker
        Bedrock["🤖 Amazon Bedrock <br> (Claude 3.5 Sonnet)"]:::worker
    end

    %% Persistence Layer
    subgraph Persistence_Tier ["🗄️ DATA STORAGE TIER"]
        DynamoDB[("📦 Amazon DynamoDB Table")]:::storage
    end

    %% Flow Path 1: Ingestion
    Frontend -->|1. POST /receipts Base64| Gateway
    Gateway --> ApiHandler
    ApiHandler -->|2. Writes Binary Object| S3Bucket
    ApiHandler -.->|3. HTTP 202 Accepted Instant Return| Frontend

    %% Flow Path 2: AI Processing Pipeline
    S3Bucket -->|4. s3:ObjectCreated Lifecycle Event| PipelineWorker
    PipelineWorker <-->|5. Extract Layout Lines| Rekognition
    PipelineWorker <-->|6. Structural Text Transformation| Bedrock
    PipelineWorker -->|7. Serialize Validated JSON Record| DynamoDB

    %% Flow Path 3: Read Path
    Frontend ===>|8. GET /receipts Fetch Summary| Gateway
    Gateway ===> ApiHandler
    ApiHandler ===>|9. Query Projected Attributes| DynamoDB
    ApiHandler ===>|10. Hydrate Dashboard Rows| Frontend
```
