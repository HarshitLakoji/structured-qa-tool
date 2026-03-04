# Structured QA Tool – GTM Engineer Internship Assignment

## Overview

This project implements a **Structured Question Answering system** designed to help GTM (Go-To-Market) teams automatically answer repetitive questionnaires using internal documentation.

Many companies receive security, compliance, or product questionnaires from potential customers. These questionnaires often contain repetitive questions that require referencing multiple internal documents. This tool demonstrates how **Retrieval Augmented Generation (RAG)** can be used to automatically generate answers from company documentation.

The system allows users to upload reference documents, process questionnaires, retrieve relevant context, and generate answers using an LLM.

---

# Industry & Context Setup

**Industry:** SaaS – Customer Relationship Management (CRM)

**Fictional Company:** AcmeCloud CRM

AcmeCloud CRM is a fictional SaaS platform that helps businesses manage customer relationships, sales pipelines, and marketing campaigns. The platform provides features such as contact management, workflow automation, analytics dashboards, and integrations with external services.

The platform is designed for small and medium-sized businesses that need a centralized system to manage customer interactions and sales operations.

The questionnaire used in this assignment simulates **security and compliance questions that enterprise customers typically ask SaaS vendors before purchasing software.**

---

# What I Built

The application consists of a backend system and a simple frontend interface that demonstrates a structured QA workflow.

### Backend

The backend is implemented using **FastAPI** and **SQLAlchemy**.

Main capabilities include:

* User authentication
* Uploading and managing reference documents
* Storing questionnaires and questions
* Retrieving relevant information from documents
* Generating answers using an LLM
* Storing answers along with supporting context
* Exporting questionnaire results

### Frontend

The frontend provides a simple web interface to interact with the system.

Users can:

* Log in to the system
* Upload reference documents
* Select and run questionnaires
* View generated answers
* Download questionnaire results

---

# System Workflow

The system follows a **Retrieval Augmented Generation (RAG) workflow**:

1. Reference documents are uploaded and stored in the system.
2. When a questionnaire is executed, the system retrieves relevant document content for each question.
3. The retrieved context is combined with the question.
4. The combined prompt is sent to the language model.
5. The generated answer and sources are stored and displayed to the user.

This approach ensures answers are **grounded in company documentation** rather than relying solely on the language model.

---

# Questionnaire

The questionnaire contains realistic questions related to SaaS product security and operations.

Example questions include:

* What security measures are used to protect customer data?
* How is customer data encrypted during storage and transmission?
* Does the platform support role-based access control?
* What authentication mechanisms are supported?
* What compliance standards does the platform follow?
* How are backups and disaster recovery handled?
* What uptime guarantees are provided?

---

# Reference Documents

The system uses internally created reference documents as the **source of truth**.

These documents simulate internal company documentation such as:

* Security policies
* Authentication guidelines
* Compliance documentation
* Backup and recovery procedures
* Infrastructure monitoring policies

These documents are used by the retrieval system to provide context for answering questions.

---

# Assumptions

Several assumptions were made while building this system:

* The fictional company (AcmeCloud CRM) provides SaaS software to business customers.
* Customers frequently send security and compliance questionnaires before purchasing software.
* Internal documentation exists that can be used as the source of truth for answering questions.
* The goal of the system is to assist GTM teams by automatically generating draft answers based on these documents.

---

# Trade-offs

Due to time constraints and assignment scope, several design trade-offs were made:

* SQLite was used instead of a production database.
* Basic document retrieval was implemented instead of a full vector database.
* The UI was kept simple to focus on core backend functionality.
* Limited document preprocessing and chunking were implemented.

These decisions allowed focusing on demonstrating the **core structured QA workflow**.

---

# What I Would Improve With More Time

If given more time, the system could be improved in several ways:

* Integrate a vector database such as FAISS or Pinecone for better document retrieval.
* Implement better document chunking and embedding strategies.
* Add answer confidence scores.
* Improve citation and source attribution.
* Build a more advanced frontend dashboard.
* Add support for multiple questionnaires and batch processing.
* Implement document versioning and indexing.

---

# Running the Project Locally

Clone the repository:

git clone https://github.com/HarshitLakoji/structured-qa-tool.git

Navigate to the project folder:

cd structured-qa-tool

Install dependencies:

pip install -r requirements.txt

Run the application:

uvicorn main:app --reload

Open in browser:

http://localhost:8000

API documentation is available at:

http://localhost:8000/docs

---

# Live Application

Live Application URL:

https://your-render-app.onrender.com

API Documentation:

https://your-render-app.onrender.com/docs

---

# Project Structure

structured-qa-tool
│
├── app
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   └── routes
│
├── templates
├── static
├── questionnaires
├── reference_docs
├── requirements.txt
└── README.md

---

# Technologies Used

* Python
* FastAPI
* SQLAlchemy
* Jinja2 Templates
* SQLite
* LLM API
* Retrieval Augmented Generation (RAG)

---

# Conclusion

This project demonstrates how a structured QA system can help GTM teams automate the process of answering repetitive questionnaires using internal documentation and AI-assisted generation.
