# Veritas - AI Chatbot

A sophisticated, ChatGPT-style conversational AI interface powered by the Groq LLaMA 4 model. This application provides a responsive, feature-rich chat experience with real-time streaming, context retention, and integrated web search capabilities.

## Key Features

### Advanced Conversational Interface
*   **Real-time Streaming**: Utilizes server-sent events (SSE) to deliver instantaneous, token-by-token responses, mimicking natural typing behavior.
*   **Contextual Memory**: Maintains full conversation history within the session, allowing for complex multi-turn interactions and context-aware follow-up questions.
*   **Intelligent Web Search**: Automatically detects queries requiring external information (such as current events or real-time data) and performs web searches to provide accurate, up-to-date citations.
*   **Message Editing**: Users can edit previous messages to refine prompts or correct errors. The system automatically branches the conversation from the edit point, regenerating the subsequent response.

### User Experience & Interface
*   **Syntax Highlighting**: Automatically identifies code blocks within responses and applies language-specific syntax highlighting, ensuring code is readable and copy-ready.
*   **Theme Customization**: Features a robust, system-aware dark and light mode toggle with local storage persistence for user preference.
*   **Export Capabilities**: detailed conversation threads can be exported directly to Markdown format for documentation, archiving, or sharing.
*   **Responsive Design**: A fluid, adaptive interface that ensures full functionality across desktop, tablet, and mobile viewports.

### System Architecture
*   **Persistent Storage**: Integrates with Supabase (PostgreSQL) for reliable cloud storage of conversation history, ensuring data persistence across browser sessions.
*   **Graceful Degradation**: Seamlessly falls back to in-memory session storage if cloud database credentials are not configured, ensuring the application remains functional in all environments.
*   **Conversation Search**: Includes client-side filtering capabilities to rapidly locate specific discussions within the conversation history.

## API Reference

The backend exposes a RESTful API designed for scalability and ease of integration.

### Core Endpoints
*   `POST /api/chat`: Submits a message to the AI agent. Supports `stream=true` for real-time response handling. Automatically handles context window management and web search orchestration.
*   `POST /api/search`: Provides direct access to the search subsystem, allowing for programmatic web queries using the underlying provider.

### Data Management
*   `GET /api/conversations`: Retrieves a paginated list of stored conversation metadata.
*   `GET /api/conversations/<id>`: Fetches the complete message history and state for a specific conversation identifier.
*   `PUT /api/conversations/<id>`: Updates conversation attributes or modifies specific message nodes within the history.
*   `DELETE /api/conversations/<id>`: Permanently removes a conversation record and associated data.

## Keyboard Shortcuts

The interface supports keyboard navigation for high-productivity workflows.

| Shortcut | Function |
|----------|----------|
| Enter | Submit message |
| Shift + Enter | Insert new line |
| Ctrl + N | Initialize new conversation |
| Esc | Interrupt generation |
| Ctrl + Shift + C | Copy latest assistant response |

## Technology Stack

*   **Language Model**: Groq API (LLaMA 4)
*   **Backend Framework**: Flask (Python)
*   **Frontend Architecture**: Vanilla JavaScript (ES6+), CSS3 Variables
*   **Database**: Supabase
*   **Search Provider**: DuckDuckGo API
*   **Rendering Engines**: Marked.js (Markdown), Highlight.js (Syntax)

## License

MIT License

**Developed by Dhanush Pillay**
