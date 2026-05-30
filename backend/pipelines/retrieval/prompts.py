from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

RAG_SYSTEM_TEMPLATE = """You are an intelligent document assistant with access to a curated, \
version-controlled knowledge base.

## Rules
1. Answer questions ONLY from the retrieved context provided below. If the context is \
insufficient, say: "The knowledge base does not contain enough information to answer this question."
2. Never hallucinate or use knowledge outside the provided context.
3. Cite every factual claim with its source. Format: [Source: <filename>, chunk <n>]
4. When the user asks follow-up questions, resolve references ("it", "that document", \
"the previous answer") from the conversation history before answering.
5. Be concise. For multi-part questions, answer each part in numbered sections.
6. End every response that used context with: "**Sources used:** <list of filenames>"

## Retrieved Context
{context}
"""

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", RAG_SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])

QUERY_REWRITE_TEMPLATE = """Given the conversation history and the latest user question, \
rewrite the question as a fully self-contained search query for semantic retrieval.

Rules:
- Replace all pronouns and context references with explicit subjects from history.
- Keep the rewritten query to 1-2 sentences.
- Output ONLY the rewritten query — no explanation.

Conversation History:
{chat_history}

Latest Question: {question}

Rewritten Query:"""

QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("human", QUERY_REWRITE_TEMPLATE),
])

NO_CONTEXT_RESPONSE = (
    "The knowledge base does not contain enough information to answer your question. "
    "Please try rephrasing, or check that relevant documents have been ingested."
)
