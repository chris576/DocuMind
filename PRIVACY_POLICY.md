# Privacy Policy for DMS-RAG

Last updated: 16.08.2026

## 1. General Information

DMS-RAG ("the Application") is a self-hosted RAG (Retrieval-Augmented Generation) backend for document management systems (DMS) and ERP systems. It provides automatic document classification, smart tagging, and semantic search using OpenAI-compatible APIs and Ollama. We are committed to protecting your privacy and personal data.

## 2. Data Controller

DMS-RAG is designed to be self-hosted. You (the operator) are the data controller for all data processed by your instance. The project maintainers do not operate a hosted service and do not have access to your data.

## 3. Data Collection and Processing

### 3.1 Stored Data
The Application stores the following data in its own database (PostgreSQL) and vector database (Chroma/Qdrant/PGVector):
- Configuration and API credentials (e.g. Paperless-ngx URL and token, LLM provider keys)
- Document metadata and content retrieved from your connected DMS/ERP
- Chat history and processing results

All data is stored exclusively on your own infrastructure.

### 3.2 Document Content Processing
- The Application only accesses document content from the DMS/ERP you have connected
- Document contents are transmitted exclusively to the LLM providers you have configured (e.g. OpenAI, Ollama, DeepSeek, OpenRouter)
- No document content is transmitted to the project maintainers or other third parties

### 3.3 Chat History
- Chat histories are stored in your own database
- You can delete them at any time

## 4. Data Transmission

The Application transmits data exclusively to:
- Your self-hosted DMS/ERP installation (e.g. Paperless-ngx)
- The LLM providers you have explicitly configured

No data is transmitted to the project maintainers or other third parties.

## 5. Data Security

- All communication with your servers can be encrypted via HTTPS
- API keys are stored in your own environment configuration
- The Application implements best practices for handling sensitive data

## 6. Your Rights

As the operator of your own instance, you have full control over your data:
- You can delete stored data at any time
- You can stop using the Application at any time

Under GDPR, end users of your instance have the following rights:
- Right to access their personal data
- Right to rectification
- Right to erasure ("right to be forgotten")
- Right to restrict processing
- Right to data portability
- Right to object

## 7. Changes to Privacy Policy

We reserve the right to modify this privacy policy when necessary, in compliance with applicable data protection regulations. The current version can always be found in this repository.

## 8. Contact

If you have any questions about data protection, you can open an issue in the project repository.

## 9. Consent

By installing and using the Application, you agree to this privacy policy. You can withdraw your consent at any time by uninstalling the Application and deleting your data.

## 10. Technical Details

### 10.1 Data Storage Location
All data is stored on your own infrastructure (PostgreSQL, vector database). No data is stored on maintainer servers.

### 10.2 Data Processing
- Document content is processed only when explicitly requested through the chat interface or automated processing
- Processing occurs on your configured LLM providers
- No content caching or storage occurs outside your infrastructure

### 10.3 Security Measures
- All API communications can use HTTPS encryption
- API keys are stored in your own environment configuration
- No logging or tracking of user activities by the maintainers
- No analytics or tracking code is included in the Application

## 11. Children's Privacy

The Application is not intended for use by children under the age of 13. We do not knowingly collect or process data from children under 13 years of age.

## 13. International Data Transfers

As the Extension operates entirely within your browser and communicates only with servers you configure, no international data transfers occur through our services.
