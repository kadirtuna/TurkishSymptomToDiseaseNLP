# Project Title

A Flask web application for a question-answering system using Retrieval-Augmented Generation (RAG).

## Description

This project implements a Flask web application that provides an API for answering questions based on user-provided symptoms. It utilizes a RAG model to retrieve relevant information and generate responses.

## File Structure

```
web_app_project
├── src
│   ├── web_app.py        # Flask application with API endpoints
│   └── rag_openai.py     # Logic for the RAG model
├── requirements.txt       # Project dependencies
└── README.md              # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd web_app_project
   ```

2. Create a virtual environment:
   ```
   python3 -m venv venv
   ```

3. Activate the virtual environment:
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```
   - On Windows:
     ```
     venv\Scripts\activate
     ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the Flask application, execute the following command:

```
python src/web_app.py
```

The application will be accessible at `http://127.0.0.1:5000`.

## API Endpoints

- **GET /health**: Returns the health status of the application.
- **POST /api/ask**: Accepts a JSON payload with symptoms and returns an answer along with retrieved documents.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License.