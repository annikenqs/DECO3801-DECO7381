# DECO3801-DECO7381: Future of Memory 

### Frontend setup
Starting the server:
```bash
cd futureofmemory/frontend
```
Installing requisite libraries:
```bash
npm install
```
Running it:
```bash
npm run dev
```
### Backend setup

The backend is built with **Python** and **Django**. Follow the steps below to install dependencies, set up the environment, and run the server.

### 1. Navigate to the backend directory
```bash
cd futureofmemory/backend
```

### 2. Create virtual environment
```bash
python -m venv venv
```
### 3. Activate virtual environment
- Mac
    ```bash
    source venv/bin/activate
    ```
- Windows
    ```bash
    venv\Scripts\activate
    ```
### 4. Install required dependencies

```bash
pip install -m requirements.txt
```

### 5. Set up environment variables
- Mac
    ```bash
    export GOOGLE_API_KEY="Your_Google_API_Key"
    ```
- Windows
    ```bash
    set GOOGLE_API_KEY="Your_Google_API_Key"
    ```

### 6. Start the backend server
```bash
python manage.py runserver
```

## Formatting and linting
The application uses Prettier to format, and ESlint for linting. The most useful commands include:

```npm run lint``` → Runs ESLint (with Prettier plugin)

```npm run lint:fix``` → Fixes ESLint issues

```npm run format``` → Formats only

```npm run check``` → Runs both ESLint and Prettier checks (used for CI)
