# DECO3801-DECO7381: Future of Memory

You have to clone or download this repository to run the application locally. You have to run both the frontend and backend servers separately.

## Frontend setup

### 1. Navigate to the frontend directory

```bash
cd futureofmemory/frontend
```

### 2. Install requisite libraries:

```bash
npm install
```

### 3. Run the server:

```bash
npm run dev
```
Paste the link provided in the terminal into your browser to access the frontend.

## Backend setup

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
pip install -r requirements.txt
```

### 5. Set up environment variables

Create an .env file in the backend folder with the following content. Remember to replace `YOUR_AWS_ACCESS_KEY_ID` and `YOUR_AWS_SECRET_ACCESS_KEY` with your actual AWS credentials.

  ```bash
  AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY

  AWS_REGION=us-west-2
  SM_ENDPOINT_NAME=neuro-rag-rt
  MAX_INPUT_TOKENS=1536
  MAX_TOTAL_TOKENS=2048
  USE_SAGEMAKER=true
  ```

Add a file named `serviceAccountkey.json` in the backend folder. Paste the content from your Firebase service account key file. The file should be on this format:

  ```bash
{
    "type": "",
    "project_id": "", 
    "private_key_id": "",
    "private_key": "",
    "client_email": "",
    "client_id": "",
    "auth_uri": "",
    "token_uri": "",
    "auth_provider_x509_cert_url": "",
    "client_x509_cert_url": "",
    "universe_domain": ""
}
  ```

### 6. Run tests (optional)

```bash
python manage.py test
```

### 7. Start the backend server

```bash
python manage.py runserver
```
